"""
Sample tests for CARE Bot
"""
import pytest
from src.safety.crisis_detector import CrisisDetector
from src.generation.prompt_templates import PromptTemplates


def test_crisis_detector_initialization():
    """Test crisis detector initializes correctly"""
    detector = CrisisDetector()
    assert detector is not None
    assert len(detector.crisis_keywords) > 0


def test_crisis_detection_positive():
    """Test that crisis indicators are detected"""
    detector = CrisisDetector()
    
    result = detector.detect_crisis("I want to hurt myself")
    
    assert result["is_crisis"] == True
    assert len(result["detected_keywords"]) > 0
    assert result["severity"] in ["moderate", "high", "critical"]


def test_crisis_detection_negative():
    """Test that normal queries don't trigger crisis detection"""
    detector = CrisisDetector()
    
    result = detector.detect_crisis("I need help finding a counselor")
    
    assert result["is_crisis"] == False
    assert len(result["detected_keywords"]) == 0
    assert result["severity"] == "none"


def test_prompt_template_system_prompt():
    """Test that system prompt contains trauma-informed principles"""
    prompt = PromptTemplates.get_system_prompt()
    
    assert "trauma-informed" in prompt.lower()
    assert "safety" in prompt.lower()
    assert "choice" in prompt.lower()
    assert "empowerment" in prompt.lower()


def test_rag_prompt_construction():
    """Test RAG prompt construction"""
    query = "What follow-up do I need?"
    docs = [
        {
            "text": "Sample context text",
            "metadata": {"source": "test.pdf", "page": 1}
        }
    ]
    
    prompt = PromptTemplates.get_rag_prompt(query, docs)
    
    assert query in prompt
    assert "Sample context text" in prompt
    assert "test.pdf" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
