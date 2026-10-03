"""Database tables.

One row per prediction. This log becomes the training data for the next model
version, and powers any analytics on model behaviour.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True)
    priority: Mapped[str] = mapped_column(String(5))
    confidence: Mapped[float] = mapped_column(Float)
    action: Mapped[str] = mapped_column(String(20), index=True)

    # Filled in by a human reviewer later; NULL until then.
    corrected_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<Prediction {self.id} {self.category} {self.confidence:.2f}>"