"""
Crisis detection and safety monitoring
"""
from typing import Dict, Any, List
from config.trauma_informed_principles import CRISIS_INDICATORS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrisisDetector:
    """Detect crisis situations and provide appropriate responses"""
    
    def __init__(self, crisis_keywords: List[str] = None):
        """
        Initialize crisis detector
        
        Args:
            crisis_keywords: List of crisis indicator keywords
        """
        self.crisis_keywords = crisis_keywords or CRISIS_INDICATORS
        logger.info(f"Initialized CrisisDetector with {len(self.crisis_keywords)} keywords")
    
    def detect_crisis(self, text: str) -> Dict[str, Any]:
        """
        Detect crisis indicators in text
        
        Args:
            text: User input text
        
        Returns:
            Dictionary with crisis detection results
        """
        text_lower = text.lower()
        
        # Check for crisis keywords
        detected_keywords = [
            keyword for keyword in self.crisis_keywords
            if keyword in text_lower
        ]
        
        is_crisis = len(detected_keywords) > 0
        
        if is_crisis:
            logger.warning(f"Crisis indicators detected: {detected_keywords}")
        
        return {
            "is_crisis": is_crisis,
            "detected_keywords": detected_keywords,
            "response_needed": is_crisis
        }
    
    def get_crisis_response(self, severity: str = None) -> str:
        """
        Get crisis response message (single message for any severity)
        
        Args:
            severity: Crisis severity level (ignored - same message for all)
        
        Returns:
            Crisis response message
        """
        return """I'm concerned about what you've shared with me. Your safety is the most important thing right now.

        IMMEDIATE HELP AVAILABLE 24/7:

        • **Emergency Services**
        If you're in immediate danger: Call 911

        """
    
    def log_crisis_detection(self, 
                           user_input: str, 
                           detection_result: Dict[str, Any]) -> None:
        """
        Log crisis detection for monitoring (privacy-preserving)
        
        Args:
            user_input: User's message (logged without PII)
            detection_result: Detection results
        """
        # In production, this would log to secure monitoring system
        # For now, just log the fact that crisis was detected
        if detection_result["is_crisis"]:
            logger.warning(
                f"Crisis detected - Keywords: {len(detection_result['detected_keywords'])}"
            )


if __name__ == "__main__":
    # Test crisis detector
    detector = CrisisDetector()
    
    # Test cases
    test_inputs = [
        "I need help finding a counselor",
        "I'm feeling really anxious and having trouble sleeping",
        "I don't know if I can keep going, I want to hurt myself",
        "I'm thinking about suicide",
    ]
    
    print("Testing Crisis Detector:\n")
    
    for test_input in test_inputs:
        print(f"Input: '{test_input}'")
        result = detector.detect_crisis(test_input)
        print(f"  Crisis: {result['is_crisis']}")
        
        if result['is_crisis']:
            print(f"  Detected: {result['detected_keywords']}")
            print(f"\nResponse:\n{detector.get_crisis_response()}")
        
        print("\n" + "="*80 + "\n")