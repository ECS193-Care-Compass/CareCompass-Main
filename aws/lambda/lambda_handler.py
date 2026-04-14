"""
AWS Lambda Handler for CARE Bot
Converts FastAPI endpoints to Lambda handler for API Gateway integration
"""
import json
import logging
import os
from typing import Dict, Any, Optional
import sys
import base64
from datetime import datetime
from email import message_from_bytes
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 for logging interactions
s3_client = boto3.client('s3', region_name='us-east-1')
S3_LOGS_BUCKET = os.getenv('S3_LOGS_BUCKET', 'care-compass-logs-432732422396-dev')

# Import your CARE Bot - will be in Lambda layer
try:
    from main import CAREBot
except ImportError as e:
    logger.error(f"Failed to import CAREBot: {e}")
    CAREBot = None

# Import Supabase auth
try:
    from src.auth.supabase_auth import verify_supabase_token
except ImportError as e:
    logger.warning(f"Failed to import supabase_auth: {e}")
    verify_supabase_token = None

# Global instances (persist across warm Lambda invocations)
bot_instance = None
voice_service_instance = None


def _resolve_session_id(event: Dict[str, Any], body: Dict[str, Any]) -> Optional[str]:
    """
    Resolve session_id from JWT (authenticated) or request body (guest).
    Priority: JWT user ID > request body session_id
    """
    # Try Authorization header first
    headers = event.get("headers", {}) or {}
    # API Gateway lowercases headers
    auth_header = headers.get("authorization") or headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer ") and verify_supabase_token:
        token = auth_header[7:]
        user_id = verify_supabase_token(token)
        if user_id:
            return user_id

    # Fall back to session_id in request body
    return body.get("session_id")


def log_interaction_to_s3(event: Dict[str, Any], response: Dict[str, Any], status: str = "success"):
    """Log API interactions to S3 for audit trail and debugging"""
    try:
        timestamp = datetime.utcnow().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "status": status,
            "method": event.get("requestContext", {}).get("http", {}).get("method"),
            "path": event.get("rawPath") or event.get("path", "/"),
            "request_id": event.get("requestContext", {}).get("requestId"),
            "response_status": response.get("statusCode", "unknown"),
            "body": event.get("body") if event.get("body") and "password" not in str(event.get("body")).lower() else "[redacted]",
        }

        key = f"interactions/{timestamp.split('T')[0]}/{timestamp}.json"
        s3_client.put_object(
            Bucket=S3_LOGS_BUCKET,
            Key=key,
            Body=json.dumps(log_entry, indent=2),
            ContentType='application/json'
        )

        logger.info(f"Logged interaction to S3: {key}")
    except Exception as e:
        logger.warning(f"Failed to log interaction to S3: {str(e)}")


def initialize_bot():
    """Initialize CARE Bot on first invocation"""
    global bot_instance

    if bot_instance is not None:
        return bot_instance

    logger.info("Initializing CARE Bot...")
    try:
        bot_instance = CAREBot()

        stats = bot_instance.get_stats()
        doc_count = stats.get("vector_store", {}).get("document_count", 0)
        if doc_count == 0:
            logger.warning("Vector store has no documents. Using bot with empty RAG.")

        logger.info(f"CARE Bot initialized successfully with {doc_count} documents")
        return bot_instance

    except Exception as e:
        logger.error(f"Failed to initialize CARE Bot: {str(e)}", exc_info=True)
        logger.warning("Returning bot with fallback mode due to initialization error")

        try:
            if CAREBot is not None:
                bot_instance = CAREBot()
                return bot_instance
        except:
            pass

        raise


def build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Build Lambda HTTP response with CORS headers"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Session-ID"
        },
        "body": json.dumps(body)
    }


def handle_cors_preflight(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle CORS preflight requests"""
    return build_response(200, {"message": "OK"})


def handle_chat(event: Dict[str, Any], bot: Any) -> Dict[str, Any]:
    """Handle /chat POST requests"""
    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})

        query = body.get("query", "").strip()
        scenario = body.get("scenario")

        if not query:
            return build_response(400, {"error": "Query cannot be empty"})

        session_id = _resolve_session_id(event, body)
        logger.info(f"Processing query: {query[:50]}... (session: {session_id[:12] if session_id else 'none'})")

        result = bot.process_query(
            user_query=query,
            scenario_category=scenario,
            session_id=session_id,
        )

        response = {
            "response": result["response"],
            "is_crisis": result["is_crisis"],
            "num_docs_retrieved": result["num_docs_retrieved"],
            "scenario": scenario,
            "blocked": result.get("blocked", False)
        }

        return build_response(200, response)

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        return build_response(500, {"error": "Error processing your message"})


def handle_clear(event: Dict[str, Any], bot: Any) -> Dict[str, Any]:
    """Handle /clear POST requests"""
    try:
        # Parse body for session_id
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"]) if event.get("body") else {}
        else:
            body = event.get("body", {})

        session_id = _resolve_session_id(event, body)

        # Also check X-Session-ID header as fallback
        if not session_id:
            headers = event.get("headers", {}) or {}
            session_id = headers.get("x-session-id") or headers.get("X-Session-ID")

        bot.clear_conversation(session_id=session_id)
        return build_response(200, {"status": "cleared", "message": "Conversation history cleared"})
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}")
        return build_response(500, {"error": "Error clearing conversation"})


def handle_stats(bot: Any) -> Dict[str, Any]:
    """Handle /stats GET requests"""
    try:
        stats = bot.get_stats()
        return build_response(200, stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return build_response(200, {
            "vector_store": {
                "document_count": 0,
                "collection_name": "care_bot_documents"
            },
            "retriever_top_k": 3,
            "llm_model": "gemini-2.5-flash",
            "crisis_keywords": 0,
            "conversation_history": {
                "total_turns": 0,
                "max_turns": 20,
                "messages": 0
            },
            "error": str(e),
            "note": "Using fallback stats due to initialization issue"
        })


def handle_health() -> Dict[str, Any]:
    """Handle /health GET requests"""
    return build_response(200, {"status": "ok", "message": "CARE Bot API is running"})


def get_voice_service():
    """Lazily initialize and cache the VoiceService."""
    global voice_service_instance
    if voice_service_instance is not None:
        return voice_service_instance
    try:
        from src.utils.voice_service import VoiceService
        voice_service_instance = VoiceService()
        logger.info("VoiceService initialized")
    except Exception as e:
        logger.warning(f"VoiceService not available: {e}")
    return voice_service_instance


def _parse_multipart(raw_body: bytes, content_type: str):
    """
    Parse multipart/form-data using the standard email module.
    Returns (fields: dict[str, str], files: dict[str, tuple[str, bytes]])
    """
    msg = message_from_bytes(
        f"Content-Type: {content_type}\r\n\r\n".encode() + raw_body
    )
    fields: Dict[str, str] = {}
    files: Dict[str, tuple] = {}

    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        disp = part.get("Content-Disposition", "")
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        if "filename=" in disp:
            filename = part.get_param("filename", header="content-disposition") or ""
            files[name] = (filename, part.get_payload(decode=True) or b"")
        else:
            payload = part.get_payload(decode=False)
            fields[name] = payload.strip() if isinstance(payload, str) else ""

    return fields, files


def handle_voice_chat(event: Dict[str, Any], bot: Any) -> Dict[str, Any]:
    """Handle /voice-chat POST — transcribe audio → RAG → synthesize response."""
    headers = event.get("headers", {}) or {}
    content_type = (
        headers.get("content-type") or headers.get("Content-Type") or ""
    )

    raw_body_str = event.get("body") or ""
    is_base64_encoded = event.get("isBase64Encoded", False)

    if is_base64_encoded:
        raw_body = base64.b64decode(raw_body_str)
    else:
        raw_body = raw_body_str.encode("utf-8") if isinstance(raw_body_str, str) else raw_body_str

    # Parse multipart form data
    fields, files = _parse_multipart(raw_body, content_type)

    text_input = fields.get("text", "").strip()
    scenario = fields.get("scenario") or None
    session_id = fields.get("session_id") or None

    # Resolve session from JWT if present
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer ") and verify_supabase_token:
        jwt_user = verify_supabase_token(auth_header[7:])
        if jwt_user:
            session_id = jwt_user

    voice_svc = get_voice_service()
    if not voice_svc:
        return build_response(503, {"error": "Voice service not available"})

    try:
        # 1. Transcribe
        transcript = ""
        if text_input:
            transcript = text_input
        elif "audio" in files:
            filename, audio_bytes = files["audio"]
            file_ext = filename.rsplit(".", 1)[-1] if "." in filename else "webm"
            transcript = voice_svc.transcribe_audio(audio_bytes, file_ext) or ""

        # Handle silence/empty
        if not transcript:
            fallback = "I'm sorry, I didn't quite catch that. Could you please say that again?"
            audio_out = voice_svc.synthesize_speech(fallback)
            audio_b64 = base64.b64encode(audio_out).decode() if audio_out else ""
            return build_response(200, {
                "user_transcript": "[Silence/Unclear]",
                "bot_response": fallback,
                "audio_base64": audio_b64,
                "is_crisis": False,
                "session_id": session_id,
            })

        # 2. RAG
        result = bot.process_query(
            user_query=transcript,
            scenario_category=scenario,
            session_id=session_id,
        )

        # 3. Synthesize
        audio_out = voice_svc.synthesize_speech(result["response"])
        audio_b64 = base64.b64encode(audio_out).decode() if audio_out else ""

        return build_response(200, {
            "user_transcript": transcript,
            "bot_response": result["response"],
            "audio_base64": audio_b64,
            "is_crisis": result["is_crisis"],
            "session_id": session_id,
        })

    except Exception as e:
        logger.error(f"Error in voice_chat: {e}", exc_info=True)
        return build_response(500, {"error": "Error processing voice message"})


def handle_categories() -> Dict[str, Any]:
    """Handle /categories GET requests"""
    categories = {
        "categories": [
            {"id": "immediate_followup", "name": "Medical Follow-Up", "description": "STI/HIV testing, medical appointments, prophylaxis"},
            {"id": "mental_health", "name": "Mental Health Support", "description": "Counseling, anxiety, sleep issues, trauma support"},
            {"id": "practical_social", "name": "Practical & Social Needs", "description": "Housing, transportation, financial assistance"},
            {"id": "legal_advocacy", "name": "Legal & Advocacy", "description": "Legal help, protection orders, reporting options"},
            {"id": "delayed_ambivalent", "name": "Delayed Follow-Up", "description": "It's been a while, not sure if it still matters"},
        ]
    }
    return build_response(200, categories)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for API Gateway integration"""
    logger.info(f"Received event: {json.dumps(event)}")

    http_method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "GET")
    raw_path = event.get("rawPath") or event.get("path", "/")
    path = raw_path

    # Remove stage prefix (e.g., "/prod" or "/dev") for API Gateway
    if path.startswith("/") and "rawPath" not in event:
        path_parts = path.split("/")
        if len(path_parts) > 1 and path_parts[1] in ["prod", "dev", "test"]:
            path = "/" + "/".join(path_parts[2:])

    logger.info(f"Method: {http_method}, Path: {path}")

    response = None
    try:
        if http_method == "OPTIONS":
            response = handle_cors_preflight(event)
            return response

        if path == "/health" and http_method == "GET":
            response = handle_health()
            log_interaction_to_s3(event, response, "health_check")
            return response

        elif path == "/categories" and http_method == "GET":
            response = handle_categories()
            log_interaction_to_s3(event, response, "categories_request")
            return response

        bot = initialize_bot()

        if path == "/chat" and http_method == "POST":
            response = handle_chat(event, bot)
            log_interaction_to_s3(event, response, "chat_request")
            return response

        elif path == "/voice-chat" and http_method == "POST":
            response = handle_voice_chat(event, bot)
            log_interaction_to_s3(event, response, "voice_chat_request")
            return response

        elif path == "/clear" and http_method == "POST":
            response = handle_clear(event, bot)
            log_interaction_to_s3(event, response, "clear_request")
            return response

        elif path == "/stats" and http_method == "GET":
            response = handle_stats(bot)
            log_interaction_to_s3(event, response, "stats_request")
            return response

        else:
            logger.warning(f"Route not found: {http_method} {path}")
            response = build_response(404, {"error": "Endpoint not found"})
            log_interaction_to_s3(event, response, "not_found")
            return response

    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        response = build_response(500, {"error": "Internal server error"})
        log_interaction_to_s3(event, response, "error")
        return response