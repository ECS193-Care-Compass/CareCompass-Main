"""
Mock CARE Bot API for Testing Frontend
Returns test responses without initializing full CAREBot
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime
import boto3
import os

app = FastAPI(title="CARE Bot API (Mock)")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# S3 client for logging
try:
    s3_client = boto3.client('s3', region_name='us-east-1')
    S3_BUCKET = os.getenv('S3_DOCUMENTS_BUCKET', 'care-compass-documents-432732422396-dev')
except:
    s3_client = None
    S3_BUCKET = None

# Models
class ChatRequest(BaseModel):
    query: Optional[str] = None
    message: Optional[str] = None  # Alternative field name from frontend
    scenario: Optional[str] = None
    
    class Config:
        # Handle both 'query' and 'message' field names
        populate_by_name = True

class ChatResponse(BaseModel):
    response: str
    is_crisis: bool
    num_docs_retrieved: int
    scenario: Optional[str] = None
    blocked: bool = False

# Mock responses by scenario
MOCK_RESPONSES = {
    "mental_health": {
        "response": "I understand you're experiencing mental health concerns. This is an important issue to address. Would you like information about:\n\n1. **Therapy & Counseling** - Evidence-based treatments like CBT, EMDR\n2. **Immediate Support** - Crisis hotlines and peer support\n3. **Practical Resources** - Apps, workbooks, support groups\n\nWhat would be most helpful for you right now?",
        "is_crisis": False,
        "num_docs_retrieved": 3,
    },
    "immediate_followup": {
        "response": "For immediate follow-up after a traumatic event, here are key next steps:\n\n✓ **Medical Care** - Get checked by a healthcare provider\n✓ **Testing** - STI/HIV testing if applicable (can be done anonymously)\n✓ **Documentation** - Consider medical/legal documentation\n✓ **Support** - Reach out to someone you trust\n\nWould you like help with any of these?",
        "is_crisis": False,
        "num_docs_retrieved": 2,
    },
    "practical_social": {
        "response": "I can help with practical and social needs. Common areas include:\n\n🏠 **Housing** - Emergency shelter, transitional housing\n💰 **Financial** - Emergency assistance programs\n🚗 **Transportation** - Ride services, public transit assistance\n📱 **Communication** - Phone support, technology access\n\nWhich area would be most helpful for you right now?",
        "is_crisis": False,
        "num_docs_retrieved": 2,
    },
    "legal_advocacy": {
        "response": "Legal support and advocacy options available:\n\n⚖️ **Legal Services** - Free legal consultation and representation\n🛡️ **Protection Orders** - Information on protective orders\n📋 **Reporting** - Guidance on reporting options\n👨‍⚖️ **Advocacy** - Victim advocates to support your process\n\nWhich of these would be most helpful?",
        "is_crisis": False,
        "num_docs_retrieved": 2,
    },
    "delayed_ambivalent": {
        "response": "It's never too late to seek support, even if time has passed. Many survivors experience delayed reactions or ambivalence about moving forward, and that's completely normal.\n\n**Why reach out now?**\n- Processing takes time\n- New triggers can emerge later\n- Support is always available\n\nWhere would you like to start?",
        "is_crisis": False,
        "num_docs_retrieved": 2,
    }
}

def log_to_s3(endpoint: str, status: str, data: dict):
    """Log API calls to S3"""
    if not s3_client or not S3_BUCKET:
        return
    
    try:
        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "endpoint": endpoint,
            "status": status,
            "data": data
        }
        
        key = f"logs/interactions/{timestamp.split('T')[0]}/{timestamp}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(log_entry, indent=2),
            ContentType='application/json'
        )
    except Exception as e:
        print(f"Warning: Failed to log to S3: {e}")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "CARE Bot API is running (Mock Mode)",
        "mode": "mock_testing"
    }

@app.get("/categories")
async def categories():
    """Get scenario categories"""
    return {
        "categories": [
            {
                "id": "immediate_followup",
                "name": "Medical Follow-Up",
                "description": "STI/HIV testing, medical appointments, prophylaxis"
            },
            {
                "id": "mental_health",
                "name": "Mental Health Support",
                "description": "Counseling, anxiety, sleep issues, trauma support"
            },
            {
                "id": "practical_social",
                "name": "Practical & Social Needs",
                "description": "Housing, transportation, financial assistance"
            },
            {
                "id": "legal_advocacy",
                "name": "Legal & Advocacy",
                "description": "Legal help, protection orders, reporting options"
            },
            {
                "id": "delayed_ambivalent",
                "name": "Delayed Follow-Up",
                "description": "It's been a while, not sure if it still matters"
            }
        ]
    }

def detect_scenario_from_query(query: str) -> str:
    """Detect scenario from query keywords"""
    query_lower = query.lower()
    
    # Practical/social keywords (check first for higher priority)
    if any(word in query_lower for word in ["housing", "shelter", "transportation", "money", "financial", "food", "transport", "ride"]):
        return "practical_social"
    
    # Legal keywords
    if any(word in query_lower for word in ["legal", "lawyer", "court", "police", "report", "protection", "order", "advocate"]):
        return "legal_advocacy"
    
    # Immediate followup keywords (medical/test context)
    if any(word in query_lower for word in ["hiv", "std", "sti", "medical", "doctor", "appointment", "prophylaxis"]):
        return "immediate_followup"
    
    # Mental health keywords
    if any(word in query_lower for word in ["anxiety", "depression", "sleep", "ptsd", "stress", "trauma", "therapy", "counseling", "mental"]):
        return "mental_health"
    
    # Delayed/ambivalent keywords
    if any(word in query_lower for word in ["already happened", "past", "old story", "while ago", "not sure", "unsure", "time has passed"]):
        return "delayed_ambivalent"
    
    return "mental_health"

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint - returns mock response"""
    # Handle both 'query' and 'message' field names
    user_input = request.query or request.message or ""
    print(f"Chat request: {user_input}")
    
    # Check for crisis keywords
    crisis_keywords = ["suicide", "harm", "kill myself", "want to die", "emergency"]
    is_crisis = any(keyword in user_input.lower() for keyword in crisis_keywords)
    
    if is_crisis:
        response_text = "I hear that you're in crisis right now. Please reach out for immediate help:\n\n🚨 **National Crisis Hotline: 988** (US)\n🚨 **International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/\n\nYour life matters. Trained counselors are available 24/7 to help."
        num_docs = 0
        scenario = "crisis"
    else:
        # Detect scenario from query content if not provided
        scenario = request.scenario or detect_scenario_from_query(user_input)
        mock_data = MOCK_RESPONSES.get(scenario, MOCK_RESPONSES["mental_health"])
        response_text = mock_data["response"]
        num_docs = mock_data["num_docs_retrieved"]
    
    response = {
        "response": response_text,
        "is_crisis": is_crisis,
        "num_docs_retrieved": num_docs,
        "scenario": request.scenario,
        "blocked": False,
        "source": "mock_testing"
    }
    
    # Log to S3
    log_to_s3("/chat", "success", {
        "query": user_input,
        "scenario": scenario,
        "is_crisis": is_crisis
    })
    
    return response

@app.post("/clear")
async def clear():
    """Clear conversation history"""
    log_to_s3("/clear", "success", {})
    return {
        "status": "cleared",
        "message": "Conversation history cleared"
    }

@app.get("/stats")
async def stats():
    """Get bot statistics"""
    log_to_s3("/stats", "success", {})
    return {
        "vector_store": {
            "document_count": 42,
            "collection_name": "care_bot_documents"
        },
        "retriever_top_k": 3,
        "llm_model": "gemini-2.5-flash (mock mode)",
        "crisis_keywords": 15,
        "conversation_history": {
            "total_turns": 0,
            "max_turns": 20,
            "messages": 0
        },
        "mode": "mock_testing"
    }

@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle CORS preflight requests"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Mock CARE Bot API...")
    print("📝 All API calls will be logged to S3")
    uvicorn.run(app, host="0.0.0.0", port=8000)
