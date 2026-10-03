"""FastAPI application entrypoint.

Run locally with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import settings
from .db import get_session, init_db
from .models_db import Prediction
from .predictor import predictor
from .schemas import (
    CorrectionRequest,
    PredictionLogItem,
    PredictRequest,
    PredictResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup before the yield, shutdown after."""
    init_db()
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


# --- system response models -----------------------------------------------


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
    """Readiness: can this instance serve predictions right now?"""
    return ReadinessResponse(
        ready=predictor.is_ready,
        model_loaded=predictor.is_ready,
        detail="model loaded" if predictor.is_ready else "model not loaded",
    )


# --- prediction routes -----------------------------------------------------


@app.post("/predict", response_model=PredictResponse, tags=["prediction"])
def predict(
    request: PredictRequest,
    session: Session = Depends(get_session),
) -> PredictResponse:
    """Classify a ticket, log it, and decide whether it can be auto-routed."""
    if not predictor.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Run scripts/train.py first.",
        )

    result = predictor.predict(request.text)

    row = Prediction(
        text=request.text,
        category=result["category"],
        priority=result["priority"],
        confidence=result["confidence"],
        action=result["action"],
    )
    session.add(row)
    session.commit()

    LOGGER.info(
        "predicted %s (%.3f) -> %s [id=%s] | %s",
        result["category"],
        result["confidence"],
        result["action"],
        row.id,
        request.text[:60],
    )
    return PredictResponse(**result)


@app.get("/predictions", response_model=list[PredictionLogItem], tags=["prediction"])
def list_predictions(
    limit: int = 20,
    action: str | None = None,
    session: Session = Depends(get_session),
) -> list[Prediction]:
    """Recent predictions, newest first. Filter by action to review the
    low-confidence ones: /predictions?action=human_review
    """
    query = session.query(Prediction).order_by(Prediction.created_at.desc())
    if action:
        query = query.filter(Prediction.action == action)
    return query.limit(limit).all()


@app.patch(
    "/predictions/{prediction_id}",
    response_model=PredictionLogItem,
    tags=["prediction"],
)
def correct_prediction(
    prediction_id: int,
    correction: CorrectionRequest,
    session: Session = Depends(get_session),
) -> Prediction:
    """A human reviewer records the right answer.

    Every row where corrected_category differs from category is a labelled
    model mistake — the raw material for retraining.
    """
    row = session.get(Prediction, prediction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Prediction not found")

    row.corrected_category = correction.corrected_category
    session.commit()
    session.refresh(row)

    LOGGER.info("correction on id=%s: %s -> %s",
                prediction_id, row.category, row.corrected_category)
    return row


@app.get("/stats", tags=["prediction"])
def stats(session: Session = Depends(get_session)) -> dict:
    """Operational summary: how is the model behaving in production?"""
    from sqlalchemy import func

    total = session.query(func.count(Prediction.id)).scalar() or 0
    auto = (
        session.query(func.count(Prediction.id))
        .filter(Prediction.action == "auto_route")
        .scalar()
        or 0
    )
    corrected = (
        session.query(func.count(Prediction.id))
        .filter(Prediction.corrected_category.isnot(None))
        .scalar()
        or 0
    )
    wrong = (
        session.query(func.count(Prediction.id))
        .filter(
            Prediction.corrected_category.isnot(None),
            Prediction.corrected_category != Prediction.category,
        )
        .scalar()
        or 0
    )
    avg_conf = session.query(func.avg(Prediction.confidence)).scalar()

    by_category = dict(
        session.query(Prediction.category, func.count(Prediction.id))
        .group_by(Prediction.category)
        .all()
    )

    return {
        "total_predictions": total,
        "auto_routed": auto,
        "human_review": total - auto,
        "auto_route_rate": round(auto / total, 3) if total else None,
        "reviewed_by_human": corrected,
        "model_was_wrong": wrong,
        "avg_confidence": round(float(avg_conf), 4) if avg_conf else None,
        "by_category": by_category,
    }