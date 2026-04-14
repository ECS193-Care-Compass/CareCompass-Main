import boto3
import os
import time
import uuid
import base64
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
                logger.warning("S3_DOCUMENTS_BUCKET not set in environment variables")

            logger.info(f"VoiceService initialized. Bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize VoiceService: {e}")
            self.polly = None
            self.transcribe = None
            self.s3 = None

        # Initialize Gemini client for audio transcription fallback
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
        Transcribe audio. Tries AWS Transcribe first, falls back to Gemini.
        """
        # Try AWS Transcribe first
        transcript = self._transcribe_aws(audio_bytes, file_extension)
        if transcript:
            return transcript

        # Fallback: Use Gemini to transcribe audio
        logger.info("[DEBUG] VoiceService: AWS Transcribe failed, trying Gemini fallback...")
        transcript = self._transcribe_gemini(audio_bytes, file_extension)
        if transcript:
            return transcript

        logger.error("[DEBUG] VoiceService: All transcription methods failed.")
        return None

    def _transcribe_gemini(self, audio_bytes: bytes, file_extension: str = "webm") -> Optional[str]:
        """Transcribe audio using Google Gemini as fallback."""
        if not self._gemini_client:
            logger.warning("[DEBUG] VoiceService: Gemini client not available for transcription")
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

            logger.info(f"[DEBUG] VoiceService: Sending {len(audio_bytes)} bytes to Gemini for transcription...")
            start = time.time()

            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

            response = self._gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    "Transcribe the following audio to text. Return ONLY the transcribed text, nothing else. If the audio is silent or unclear, return exactly: [SILENCE]",
                    audio_part
                ]
            )

            transcript = response.text.strip() if hasattr(response, 'text') and response.text else ""
            elapsed = time.time() - start

            if not transcript or transcript == "[SILENCE]":
                logger.info(f"[DEBUG] VoiceService: Gemini returned silence/empty in {elapsed:.2f}s")
                return None

            logger.info(f"[DEBUG] VoiceService: Gemini transcription in {elapsed:.2f}s: \"{transcript}\"")
            return transcript

        except Exception as e:
            logger.error(f"[DEBUG] VoiceService: Gemini transcription failed: {e}", exc_info=True)
            return None

    def _transcribe_aws(self, audio_bytes: bytes, file_extension: str = "webm") -> Optional[str]:
        """Transcribe audio using AWS Transcribe."""
        start_total = time.time()
        if not self.transcribe or not self.s3 or not self.bucket_name:
            logger.error("[DEBUG] VoiceService: Transcribe/S3 client or bucket NOT initialized.")
            return None

        job_name = f"transcription-{uuid.uuid4()}"
        s3_key = f"voice-uploads/{job_name}.{file_extension}"

        try:
            # 1. Upload audio to S3
            logger.info(f"[DEBUG] VoiceService: Starting S3 upload to {s3_key}...")
            upload_start = time.time()
            self.s3.put_object(Bucket=self.bucket_name, Key=s3_key, Body=audio_bytes)
            logger.info(f"[DEBUG] VoiceService: S3 upload COMPLETED in {time.time() - upload_start:.2f}s")

            s3_uri = f"s3://{self.bucket_name}/{s3_key}"

            # 2. Start transcription job
            logger.info(f"[DEBUG] VoiceService: Starting Transcribe job {job_name}...")
            self.transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": s3_uri},
                MediaFormat=file_extension,
                LanguageCode="en-US"
            )

            # 3. Wait for job completion (polling)
            logger.info("[DEBUG] VoiceService: Polling Transcribe job status...")
            poll_start = time.time()
            max_retries = 300
            job_status = "UNKNOWN"
            status = None

            while max_retries > 0:
                status = self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
                job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
                if job_status in ["COMPLETED", "FAILED"]:
                    break
                time.sleep(0.2)
                max_retries -= 1

            poll_duration = time.time() - poll_start
            logger.info(f"[DEBUG] VoiceService: Job {job_name} finished as {job_status} in {poll_duration:.2f}s")

            if job_status == "COMPLETED" and status is not None:
                transcript_info = status.get("TranscriptionJob", {}).get("Transcript", {})
                result_url = transcript_info.get("TranscriptFileUri")
                if not result_url:
                    return None

                response = requests.get(result_url, timeout=30)
                response.raise_for_status()
                transcript_data = response.json()
                transcripts = transcript_data.get("results", {}).get("transcripts", [])
                if not transcripts:
                    return None

                transcript = transcripts[0].get("transcript", "")
                logger.info(f"[DEBUG] VoiceService: AWS transcript in {time.time() - start_total:.2f}s: \"{transcript}\"")
                return transcript
            else:
                return None

        except Exception as e:
            logger.error(f"[DEBUG] VoiceService: AWS Transcribe error: {e}")
            return None
        finally:
            for attempt in range(3):
                try:
                    self.s3.delete_object(Bucket=self.bucket_name, Key=s3_key)
                    logger.info("[DEBUG] VoiceService: Cleanup: S3 temp file deleted.")
                    break
                except Exception as cleanup_err:
                    if attempt == 2:
                        logger.warning(f"[DEBUG] VoiceService: Cleanup failed: {cleanup_err}")

    def synthesize_speech(self, text: str, voice_id: str = "Joanna") -> Optional[bytes]:
        """Convert text to speech using AWS Polly."""
        if not self.polly:
            logger.error("[DEBUG] VoiceService: Polly client NOT initialized.")
            return None

        try:
            logger.info(f"[DEBUG] VoiceService: Starting Polly synthesis for text length {len(text)}...")
            poly_start = time.time()
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat="mp3",
                VoiceId=voice_id,
                Engine="neural"
            )
            audio_data = response["AudioStream"].read()
            logger.info(f"[DEBUG] VoiceService: Polly synthesis COMPLETED in {time.time() - poly_start:.2f}s. Audio size: {len(audio_data)} bytes.")
            return audio_data
        except Exception as e:
            logger.error(f"[DEBUG] VoiceService: CRITICAL error in synthesize_speech: {e}", exc_info=True)
            return None
