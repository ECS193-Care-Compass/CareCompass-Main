"""
FastAPI server for CARE Bot
Connects the Python RAG backend to the Electron + React frontend
"""
import os
import sys
import json
import base64
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(override=True)

from main import CAREBot
from src.utils.logger import get_logger
from src.utils.backup_scheduler import BackupScheduler
from src.utils.user_manager import UserManagerWithS3
from src.utils.voice_service import VoiceService
from config.settings import VECTORSTORE_DIR
import boto3

# Import S3Manager from aws/lambda
sys.path.insert(0, str(Path(__file__).parent / "aws" / "lambda"))
try:
    from s3_manager import S3Manager  # type: ignore
except ImportError:
    S3Manager = None  # type: ignore

logger = get_logger(__name__)

# Initialize S3 client for logging
try:
    s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    S3_LOGS_BUCKET = os.getenv('S3_LOGS_BUCKET')
    if not S3_LOGS_BUCKET:
        logger.warning("S3_LOGS_BUCKET not set in environment variables")
except Exception:
    s3_client = None
    S3_LOGS_BUCKET = None

def log_to_s3(endpoint: str, status: str, data: dict):
    """Log API calls to S3"""
    if not s3_client or not S3_LOGS_BUCKET:
        return

    try:
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "endpoint": endpoint,
            "status": status,
            "data": data
        }

        key = f"interactions/{timestamp.split('T')[0]}/{timestamp}.json"
        s3_client.put_object(
            Bucket=S3_LOGS_BUCKET,
            Key=key,
            Body=json.dumps(log_entry, indent=2),
            ContentType='application/json'
        )
    except Exception as e:
        logger.warning(f"Failed to log to S3: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="CARE Bot API",
    description="Trauma-Informed RAG Chatbot API",
    version="1.0.0"
)

# CORS: Allow configurable origins (restrict in production via ALLOWED_ORIGINS env var)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize bot and backup scheduler
bot = None
backup_scheduler = None
user_manager = None
voice_service = None


@app.on_event("startup")
async def startup():
    """Initialize CARE Bot and backup scheduler on server startup"""
    global bot, backup_scheduler, user_manager, voice_service
    logger.info("Starting CARE Bot API...")
    bot = CAREBot(warmup_crisis_detector=False)
    voice_service = VoiceService()

    # Initialize user manager for tracking user data
    try:
        user_manager = UserManagerWithS3(use_s3=True)
        logger.info("User manager initialized - tracking sessions to S3")
    except Exception as e:
        user_manager = None
        logger.warning(f"User manager disabled: {e}")


    # Initialize vector store if empty
    stats = bot.get_stats()
    if stats["vector_store"]["document_count"] == 0:
        logger.info("Vector store empty. Initializing...")
        bot.initialize_vector_store()

    # Initialize backup scheduler
    try:
        logger.info("Initializing S3Manager...")
        s3_manager = S3Manager(region=os.getenv('AWS_REGION', 'us-east-1'))
        logger.info(f"S3Manager initialized: {s3_manager.vectordb_bucket}")

        # Use 1 hour interval for development, 168 hours (weekly) for production
        backup_interval = 1 if os.getenv("ENVIRONMENT") == "dev" else 168
        logger.info(f"Creating BackupScheduler (interval: {backup_interval}h, vectorstore: {VECTORSTORE_DIR})")

        backup_scheduler = BackupScheduler(
            vectorstore_path=str(VECTORSTORE_DIR),
            s3_manager=s3_manager,
            backup_interval_hours=backup_interval
        )
        backup_scheduler.start()
        logger.info("Backup scheduler started")

        # Run backup immediately on startup
        logger.info("Running initial backup now...")
        backup_scheduler._backup_job()
        logger.info("Initial backup completed")

    except Exception as e:
        logger.error(f"Backup scheduler initialization FAILED: {e}", exc_info=True)

    logger.info("CARE Bot API ready")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on server shutdown"""
    global backup_scheduler
    if backup_scheduler and backup_scheduler.is_running:
        backup_scheduler.stop()
        logger.info("ChromaDB backup scheduler stopped")


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    scenario: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    is_crisis: bool
    num_docs_retrieved: int
    scenario: Optional[str] = None
    blocked: bool = False

class StatsResponse(BaseModel):
    vector_store: dict
    retriever_top_k: int
    llm_model: str
    crisis_keywords: int
    conversation_history: dict


# --- API Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to CARE Bot and get a response

    - **query**: User's message
    - **user_id**: Optional user identifier (auto-provided by frontend)
    - **scenario**: Optional category (immediate_followup, mental_health, practical_social, legal_advocacy, delayed_ambivalent)
    - **session_id**: Optional session ID (auto-generated if not provided)
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Use provided IDs or skip if not available
        user_id = request.user_id
        session_id = request.session_id

        # Track user and create/get session (only if user_id provided)
        if user_manager and user_id:
            # Create user if doesn't exist
            user = user_manager.get_user(user_id)
            if not user:
                user_manager.create_user(user_id)

            # Generate session if needed
            if not session_id:
                session_id = f"sess_{str(uuid.uuid4())[:8]}"

            # Create session if doesn't exist
            session = user_manager.get_session(session_id)
            if not session:
                user_manager.create_session(session_id, user_id)

            # Save user prompt
            user_manager.add_message(session_id, "user", request.query)

        # Process query
        result = bot.process_query(
            user_query=request.query,
            scenario_category=request.scenario
        )

        # Save bot response
        if user_manager and user_id and session_id:
            user_manager.add_message(session_id, "assistant", result["response"])

        # Log to S3
        log_to_s3("/chat", "success", {
            "user_id": user_id,
            "session_id": session_id,
            "query": request.query,
            "scenario": request.scenario,
            "is_crisis": result["is_crisis"],
            "docs_retrieved": result["num_docs_retrieved"]
        })

        return ChatResponse(
            response=result["response"],
            is_crisis=result["is_crisis"],
            num_docs_retrieved=result["num_docs_retrieved"],
            scenario=request.scenario,
            blocked=result.get("blocked", False)
        )

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        log_to_s3("/chat", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Error processing your message")


@app.post("/voice-chat")
async def voice_chat(
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    scenario: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Handle voice chat: (Transcribe if needed) -> RAG -> Synthesize
    """
    start_time = datetime.now()
    logger.info(f"[DEBUG] API: /voice-chat received. Text provided: {text is not None}, User: {user_id}")

    if not voice_service:
        logger.error("[DEBUG] API: Voice service not initialized")
        raise HTTPException(status_code=500, detail="Voice service not initialized")

    try:
        transcript = ""

        # 1. Get Transcript (either from parameters or from audio)
        if text and text.strip():
            logger.info(f"[DEBUG] API: Using direct text input: \"{text}\"")
            transcript = text
        elif audio:
            audio_bytes = await audio.read()
            file_ext = audio.filename.split(".")[-1] if audio.filename and "." in audio.filename else "webm"
            logger.info(f"[DEBUG] API: Calling transcribe_audio (size: {len(audio_bytes)} bytes)...")
            transcript = voice_service.transcribe_audio(audio_bytes, file_ext)

        if not transcript or not transcript.strip():
            logger.info("[DEBUG] API: Empty transcript. Returning fallback response.")
            fallback_text = "I'm sorry, I didn't quite catch that. Could you please say that again?"
            audio_response_bytes = voice_service.synthesize_speech(fallback_text)
            audio_b64 = base64.b64encode(audio_response_bytes).decode("utf-8") if audio_response_bytes else ""

            return {
                "user_transcript": "[Silence/Unclear]",
                "bot_response": fallback_text,
                "audio_base64": audio_b64,
                "is_crisis": False,
                "session_id": session_id
            }

        logger.info(f"[DEBUG] API: Proceeding with transcript: \"{transcript}\"")

        # 2. Process query via RAG
        logger.info("[DEBUG] API: Processing RAG query...")
        rag_start = datetime.now()
        # Handle user tracking/session management
        if user_manager and user_id:
            if not user_manager.get_user(user_id):
                user_manager.create_user(user_id)
            if not session_id:
                session_id = f"sess_{str(uuid.uuid4())[:8]}"
            if not user_manager.get_session(session_id):
                user_manager.create_session(session_id, user_id)
            user_manager.add_message(session_id, "user", transcript)

        result = bot.process_query(user_query=transcript, scenario_category=scenario)
        logger.info(f"[DEBUG] API: RAG processing COMPLETED in {(datetime.now() - rag_start).total_seconds():.2f}s")

        if user_manager and user_id and session_id:
            user_manager.add_message(session_id, "assistant", result["response"])

        # 3. Synthesize response (graceful degradation if Polly fails)
        logger.info("[DEBUG] API: Calling synthesize_speech...")
        synth_start = datetime.now()
        audio_response_bytes = voice_service.synthesize_speech(result["response"])
        audio_b64 = ""

        if audio_response_bytes:
            logger.info(f"[DEBUG] API: Synthesis COMPLETED in {(datetime.now() - synth_start).total_seconds():.2f}s")
            audio_b64 = base64.b64encode(audio_response_bytes).decode("utf-8")
        else:
            logger.warning("[DEBUG] API: Polly synthesis failed — returning text-only response")

        # 4. Return both text and audio (base64)
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"[DEBUG] API: /voice-chat TOTAL in {total_duration:.2f}s. Audio B64 length: {len(audio_b64)}")

        return {
            "user_transcript": transcript,
            "bot_response": result["response"],
            "audio_base64": audio_b64,
            "is_crisis": result["is_crisis"],
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"[DEBUG] API: CRITICAL error in voice_chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear")
async def clear_conversation():
    """Clear conversation history for a fresh start"""
    bot.clear_conversation()
    log_to_s3("/clear", "success", {})
    return {"status": "cleared", "message": "Conversation history cleared"}


@app.get("/user/{user_id}")
async def get_user(user_id: str):
    """Get user profile and session statistics"""
    if not user_manager:
        raise HTTPException(status_code=500, detail="User manager not initialized")

    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    sessions = user_manager.get_user_sessions(user_id)

    log_to_s3(f"/user/{user_id}", "success", {})

    return {
        "user_id": user_id,
        "profile": user,
        "sessions": [
            {
                "session_id": s["session_id"],
                "created_at": s["created_at"],
                "message_count": s["message_count"]
            }
            for s in sessions
        ]
    }


@app.get("/user/{user_id}/session/{session_id}")
async def get_session(user_id: str, session_id: str):
    """Get a specific user session with all messages"""
    if not user_manager:
        raise HTTPException(status_code=500, detail="User manager not initialized")

    session = user_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this user")

    log_to_s3(f"/user/{user_id}/session/{session_id}", "success", {})

    return session


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get bot statistics"""
    stats = bot.get_stats()
    log_to_s3("/stats", "success", {})
    return stats


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    log_to_s3("/health", "success", {})
    return {"status": "ok", "message": "CARE Bot API is running"}


@app.get("/categories")
async def get_categories():
    """Get available scenario categories"""
    log_to_s3("/categories", "success", {})
    return {
        "categories": [
            {"id": "immediate_followup", "name": "Medical Follow-Up", "description": "STI/HIV testing, medical appointments, prophylaxis"},
            {"id": "mental_health", "name": "Mental Health Support", "description": "Counseling, anxiety, sleep issues, trauma support"},
            {"id": "practical_social", "name": "Practical & Social Needs", "description": "Housing, transportation, financial assistance"},
            {"id": "legal_advocacy", "name": "Legal & Advocacy", "description": "Legal help, protection orders, reporting options"},
            {"id": "delayed_ambivalent", "name": "Delayed Follow-Up", "description": "It's been a while, not sure if it still matters"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
