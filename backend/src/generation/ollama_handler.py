"""
LLM handler for local Ollama inference.

Drop-in alternative to LLMHandler (Google Gemini).  All user data stays
on-device — nothing is sent to an external API.
"""
import requests
from typing import Dict, Any, List
from config.settings import OLLAMA_MODEL, OLLAMA_BASE_URL
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaHandler:
    """Handle interactions with a local Ollama instance."""

    def __init__(
        self,
        model_name: str = OLLAMA_MODEL,
        base_url: str = OLLAMA_BASE_URL,
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

        # Conversation history (same structure as LLMHandler)
        self.conversation_history: List[Dict] = []
        self.max_history_turns = 10

        logger.info(f"Initialized OllamaHandler with model: {model_name} at {self.base_url}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_response(
        self,
        prompt: str,
        user_query: str = "",
        is_crisis: bool = False,
    ) -> Dict[str, Any]:
        """Generate a response from the local Ollama model."""
        logger.info(f"Generating response — prompt length: {len(prompt)}, is_crisis: {is_crisis}")

        if is_crisis:
            prompt = self._inject_crisis_instruction(prompt)

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            response_text = resp.json().get("response", "")

            if not response_text:
                logger.warning("Empty response from Ollama")
                return {
                    "text": self._get_fallback_response(is_crisis),
                    "blocked": True,
                    "is_crisis": is_crisis,
                }

            if user_query:
                self._add_to_history(user_query, response_text)

            logger.info(f"Response generated — length: {len(response_text)}")

            return {
                "text": response_text,
                "blocked": False,
                "is_crisis": is_crisis,
            }

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "text": self._get_fallback_response(is_crisis),
                "blocked": False,
                "is_crisis": is_crisis,
                "error": str(e),
            }

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_history_summary(self) -> Dict[str, Any]:
        """Return summary stats about current conversation history."""
        return {
            "total_turns": len(self.conversation_history) // 2,
            "max_turns": self.max_history_turns,
            "messages": len(self.conversation_history),
        }

    def test_connection(self) -> bool:
        """Test if the local Ollama instance is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Ollama connection test failed: {str(e)}")
            return False

    # ── Private: history ───────────────────────────────────────────────────────

    def _add_to_history(self, user_query: str, response_text: str) -> None:
        """Add a user/model turn to conversation history, trimming if needed."""
        self.conversation_history.append({"role": "user", "parts": [user_query]})
        self.conversation_history.append({"role": "model", "parts": [response_text]})

        max_messages = self.max_history_turns * 2
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    # ── Private: prompt injection ──────────────────────────────────────────────

    @staticmethod
    def _inject_crisis_instruction(prompt: str) -> str:
        """Prepend crisis protocol instructions to the prompt."""
        instruction = """
=== CRISIS PROTOCOL — SUICIDAL IDEATION DETECTED ===
User has expressed suicidal thoughts or self-harm ideation.

Your response MUST:
1. Open with immediate, warm acknowledgment of their pain
2. Provide these crisis resources early in your response:
   • 988 Suicide & Crisis Lifeline — call or text 988 (free, 24/7)
   • Crisis Text Line — text HOME to 741741
3. Keep the tone calm, human, and not clinical
4. Answer their question while maintaining safety focus
5. End with a gentle invitation to keep talking

DO NOT include these resources in normal (non-crisis) conversations.

=====================================================

"""
        return instruction + prompt

    # ── Private: fallback ──────────────────────────────────────────────────────

    @staticmethod
    def _get_fallback_response(is_crisis: bool = False) -> str:
        """Crisis-aware fallback for when generation fails."""
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
