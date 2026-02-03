"""
LLM handler for Google Gemini API
Using new google-genai library (google.genai)
"""
from google import genai
from google.genai import types
from typing import Optional, Dict, Any
from config.settings import GOOGLE_API_KEY, MODEL_NAME, TEMPERATURE, MAX_OUTPUT_TOKENS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMHandler:
    """Handle interactions with Google Gemini API"""
    
    def __init__(self, 
                 api_key: str = GOOGLE_API_KEY,
                 model_name: str = MODEL_NAME,
                 temperature: float = TEMPERATURE,
                 max_tokens: int = MAX_OUTPUT_TOKENS):
        """
        Initialize LLM handler
        
        Args:
            api_key: Google API key
            model_name: Name of the Gemini model
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum output tokens
        """
        if not api_key:
            raise ValueError("GOOGLE_API_KEY must be set in environment variables")
        
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
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
        
        logger.info(f"Initialized LLMHandler with model: {model_name}")
    
    def generate_response(self, prompt: str) -> Dict[str, Any]:
        """
        Generate response from the LLM
        
        Args:
            prompt: Complete prompt including system instructions and context
        
        Returns:
            Dictionary with response text and metadata
        """
        logger.info(f"Generating response for prompt of length: {len(prompt)}")
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
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
            
            logger.info(f"Successfully generated response of length: {len(response_text)}")
            
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