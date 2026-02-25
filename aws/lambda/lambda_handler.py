"""
AWS Lambda Handler for CARE Bot
Converts FastAPI endpoints to Lambda handler for API Gateway integration
"""
import json
import logging
import os
from typing import Dict, Any
import sys
from datetime import datetime
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

# Global bot instance (persists across warm Lambda invocations)
bot_instance = None


def log_interaction_to_s3(event: Dict[str, Any], response: Dict[str, Any], status: str = "success"):
    """
    Log API interactions to S3 for audit trail and debugging
    
    Args:
        event: The API Gateway event
        response: The response returned
        status: Status of the interaction (success, error, etc.)
    """
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
        
        # Upload to S3
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
        # Try to import and initialize the bot
        bot_instance = CAREBot()
        
        # Check if vector store has documents
        stats = bot_instance.get_stats()
        doc_count = stats.get("vector_store", {}).get("document_count", 0)
        if doc_count == 0:
            logger.warning("Vector store has no documents. Using bot with empty RAG.")
        
        logger.info(f"CARE Bot initialized successfully with {doc_count} documents")
        return bot_instance
    
    except Exception as e:
        logger.error(f"Failed to initialize CARE Bot: {str(e)}", exc_info=True)
        # Return a minimal bot that can still respond, even without vector store
        # This allows the Lambda to continue serving requests
        logger.warning("Returning bot with fallback mode due to initialization error")
        
        # Try to return minimal bot instance if available
        try:
            if CAREBot is not None:
                bot_instance = CAREBot()
                return bot_instance
        except:
            pass
        
        raise


def build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Lambda HTTP response with CORS headers
    
    Args:
        status_code: HTTP status code
        body: Response body (will be JSON stringified)
    
    Returns:
        Lambda proxy response
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body)
    }


def handle_cors_preflight(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle CORS preflight requests"""
    return build_response(200, {"message": "OK"})


def handle_chat(event: Dict[str, Any], bot: Any) -> Dict[str, Any]:
    """
    Handle /chat POST requests
    
    Event body should contain:
    {
        "query": "user message",
        "scenario": "optional_scenario_category"
    }
    """
    try:
        # Parse request body
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", {})
        
        query = body.get("query", "").strip()
        scenario = body.get("scenario")
        
        if not query:
            return build_response(400, {"error": "Query cannot be empty"})
        
        logger.info(f"Processing query: {query[:50]}...")
        
        # Process query
        result = bot.process_query(
            user_query=query,
            scenario_category=scenario
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


def handle_clear(bot: Any) -> Dict[str, Any]:
    """Handle /clear POST requests"""
    try:
        bot.clear_conversation()
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
        # Return basic stats even if bot fails to initialize properly
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


def handle_categories() -> Dict[str, Any]:
    """Handle /categories GET requests"""
    categories = {
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
    return build_response(200, categories)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for API Gateway integration
    
    Args:
        event: API Gateway proxy event or Lambda Function URL event
        context: Lambda context object
    
    Returns:
        HTTP response in API Gateway proxy format
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract HTTP method and path - handle both API Gateway and Lambda Function URL formats
    http_method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "GET")
    raw_path = event.get("rawPath") or event.get("path", "/")
    path = raw_path
    
    # Remove stage prefix (e.g., "/prod" or "/dev") for API Gateway
    if path.startswith("/") and "rawPath" not in event:
        path_parts = path.split("/")
        # Handle stage-prefixed paths
        if len(path_parts) > 1 and path_parts[1] in ["prod", "dev", "test"]:
            path = "/" + "/".join(path_parts[2:])
    
    logger.info(f"Method: {http_method}, Path: {path}")
    
    response = None
    try:
        # Handle CORS preflight
        if http_method == "OPTIONS":
            response = handle_cors_preflight(event)
            return response
        
        # Handle routes that don't need bot initialization
        if path == "/health" and http_method == "GET":
            response = handle_health()
            log_interaction_to_s3(event, response, "health_check")
            return response
        
        elif path == "/categories" and http_method == "GET":
            response = handle_categories()
            log_interaction_to_s3(event, response, "categories_request")
            return response
        
        # Initialize bot only for routes that need it
        bot = initialize_bot()
        
        # Route to appropriate handler
        if path == "/chat" and http_method == "POST":
            response = handle_chat(event, bot)
            log_interaction_to_s3(event, response, "chat_request")
            return response
        
        elif path == "/clear" and http_method == "POST":
            response = handle_clear(bot)
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
