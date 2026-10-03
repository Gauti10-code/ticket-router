"""Model loading and prediction logic.

Separate from main.py so the routing layer stays thin and this can be tested
without starting a web server.
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib

from .config import settings

LOGGER = logging.getLogger(__name__)

# category -> priority, mirroring the support SLA rules
PRIORITY_MAP = {
    "PJP_MAP": "P1",
    "GRN_STUCK": "P1",
    "USER_CREATION": "P2",
    "LOGIN_ISSUE": "P2",
    "OUTLET_NOT_VISIBLE": "P2",
    "BEAT_CHANGE": "P3",
    "SCHEME_MAIL": "P4",
    "INVENTORY_ADD": "P5",
}


class Predictor:
    """Wraps the fitted pipeline. Loaded once at startup, reused per request."""

    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)
        self.pipeline = None

    def load(self) -> bool:
        """Load the model. Returns False instead of raising, so the app can
        still start and report its state through /ready."""
        if not self.model_path.exists():
            LOGGER.warning("Model file not found at %s", self.model_path)
            return False
        self.pipeline = joblib.load(self.model_path)
        LOGGER.info("Model loaded: %d classes", len(self.pipeline.classes_))
        return True

    @property
    def is_ready(self) -> bool:
        return self.pipeline is not None

    def predict(self, text: str) -> dict:
        """Classify one ticket and decide how to route it."""
        if not self.is_ready:
            raise RuntimeError("Model is not loaded")

        probabilities = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_

        ranked = sorted(zip(classes, probabilities), key=lambda x: x[1], reverse=True)
        top_category, top_confidence = ranked[0]

        return {
            "category": top_category,
            "priority": PRIORITY_MAP.get(top_category, "P3"),
            "confidence": round(float(top_confidence), 4),
            "action": (
                "auto_route"
                if top_confidence >= settings.confidence_threshold
                else "human_review"
            ),
            "alternatives": [
                {"category": c, "confidence": round(float(p), 4)}
                for c, p in ranked[1:3]
            ],
        }


predictor = Predictor(settings.model_path)