"""
LLM handler for Google Gemini via Vertex AI

Crisis detection is handled via structured JSON output, every Gemini
response includes an is_crisis field assessed by the model.
Keyword-based crisis detection is done upstream in CAREBot.process_query().

Conversation history is stored in DynamoDB (per session) with an
in-memory fallback when DynamoDB is unavailable.
"""
import json
from typing import Dict, Any, List, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part, GenerationConfig
from config.settings import (
    MODEL_NAME, TEMPERATURE, MAX_OUTPUT_TOKENS, MAX_HISTORY_TURNS,
    GCP_PROJECT_ID, GCP_LOCATION
)
from src.utils.dynamodb_history import DynamoDBHistory
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMHandler:
    """Handle interactions with Google Gemini via Vertex AI"""

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_OUTPUT_TOKENS,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not GCP_PROJECT_ID:
            raise ValueError("GCP_PROJECT_ID must be set in environment variables")
        
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        self.model = GenerativeModel(model_name)
        self.generation_config = GenerationConfig(
            temperature=self.temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=self.max_tokens,
            response_mime_type="application/json",
        )
        logger.info(f"Initialized Vertex AI with project: {GCP_PROJECT_ID}, model: {model_name}")

        # DynamoDB history (falls back to in-memory if unavailable)
        self.db_history = DynamoDBHistory()

        # In-memory fallback (used when DynamoDB is unavailable)
        self._memory_history: Dict[str, List[Dict]] = {}
        self.max_history_turns = MAX_HISTORY_TURNS

    # Public API

    def generate_response(
        self,
        prompt: str,
        user_query: str = "",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a Gemini response with structured JSON output.

        Args:
            prompt:     Full RAG/scenario prompt to send to Gemini.
            user_query: Raw user message, stored in conversation history.
            session_id: Session ID for DynamoDB history. If None, no history is stored.

        Returns:
            {
                "text":      str  - response text
                "blocked":   bool - True if Gemini safety filters triggered
                "is_crisis": bool - whether Gemini detected crisis signals
                "error":     str  - only present if an exception occurred
            }
        """
        logger.info(f"Generating response — prompt length: {len(prompt)}")

        try:
            # Build contents with conversation history
            contents = self._build_contents(prompt, session_id)

            # Call Vertex AI
            response = self.model.generate_content(
                contents,
                generation_config=self.generation_config,
            )

            response_text = response.text if hasattr(response, 'text') else ""

            if not response_text:
                logger.warning("Response empty or blocked by Gemini safety filters")
                return {
                    "text":      self._get_fallback_response(),
                    "blocked":   True,
                    "is_crisis": False,
                }

            # Parse structured JSON response
            parsed = self._parse_structured_response(response_text)

            # Store turn in conversation history
            if user_query and session_id:
                self._save_turn(session_id, user_query, parsed["text"])

            logger.info(f"Response generated — length: {len(parsed['text'])}, is_crisis: {parsed['is_crisis']}")

            return {
                "text":      parsed["text"],
                "blocked":   False,
                "is_crisis": parsed["is_crisis"],
            }

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "text":      self._get_fallback_response(),
                "blocked":   False,
                "is_crisis": False,
                "error":     str(e),
            }

    def clear_history(self, session_id: Optional[str] = None) -> None:
        """Clear conversation history for a session."""
        if session_id and self.db_history.available:
            self.db_history.clear_session(session_id)
        elif session_id:
            self._memory_history.pop(session_id, None)
        else:
            self._memory_history.clear()
        logger.info(f"Conversation history cleared for session {session_id or 'all'}")

    def get_history_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Return summary stats about current conversation history."""
        if session_id and self.db_history.available:
            return self.db_history.get_session_stats(session_id)

        if session_id and session_id in self._memory_history:
            msgs = len(self._memory_history[session_id])
            return {
                "total_turns": msgs // 2,
                "max_turns":   self.max_history_turns,
                "messages":    msgs,
            }

        return {
            "total_turns": 0,
            "max_turns":   self.max_history_turns,
            "messages":    0,
        }

    def test_connection(self) -> bool:
        """Test if the Gemini API connection is working."""
        try:
            self.model.generate_content("Hello, this is a test.")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    # Private: response parsing

    @staticmethod
    def _parse_structured_response(response_text: str) -> Dict[str, Any]:
        """
        Parse the structured JSON response from Gemini.

        Expected format: {"response": "...", "is_crisis": true/false}
        Falls back to raw text with is_crisis=False if parsing fails.
        """
        try:
            data = json.loads(response_text)
            text = data.get("response", response_text)
            is_crisis = bool(data.get("is_crisis", False))
            return {"text": text, "is_crisis": is_crisis}
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to parse structured response: {e}")
            return {"text": response_text, "is_crisis": False}

    # Private: history 

    def _build_contents(self, prompt: str, session_id: Optional[str] = None) -> list:
        """
        Build the contents list for Gemini, including conversation history.

        The prompt (system instructions + RAG context + current query) is the
        last user message. Previous turns are prepended so Gemini has context.
        """
        if not session_id:
            return [prompt]

        history = self.get_history(session_id)
        if not history:
            return [prompt]

        # Build multi-turn contents: history turns + current prompt
        contents = []
        for turn in history:
            role = turn.get("role", "user")
            parts = turn.get("parts", [])
            text = parts[0] if parts else ""
            if text:
                contents.append(Content(role=role, parts=[Part.from_text(text)]))

        # Current prompt as the final user message
        contents.append(Content(role="user", parts=[Part.from_text(prompt)]))

        logger.info(f"Built contents with {len(history)} history messages + current prompt")
        return contents

    def _save_turn(self, session_id: str, user_query: str, response_text: str) -> None:
        """Save a turn to DynamoDB or in-memory fallback."""
        if self.db_history.available:
            self.db_history.add_turn(session_id, user_query, response_text)
        else:
            history = self._memory_history.setdefault(session_id, [])
            history.append({"role": "user",  "parts": [user_query]})
            history.append({"role": "model", "parts": [response_text]})
            max_messages = self.max_history_turns * 2
            if len(history) > max_messages:
                self._memory_history[session_id] = history[-max_messages:]

    def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session."""
        if self.db_history.available:
            return self.db_history.get_history(session_id)
        return self._memory_history.get(session_id, [])

    # Private: fallback

    @staticmethod
    def _get_fallback_response(is_crisis: bool = False) -> str:
        """Crisis-aware fallback for when Gemini generation fails."""
        if is_crisis:
            return (
                "I'm having some technical difficulties right now, but I want "
                "you to know that what you're feeling matters and you don't "
                "have to face this alone.\n\n"
                "Please reach out for immediate support:\n\n"
                "- **988 Suicide & Crisis Lifeline**: Call or text **988** (free, 24/7)\n"
                "- **Crisis Text Line**: Text **HOME** to **741741**\n"
                "- **National Sexual Assault Hotline**: 1-800-656-HOPE (4673)\n\n"
                "These lines are available right now."
            )

        return (
            "I apologize, but I'm having trouble responding right now.\n\n"
            "For immediate support, please reach out to:\n\n"
            "- **National Sexual Assault Hotline**: 1-800-656-HOPE (4673)\n"
            "- **Crisis Text Line**: Text \"HELLO\" to 741741\n"
            "- **988 Suicide & Crisis Lifeline**: Call or text 988\n\n"
            "I'm here to help connect you with resources. "
            "Could you try rephrasing your question?"
        )
