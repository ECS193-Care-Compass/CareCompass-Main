"""
FastAPI server for CARE Bot
Connects the Python RAG backend to the Electron + React frontend
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from main import CAREBot
from src.utils.logger import get_logger
from src.utils.backup_scheduler import BackupScheduler
from config.settings import VECTORSTORE_DIR
import boto3
import json
from datetime import datetime
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Import S3Manager from aws/lambda (lambda is reserved, so use dynamic import)
sys.path.insert(0, str(Path(__file__).parent / "aws" / "lambda"))
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

# Initialize bot and backup scheduler
bot = None
backup_scheduler = None


@app.on_event("startup")
async def startup():
    """Initialize CARE Bot and backup scheduler on server startup"""
    global bot, backup_scheduler
    logger.info("Starting CARE Bot API...")
    bot = CAREBot(warmup_crisis_detector=False)

    
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
    - **scenario**: Optional category (immediate_followup, mental_health, practical_social, legal_advocacy, delayed_ambivalent)
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        result = bot.process_query(
            user_query=request.query,
            scenario_category=request.scenario
        )
        
        # Log to S3
        log_to_s3("/chat", "success", {
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


@app.post("/clear")
async def clear_conversation():
    """Clear conversation history for a fresh start"""
    bot.clear_conversation()
    log_to_s3("/clear", "success", {})
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)