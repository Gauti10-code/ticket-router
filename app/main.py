"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .predictor import predictor
from .schemas import PredictRequest, PredictResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup, and again on shutdown after the yield.

    The model is loaded here, not per request: joblib.load() takes ~100ms, so
    doing it on every call would make the API far slower than it needs to be.
    """
    loaded = predictor.load()
    LOGGER.info("startup complete (model_loaded=%s)", loaded)
    yield
    LOGGER.info("shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Classifies support tickets by category and priority, and routes them. "
        "Low-confidence predictions are flagged for human review."
    ),
    lifespan=lifespan,
)


# --- response models for the system endpoints -----------------------------


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    ready: bool
    model_loaded: bool
    detail: str


# --- system routes ---------------------------------------------------------


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} — see /docs for the API"}


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness: is the process up? Must stay cheap — no model, no database."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )


@app.get("/ready", response_model=ReadinessResponse, tags=["system"])
def ready() -> ReadinessResponse:
    """Readiness: can this instance actually serve predictions right now?

    Separate from /health because a process can be alive but unable to serve —
    model still loading, dependency down. Orchestrators treat them differently:
    a failed liveness check restarts the container, a failed readiness check
    just stops traffic being sent here.
    """
    return ReadinessResponse(
        ready=predictor.is_ready,
        model_loaded=predictor.is_ready,
        detail="model loaded" if predictor.is_ready else "model not loaded",
    )


# --- prediction route ------------------------------------------------------


@app.post("/predict", response_model=PredictResponse, tags=["prediction"])
def predict(request: PredictRequest) -> PredictResponse:
    """Classify a ticket and decide whether it can be routed automatically.

    Returns 503 (not 500) when the model is missing: the service is temporarily
    unable to serve, which is a different situation from an unexpected crash.
    """
    if not predictor.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Run scripts/train.py first.",
        )

    result = predictor.predict(request.text)

    LOGGER.info(
        "predicted %s (%.3f) -> %s | %s",
        result["category"],
        result["confidence"],
        result["action"],
        request.text[:60],
    )
    return PredictResponse(**result)