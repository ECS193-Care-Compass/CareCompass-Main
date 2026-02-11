"""
LLM handler for Google Gemini API
Using new google-genai library (google.genai)
With conversation history for multi-turn memory
"""
from google import genai
from google.genai import types
from typing import Optional, Dict, Any, List
from config.settings import GOOGLE_API_KEY, MODEL_NAME, TEMPERATURE, MAX_OUTPUT_TOKENS
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Max number of conversation turns to keep in memory
MAX_HISTORY_TURNS = 10


class LLMHandler:
    """Handle interactions with Google Gemini API with conversation memory"""
    
    def __init__(self, 
                 api_key: str = GOOGLE_API_KEY,
                 model_name: str = MODEL_NAME,
                 temperature: float = TEMPERATURE,
                 max_tokens: int = MAX_OUTPUT_TOKENS,
                 max_history_turns: int = MAX_HISTORY_TURNS):
        """
        Initialize LLM handler
        
        Args:
            api_key: Google API key
            model_name: Name of the Gemini model
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum output tokens
            max_history_turns: Max conversation turns to remember
        """
        if not api_key:
            raise ValueError("GOOGLE_API_KEY must be set in environment variables")
        
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_history_turns = max_history_turns
        
        # Conversation history: list of {"role": "user"/"model", "text": "..."}
        self.conversation_history: List[Dict[str, str]] = []
        
        # Initialize client with API key
        self.client = genai.Client(api_key=self.api_key)
        
        # Setup generation config with safety settings
        self.generation_config = types.GenerateContentConfig(
            temperature=self.temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=self.max_tokens,
            safety_settings=[
                types.SafetySetting(
                    category='HARM_CATEGORY_HARASSMENT',
                    threshold='BLOCK_ONLY_HIGH'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_HATE_SPEECH',
                    threshold='BLOCK_MEDIUM_AND_ABOVE'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
                    threshold='BLOCK_ONLY_HIGH'
                ),
                types.SafetySetting(
                    category='HARM_CATEGORY_DANGEROUS_CONTENT',
                    threshold='BLOCK_MEDIUM_AND_ABOVE'
                ),
            ]
        )
        
        logger.info(f"Initialized LLMHandler with model: {model_name}, max_history: {max_history_turns}")
    
    def _build_contents_with_history(self, prompt: str) -> List[types.Content]:
        """
        Build contents list with conversation history for multi-turn context
        
        Args:
            prompt: Current prompt (system instructions + RAG context + user query)
        
        Returns:
            List of Content objects for Gemini API
        """
        contents = []
        
        # Add previous conversation turns
        for turn in self.conversation_history:
            contents.append(
                types.Content(
                    role=turn["role"],
                    parts=[types.Part.from_text(text=turn["text"])]
                )
            )
        
        # Add current user prompt
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        )
        
        return contents
    
    def _add_to_history(self, user_message: str, model_response: str) -> None:
        """
        Add a conversation turn to history
        
        Args:
            user_message: The user's original query (not the full RAG prompt)
            model_response: The model's response text
        """
        self.conversation_history.append({"role": "user", "text": user_message})
        self.conversation_history.append({"role": "model", "text": model_response})
        
        # Trim history if it exceeds max turns (each turn = 2 entries: user + model)
        max_entries = self.max_history_turns * 2
        if len(self.conversation_history) > max_entries:
            self.conversation_history = self.conversation_history[-max_entries:]
            logger.info(f"Trimmed conversation history to {self.max_history_turns} turns")
    
    def generate_response(self, prompt: str, user_query: str = None) -> Dict[str, Any]:
        """
        Generate response from the LLM with conversation history
        
        Args:
            prompt: Complete prompt including system instructions and context
            user_query: Original user query (stored in history for cleaner context)
        
        Returns:
            Dictionary with response text and metadata
        """
        logger.info(f"Generating response for prompt of length: {len(prompt)}")
        
        try:
            # Build contents with conversation history
            contents = self._build_contents_with_history(prompt)
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=self.generation_config
            )
            
            # Extract text from response
            response_text = response.text if hasattr(response, 'text') else ""
            
            # Check if response was blocked
            if not response_text:
                logger.warning("Response was empty or blocked by safety filters")
                return {
                    "text": self._get_fallback_response(),
                    "blocked": True
                }
            
            # Store in conversation history (use original query if provided, not full RAG prompt)
            history_message = user_query if user_query else prompt[:500]
            self._add_to_history(history_message, response_text)
            
            logger.info(f"Successfully generated response of length: {len(response_text)}")
            logger.info(f"Conversation history: {len(self.conversation_history) // 2} turns")
            
            return {
                "text": response_text,
                "blocked": False
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "text": self._get_fallback_response(),
                "blocked": False,
                "error": str(e)
            }
    
    def clear_history(self) -> None:
        """Clear conversation history (e.g., for new session)"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_history_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation history"""
        return {
            "total_turns": len(self.conversation_history) // 2,
            "max_turns": self.max_history_turns,
            "messages": len(self.conversation_history)
        }
    
    def _get_fallback_response(self) -> str:
        """Get fallback response when generation fails"""
        return """I apologize, but I'm having trouble responding right now.

For immediate support, please reach out to:

- **National Sexual Assault Hotline**: 1-800-656-HOPE (4673)
- **Crisis Text Line**: Text "HELLO" to 741741
- **988 Suicide & Crisis Lifeline**: Call or text 988

I'm here to help connect you with resources. Could you try rephrasing your question?"""
    
    def test_connection(self) -> bool:
        """Test if the API connection works"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Hello, this is a test.",
                config=types.GenerateContentConfig(max_output_tokens=10)
            )
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False