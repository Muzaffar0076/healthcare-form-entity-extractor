"""
ORM Model for User Extraction History.

Allows authenticated users to persist and view their previous healthcare form
extraction records, storing original form text and extracted entities with
labels and character positions.
"""

from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.app.database import Base


def generate_uuid() -> str:
    """Generate an RFC 4122 compliant UUID v4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class ExtractionHistoryModel(Base):
    """
    Table storing healthcare form extraction history for authenticated users.
    Each record belongs to a specific user.
    """

    __tablename__ = "extraction_history"

    id = Column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        index=True,
        doc="Unique extraction record identifier (UUID v4)",
    )
    user_id = Column(
        String(36),
        ForeignKey("users._id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key referencing users._id",
    )
    form_text = Column(
        Text,
        nullable=False,
        doc="The original submitted healthcare form text",
    )
    extracted_entities = Column(
        JSON,
        nullable=False,
        doc="JSON object containing extracted entities list with labels and offsets",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
        doc="UTC timestamp when the extraction was saved",
    )

    # Relationships
    user = relationship("UserModel", back_populates="extractions")

