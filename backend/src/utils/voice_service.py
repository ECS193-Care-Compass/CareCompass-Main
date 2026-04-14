"""
VoiceService: Audio transcription and synthesis for CARE Bot.
- Transcription: AWS Transcribe (primary) → Gemini (fallback)
- Synthesis: AWS Polly (neural TTS)
"""
import boto3
import os
import time
import uuid
import requests
from typing import Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceService:
    def __init__(self, region_name: str = None):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        try:
            self.polly = boto3.client("polly", region_name=self.region_name)
            self.transcribe = boto3.client("transcribe", region_name=self.region_name)
            self.s3 = boto3.client("s3", region_name=self.region_name)
            self.bucket_name = os.getenv("S3_DOCUMENTS_BUCKET")
            if not self.bucket_name:
                logger.warning("S3_DOCUMENTS_BUCKET not set — AWS Transcribe will be unavailable")
            logger.info(f"VoiceService initialized. Bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize VoiceService AWS clients: {e}")
            self.polly = None
            self.transcribe = None
            self.s3 = None

        # Gemini client for transcription fallback
        self._gemini_client = None
        try:
            from google import genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                self._gemini_client = genai.Client(api_key=api_key)
                logger.info("VoiceService: Gemini audio transcription fallback enabled")
        except Exception as e:
            logger.warning(f"VoiceService: Gemini fallback not available: {e}")

    def transcribe_audio(self, audio_bytes: bytes, file_extension: str = "webm") -> Optional[str]:
        """
        Transcribe audio bytes to text using Gemini.
        Falls back to AWS Transcribe if Gemini is unavailable.
        """
        # Try Gemini first (faster, no subscription required)
        transcript = self._transcribe_gemini(audio_bytes, file_extension)
        if transcript:
            return transcript

        # Fallback to AWS Transcribe
        logger.info("VoiceService: Gemini failed, trying AWS Transcribe fallback...")
        return self._transcribe_aws(audio_bytes, file_extension)

    def _transcribe_gemini(self, audio_bytes: bytes, file_extension: str = "webm") -> Optional[str]:
        """Transcribe audio using Google Gemini as fallback."""
        if not self._gemini_client:
            logger.warning("VoiceService: Gemini client not available for transcription")
            return None

        try:
            from google.genai import types

            mime_map = {
                "webm": "audio/webm",
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "ogg": "audio/ogg",
                "flac": "audio/flac",
            }
            mime_type = mime_map.get(file_extension, "audio/webm")

            logger.info(f"VoiceService: Sending {len(audio_bytes)} bytes to Gemini for transcription...")
            start = time.time()

            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            response = self._gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    "Transcribe the following audio to text. Return ONLY the transcribed text, "
                    "nothing else. If the audio is silent or unclear, return exactly: [SILENCE]",
                    audio_part,
                ],
            )

            transcript = response.text.strip() if hasattr(response, "text") and response.text else ""
            elapsed = time.time() - start

            if not transcript or transcript == "[SILENCE]":
                logger.info(f"VoiceService: Gemini returned silence/empty in {elapsed:.2f}s")
                return None

            logger.info(f"VoiceService: Gemini transcription in {elapsed:.2f}s: \"{transcript}\"")
            return transcript

        except Exception as e:
            logger.error(f"VoiceService: Gemini transcription failed: {e}", exc_info=True)
            return None

    def _transcribe_aws(self, audio_bytes: bytes, file_extension: str = "webm") -> Optional[str]:
        """Transcribe audio using AWS Transcribe (uploads to S3, polls for result)."""
        start_total = time.time()
        if not self.transcribe or not self.s3 or not self.bucket_name:
            logger.warning("VoiceService: AWS Transcribe unavailable (missing client or bucket)")
            return None

        job_name = f"transcription-{uuid.uuid4()}"
        s3_key = f"voice-uploads/{job_name}.{file_extension}"

        try:
            self.s3.put_object(Bucket=self.bucket_name, Key=s3_key, Body=audio_bytes)
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"

            self.transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": s3_uri},
                MediaFormat=file_extension,
                LanguageCode="en-US",
            )

            # Poll until complete (0.2s interval, max 60s)
            max_retries = 300
            status = None
            job_status = "UNKNOWN"
            while max_retries > 0:
                status = self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
                job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
                if job_status in ("COMPLETED", "FAILED"):
                    break
                time.sleep(0.2)
                max_retries -= 1

            if job_status == "COMPLETED" and status:
                result_url = (
                    status.get("TranscriptionJob", {})
                    .get("Transcript", {})
                    .get("TranscriptFileUri")
                )
                if not result_url:
                    return None
                resp = requests.get(result_url, timeout=30)
                resp.raise_for_status()
                transcripts = resp.json().get("results", {}).get("transcripts", [])
                if not transcripts:
                    return None
                transcript = transcripts[0].get("transcript", "")
                logger.info(f"VoiceService: AWS transcript in {time.time() - start_total:.2f}s: \"{transcript}\"")
                return transcript
            else:
                return None

        except Exception as e:
            logger.error(f"VoiceService: AWS Transcribe error: {e}")
            return None
        finally:
            for attempt in range(3):
                try:
                    self.s3.delete_object(Bucket=self.bucket_name, Key=s3_key)
                    break
                except Exception as cleanup_err:
                    if attempt == 2:
                        logger.warning(f"VoiceService: S3 cleanup failed: {cleanup_err}")

    def synthesize_speech(self, text: str, voice_id: str = "Joanna") -> Optional[bytes]:
        """Convert text to speech using AWS Polly (neural engine, MP3 output)."""
        if not self.polly:
            logger.error("VoiceService: Polly client not initialized.")
            return None

        try:
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat="mp3",
                VoiceId=voice_id,
                Engine="neural",
            )
            audio_data = response["AudioStream"].read()
            logger.info(f"VoiceService: Polly synthesized {len(audio_data)} bytes")
            return audio_data
        except Exception as e:
            logger.error(f"VoiceService: Polly synthesis failed: {e}", exc_info=True)
            return None
