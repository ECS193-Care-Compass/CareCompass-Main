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

logger = get_logger(__name__)

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

# Initialize bot (once on startup)
bot = None


@app.on_event("startup")
async def startup():
    """Initialize CARE Bot on server startup"""
    global bot
    logger.info("Starting CARE Bot API...")
    bot = CAREBot()
    
    # Initialize vector store if empty
    stats = bot.get_stats()
    if stats["vector_store"]["document_count"] == 0:
        logger.info("Vector store empty. Initializing...")
        bot.initialize_vector_store()
    
    logger.info("CARE Bot API ready")


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
        
        return ChatResponse(
            response=result["response"],
            is_crisis=result["is_crisis"],
            num_docs_retrieved=result["num_docs_retrieved"],
            scenario=request.scenario,
            blocked=result.get("blocked", False)
        )
    
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing your message")


@app.post("/clear")
async def clear_conversation():
    """Clear conversation history for a fresh start"""
    bot.clear_conversation()
    return {"status": "cleared", "message": "Conversation history cleared"}


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get bot statistics"""
    return bot.get_stats()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "CARE Bot API is running"}


@app.get("/categories")
async def get_categories():
    """Get available scenario categories"""
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