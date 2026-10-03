"""Request and response models for the API.

These classes are the API contract: FastAPI validates incoming JSON against
them, builds the /docs schema from them, and rejects anything that doesn't fit
before your code runs.
"""

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
    action: str                      # "auto_route" or "human_review"
    alternatives: list[Alternative]