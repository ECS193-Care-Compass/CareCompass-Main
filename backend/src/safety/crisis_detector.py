"""
Crisis detection using keyword matching

Keyword-only detection layer for explicit crisis language.
Implicit/indirect crisis detection is handled downstream by the LLM
(Gemini assesses every message for crisis signals as part of its
structured JSON response).

A message is flagged as a crisis if keywords match OR the LLM detects it.
"""

import re
from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Keywords
# Explicit direct statements that catch clear self-harm/suicidal language.
CRISIS_KEYWORDS = [
    # Direct suicidal statements
    "kill myself",
    "end my life",
    "take my life",
    "commit suicide",
    "want to die",
    "don't want to live",
    "don't want to be alive",
    "ready to die",
    "planning to die",
    "going to kill myself",
    # Self-harm
    "cutting myself",
    "cut myself",
    "hurting myself",
    "hurt myself",
    "harming myself",
    "harm myself",
    "self harm",
    "self-harm",
    # Means/plans
    "have a plan",
    "took pills",
    "taking pills to",
    "overdose",
    "hanging myself",
    "shoot myself",
    "jump off",
]

# Pre-compile a single regex with word boundaries for all keywords.
# Produces: \b(?:kill myself|end my life|...)\b
#   \b          = word boundary (prevents partial matches like "planetary" matching "plan")
#   (?:...|...) = non-capturing OR group — matches any keyword
#   re.escape   = escapes special regex chars (e.g. "-" in "self-harm")
#   IGNORECASE  = case-insensitive matching
_CRISIS_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(kw) for kw in CRISIS_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def _keyword_match(text: str) -> bool:
    """
    Check if the text contains any crisis keywords.
    Case-insensitive, matches whole phrases with word boundaries.
    """
    match = _CRISIS_PATTERN.search(text)
    if match:
        logger.info(f"Crisis keyword matched: '{match.group()}'")
        return True
    return False


class CrisisDetector:
    """
    Keyword-based crisis detector for suicidal ideation and self-harm.

    Checks for explicit crisis keywords in user messages.
    Implicit crisis detection is delegated to the LLM via structured
    JSON output (is_crisis field in every response).
    """

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Run keyword-based crisis detection on a user message.

        Args:
            text: Raw user message string.

        Returns:
            {
                "is_crisis":        bool — True if keywords matched
                "keyword_triggered": bool — True if a keyword matched
                "model_triggered":   bool — always False (LLM handles this)
            }
        """
        if not text or not text.strip():
            return {
                "is_crisis": False,
                "keyword_triggered": False,
                "model_triggered": False,
            }

        keyword_triggered = _keyword_match(text)

        return {
            "is_crisis": keyword_triggered,
            "keyword_triggered": keyword_triggered,
            "model_triggered": False,
        }
