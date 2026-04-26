"""
FastAPI server for CARE Bot
Connects the Python RAG backend to the Electron + React frontend
"""
from fastapi import FastAPI, Header, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from main import CAREBot
from src.auth.supabase_auth import verify_supabase_token
from src.utils.logger import get_logger
from src.utils.backup_scheduler import BackupScheduler
from src.utils.voice_service import VoiceService
from config.settings import VECTORSTORE_DIR
import base64
import boto3
import json
import time
from collections import defaultdict
from datetime import datetime
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Import S3Manager from aws/lambda (lambda is reserved, so use dynamic import)
sys.path.insert(0, str(Path(__file__).parent.parent / "aws" / "lambda"))
try:
    from s3_manager import S3Manager  # type: ignore
except ImportError:
    S3Manager = None  # type: ignore

logger = get_logger(__name__)

# Initialize S3 client
try:
    s3_client = boto3.client('s3', region_name='us-east-1')
    S3_LOGS_BUCKET = os.getenv('S3_LOGS_BUCKET', 'care-compass-logs-432732422396-dev')
except:
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

# Allow requests from Electron frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your Electron app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory metrics accumulator (resets on server restart)
# ---------------------------------------------------------------------------
class _ServerMetrics:
    def __init__(self):
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.total_crisis_events: int = 0
        self.response_times_ms: List[float] = []
        self.category_counts: dict = defaultdict(int)
        self.docs_retrieved: List[int] = []
        self.voice_requests: int = 0
        self.server_start_time: str = datetime.now().isoformat()

    def record_chat(self, response_time_ms: float, is_crisis: bool, scenario: Optional[str],
                    docs_retrieved: int, is_error: bool = False):
        self.total_requests += 1
        if is_error:
            self.total_errors += 1
            return
        self.response_times_ms.append(response_time_ms)
        self.docs_retrieved.append(docs_retrieved)
        if is_crisis:
            self.total_crisis_events += 1
        if scenario:
            self.category_counts[scenario] += 1

    def record_voice(self, response_time_ms: float, is_crisis: bool):
        self.voice_requests += 1
        self.total_requests += 1
        self.response_times_ms.append(response_time_ms)
        if is_crisis:
            self.total_crisis_events += 1

    def to_dict(self) -> dict:
        times = self.response_times_ms
        docs = self.docs_retrieved
        return {
            "server_start_time": self.server_start_time,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "total_crisis_events": self.total_crisis_events,
            "voice_requests": self.voice_requests,
            "response_times": {
                "count": len(times),
                "avg_ms": round(sum(times) / len(times), 1) if times else 0,
                "min_ms": round(min(times), 1) if times else 0,
                "max_ms": round(max(times), 1) if times else 0,
                "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 1) if len(times) >= 20 else None,
            },
            "docs_retrieved": {
                "avg": round(sum(docs) / len(docs), 1) if docs else 0,
            },
            "category_counts": dict(self.category_counts),
            "crisis_rate": round(self.total_crisis_events / max(self.total_requests, 1) * 100, 1),
            "error_rate": round(self.total_errors / max(self.total_requests, 1) * 100, 1),
        }

_metrics = _ServerMetrics()

# Initialize bot, backup scheduler, and voice service
bot = None
backup_scheduler = None
voice_service = None


@app.on_event("startup")
async def startup():
    """Initialize CARE Bot, voice service, and backup scheduler on server startup"""
    global bot, backup_scheduler, voice_service
    logger.info("Starting CARE Bot API...")
    bot = CAREBot()

    # Initialize voice service
    try:
        voice_service = VoiceService()
        logger.info("Voice service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize voice service: {e}")

    
    # Initialize vector store if empty
    stats = bot.get_stats()
    if stats["vector_store"]["document_count"] == 0:
        logger.info("Vector store empty. Initializing...")
        bot.initialize_vector_store()
    
    # Initialize backup scheduler
    try:
        s3_manager = S3Manager(region="us-east-1")
        backup_scheduler = BackupScheduler(
            vectorstore_path=str(VECTORSTORE_DIR),
            s3_manager=s3_manager,
            backup_interval_hours=168
        )
        backup_scheduler.start()
        logger.info("ChromaDB backup scheduler started (weekly backups to S3)")
    except Exception as e:
        logger.warning(f"Could not start backup scheduler: {e}")
    
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
    scenario: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    is_crisis: bool
    num_docs_retrieved: int
    scenario: Optional[str] = None
    blocked: bool = False
    processing_time_ms: Optional[int] = None

class StatsResponse(BaseModel):
    vector_store: dict
    retriever_top_k: int
    llm_model: str
    crisis_keywords: int
    conversation_history: dict


# --- API Endpoints ---

def _resolve_session_id(request: ChatRequest, authorization: Optional[str] = None) -> Optional[str]:
    """
    Resolve session_id from JWT (authenticated) or request body (guest).
    Priority: JWT user ID > request body session_id
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user_id = verify_supabase_token(token)
        if user_id:
            return user_id

    return request.session_id


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Send a message to CARE Bot and get a response

    - **query**: User's message
    - **scenario**: Optional category (immediate_followup, mental_health, practical_social, legal_advocacy, delayed_ambivalent)
    - **session_id**: Optional session ID (for guest users)
    - **Authorization**: Optional Bearer token (for authenticated users)
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_id = _resolve_session_id(request, authorization)

    try:
        t_start = time.perf_counter()
        result = bot.process_query(
            user_query=request.query,
            scenario_category=request.scenario,
            session_id=session_id,
        )
        processing_time_ms = int((time.perf_counter() - t_start) * 1000)

        _metrics.record_chat(
            response_time_ms=processing_time_ms,
            is_crisis=result["is_crisis"],
            scenario=request.scenario,
            docs_retrieved=result["num_docs_retrieved"],
        )
        
        # Log to S3
        log_to_s3("/chat", "success", {
            "query": request.query,
            "response": result["response"],
            "scenario": request.scenario,
            "is_crisis": result["is_crisis"],
            "docs_retrieved": result["num_docs_retrieved"],
            "processing_time_ms": processing_time_ms,
        })
        
        return ChatResponse(
            response=result["response"],
            is_crisis=result["is_crisis"],
            num_docs_retrieved=result["num_docs_retrieved"],
            scenario=request.scenario,
            blocked=result.get("blocked", False),
            processing_time_ms=processing_time_ms,
        )
    
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        _metrics.record_chat(response_time_ms=0, is_crisis=False, scenario=request.scenario,
                             docs_retrieved=0, is_error=True)
        log_to_s3("/chat", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Error processing your message")


@app.post("/clear")
async def clear_conversation(
    authorization: Optional[str] = Header(None),
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Clear conversation history for a session"""
    # Prefer JWT user ID over header session_id
    if authorization and authorization.startswith("Bearer "):
        user_id = verify_supabase_token(authorization[7:])
        if user_id:
            session_id = user_id
    bot.clear_conversation(session_id=session_id)
    log_to_s3("/clear", "success", {"session_id": session_id})
    return {"status": "cleared", "message": "Conversation history cleared"}


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


@app.post("/voice-chat")
async def voice_chat(
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    scenario: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
):
    """
    Voice chat endpoint: transcribe audio (or accept text directly) → RAG → synthesize response.

    Returns JSON with:
    - user_transcript: what the user said
    - bot_response: CARE Bot's reply
    - audio_base64: base64-encoded MP3 of the reply (empty string if synthesis unavailable)
    - is_crisis: whether crisis indicators were detected
    """
    if not voice_service:
        raise HTTPException(status_code=503, detail="Voice service not available")

    start_time = datetime.now()

    # Resolve session from JWT or form field
    if authorization and authorization.startswith("Bearer "):
        jwt_user = verify_supabase_token(authorization[7:])
        if jwt_user:
            session_id = jwt_user

    try:
        # 1. Get transcript
        transcript = ""
        if text and text.strip():
            transcript = text.strip()
        elif audio:
            audio_bytes = await audio.read()
            file_ext = "webm"
            if audio.filename and "." in audio.filename:
                file_ext = audio.filename.rsplit(".", 1)[-1]
            transcript = voice_service.transcribe_audio(audio_bytes, file_ext) or ""

        # Handle empty/silent input
        if not transcript:
            fallback = "I'm sorry, I didn't quite catch that. Could you please say that again?"
            audio_bytes_out = voice_service.synthesize_speech(fallback)
            audio_b64 = base64.b64encode(audio_bytes_out).decode() if audio_bytes_out else ""
            return {
                "user_transcript": "[Silence/Unclear]",
                "bot_response": fallback,
                "audio_base64": audio_b64,
                "is_crisis": False,
                "session_id": session_id,
            }

        # 2. Process via RAG pipeline
        result = bot.process_query(
            user_query=transcript,
            scenario_category=scenario,
            session_id=session_id,
        )

        # 3. Synthesize response audio
        audio_bytes_out = voice_service.synthesize_speech(result["response"])
        audio_b64 = base64.b64encode(audio_bytes_out).decode() if audio_bytes_out else ""

        duration = (datetime.now() - start_time).total_seconds()
        duration_ms = int(duration * 1000)
        logger.info(f"/voice-chat completed in {duration:.2f}s. Crisis: {result['is_crisis']}")

        _metrics.record_voice(response_time_ms=duration_ms, is_crisis=result["is_crisis"])

        log_to_s3("/voice-chat", "success", {
            "transcript": transcript,
            "response": result["response"],
            "scenario": scenario,
            "is_crisis": result["is_crisis"],
        })

        return {
            "user_transcript": transcript,
            "bot_response": result["response"],
            "audio_base64": audio_b64,
            "is_crisis": result["is_crisis"],
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"Error in voice_chat: {e}")
        log_to_s3("/voice-chat", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Error processing voice message")



@app.get("/admin/dashboard")
async def admin_dashboard():
    """
    Admin dashboard data: aggregated server metrics + current bot stats.
    NOTE: No auth guard for local debugging. Add auth before deploying.
    """
    bot_stats = bot.get_stats() if bot else {}
    return {
        "server_metrics": _metrics.to_dict(),
        "bot_stats": bot_stats,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)