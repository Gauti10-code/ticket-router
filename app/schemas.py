"""Request and response models for the API.

These classes are the API contract: FastAPI validates incoming JSON against
them, builds the /docs schema from them, and rejects anything that doesn't fit.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Raw ticket text as the user wrote it",
        examples=["grn stuck for invoice INV4421 since morning"],
    )


class Alternative(BaseModel):
    category: str
    confidence: float


class PredictResponse(BaseModel):
    category: str
    priority: str
    confidence: float
    action: str                       # "auto_route" or "human_review"
    alternatives: list[Alternative]


class PredictionLogItem(BaseModel):
    """One row from the predictions table."""

    id: int
    created_at: datetime
    text: str
    category: str
    priority: str
    confidence: float
    action: str
    corrected_category: str | None

    # Lets Pydantic read a SQLAlchemy object directly instead of a dict.
    model_config = {"from_attributes": True}


class CorrectionRequest(BaseModel):
    """A human reviewer saying what the category should have been."""

    corrected_category: str = Field(..., min_length=2, max_length=50)