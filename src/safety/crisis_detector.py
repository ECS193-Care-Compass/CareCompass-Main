"""
Crisis detection using gooohjy/suicidal-electra + keyword matching

Two-layer detection:
  Layer 1 — Keyword check (fast, catches direct explicit statements)
  Layer 2 — ML model check (catches indirect/implicit expressions)

A message is flagged as a crisis if EITHER layer triggers.

Model:   gooohjy/suicidal-electra
Base:    google/electra-base-discriminator
Task:    Binary text classification → LABEL_1 (suicidal) / LABEL_0 (non-suicidal)
Source:  https://huggingface.co/gooohjy/suicidal-electra
         https://github.com/gohjiayi/suicidal-text-detection
"""

import re
import torch
from transformers import pipeline
from typing import Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)

MODEL_ID = "gooohjy/suicidal-electra"
CRISIS_LABEL = "LABEL_1"

# ── Keywords ──────────────────────────────────────────────────────────────────
# Explicit direct statements the model may miss.
# Kept focused on clear self-harm/suicidal language to minimise false positives.
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


def _keyword_match(text: str) -> bool:
    """
    Check if the text contains any crisis keywords.
    Case-insensitive, matches whole phrases.
    """
    text_lower = text.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword in text_lower:
            logger.info(f"Crisis keyword matched: '{keyword}'")
            return True
    return False


class CrisisDetector:
    """
    Two-layer crisis detector for suicidal ideation and self-harm.

    Layer 1 — keyword check: fast, no model needed, catches direct statements
    Layer 2 — ML model:      catches indirect/implicit expressions of distress

    is_crisis = keyword_match OR model_label == LABEL_1

    Lazy-loads the model on first call to keep app startup fast.
    """

    def __init__(self, model_id: str = MODEL_ID):
        self.model_id = model_id
        self._classifier = None

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._classifier is not None:
            return

        logger.info(f"Loading crisis detection model: {self.model_id}")
        device = 0 if torch.cuda.is_available() else -1

        self._classifier = pipeline(
            task="text-classification",
            model=self.model_id,
            tokenizer=self.model_id,
            device=device,
            truncation=True,
            max_length=512,
        )

        logger.info(
            f"Crisis detection model loaded on "
            f"{'GPU' if device == 0 else 'CPU'}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Run two-layer crisis detection on a user message.

        Pass only the raw user message — NOT the full RAG prompt.
        Context documents add noise to the classifier.

        Args:
            text: Raw user message string.

        Returns:
            {
                "is_crisis":        bool — True if either layer triggered
                "keyword_triggered": bool — True if a keyword matched
                "model_triggered":   bool — True if model returned LABEL_1
                "model_label":       str  — raw model label (LABEL_0 / LABEL_1)
            }
        """
        if not text or not text.strip():
            return self._result(
                keyword_triggered=False,
                model_triggered=False,
                model_label="LABEL_0"
            )

        # Layer 1 — keyword check (no model load needed if keyword matches)
        keyword_triggered = _keyword_match(text)

        # Layer 2 — model check
        model_triggered = False
        model_label = "LABEL_0"

        try:
            self._load()
            result = self._classifier(text)[0]
            model_label = result["label"]
            model_triggered = model_label == CRISIS_LABEL
            logger.info(f"Crisis model — label: {model_label}")

        except Exception as e:
            logger.error(f"Crisis model failed: {e}")
            # Fail safe — if model errors and no keyword match, still flag
            # so the user gets careful handling
            model_triggered = True

        return self._result(keyword_triggered, model_triggered, model_label)

    def warmup(self) -> None:
        """
        Force model load at app startup to avoid latency on the first message.
        Call from your FastAPI lifespan/startup event.
        """
        self._load()
        logger.info("CrisisDetector warmup complete.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _result(
        keyword_triggered: bool,
        model_triggered: bool,
        model_label: str,
    ) -> Dict[str, Any]:
        return {
            "is_crisis":         keyword_triggered or model_triggered,
            "keyword_triggered": keyword_triggered,
            "model_triggered":   model_triggered,
            "model_label":       model_label,
        }