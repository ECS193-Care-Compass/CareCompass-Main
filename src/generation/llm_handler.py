"""
LLM handler for Google Gemini API
Using google-generativeai library

Crisis detection is handled upstream in CAREBot.process_query().
LLMHandler receives the result via the is_crisis flag and injects
the appropriate prompt instruction if needed.
"""
import google.generativeai as genai
from typing import Dict, Any, List
from config.settings import GOOGLE_API_KEY, MODEL_NAME, TEMPERATURE, MAX_OUTPUT_TOKENS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMHandler:
    """Handle interactions with Google Gemini API"""

    def __init__(
        self,
        api_key: str = GOOGLE_API_KEY,
        model_name: str = MODEL_NAME,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_OUTPUT_TOKENS,
    ):
        """
        Initialize LLM handler.

        Args:
            api_key:     Google API key
            model_name:  Gemini model name
            temperature: Generation temperature (0.0-1.0)
            max_tokens:  Maximum output tokens
        """
        if not api_key:
            raise ValueError("GOOGLE_API_KEY must be set in environment variables")

        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Configure Gemini API
        genai.configure(api_key=self.api_key)

        # Conversation history
        self.conversation_history: List[Dict] = []
        self.max_history_turns = 10

        # Create the model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=self.max_tokens,
            ),
        )

        logger.info(f"Initialized LLMHandler with model: {model_name}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_response(
        self,
        prompt: str,
        user_query: str = "",
        is_crisis: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a Gemini response.

        Crisis detection is done upstream in CAREBot — this method just
        receives the result and injects crisis instructions if needed.

        Args:
            prompt:     Full RAG/scenario prompt to send to Gemini.
            user_query: Raw user message, stored in conversation history.
            is_crisis:  Whether crisis was detected upstream. If True,
                        crisis protocol instructions are prepended to prompt.

        Returns:
            {
                "text":      str  - response text
                "blocked":   bool - True if Gemini safety filters triggered
                "is_crisis": bool - echoed back from input
                "error":     str  - only present if an exception occurred
            }
        """
        logger.info(f"Generating response — prompt length: {len(prompt)}, is_crisis: {is_crisis}")

        # Inject crisis instructions into prompt if needed
        if is_crisis:
            prompt = self._inject_crisis_instruction(prompt)

        try:
            response = self.model.generate_content(prompt)

            response_text = response.text if hasattr(response, 'text') else ""

            if not response_text:
                logger.warning("Response empty or blocked by Gemini safety filters")
                return {
                    "text":      self._get_fallback_response(is_crisis),
                    "blocked":   True,
                    "is_crisis": is_crisis,
                }

            # Store turn in conversation history
            if user_query:
                self._add_to_history(user_query, response_text)

            logger.info(f"Response generated — length: {len(response_text)}")

            return {
                "text":      response_text,
                "blocked":   False,
                "is_crisis": is_crisis,
            }

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "text":      self._get_fallback_response(is_crisis),
                "blocked":   False,
                "is_crisis": is_crisis,
                "error":     str(e),
            }

    def clear_history(self) -> None:
        """Clear conversation history for a fresh start."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_history_summary(self) -> Dict[str, Any]:
        """Return summary stats about current conversation history."""
        return {
            "total_turns": len(self.conversation_history) // 2,
            "max_turns":   self.max_history_turns,
            "messages":    len(self.conversation_history),
        }

    def test_connection(self) -> bool:
        """Test if the Gemini API connection is working."""
        try:
            self.model.generate_content("Hello, this is a test.")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    # ── Private: history ───────────────────────────────────────────────────────

    def _add_to_history(self, user_query: str, response_text: str) -> None:
        """Add a user/model turn to conversation history, trimming if needed."""
        self.conversation_history.append({"role": "user",  "parts": [user_query]})
        self.conversation_history.append({"role": "model", "parts": [response_text]})

        # Keep only the last max_history_turns turns
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