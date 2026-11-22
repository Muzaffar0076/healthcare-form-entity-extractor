"""
User ORM model definition.

Complies with Section 3 of User Registration & Login Module specifications:
_id, fullName, email, password, phoneNumber, role, isVerified, createdAt, updatedAt.
"""

from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship
from backend.app.database import Base


def generate_uuid() -> str:
    """Generate a RFC 4122 compliant UUID v4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class UserModel(Base):
    """
    User account table representing registered healthcare app users.
    """

    __tablename__ = "users"

    _id = Column(
        String(36),
        primary_key=True,
        default=generate_uuid,
        index=True,
        doc="Unique user identifier",
    )
    fullName = Column(
        String(100),
        nullable=False,
        doc="User's full name",
    )
    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique user email address",
    )
    password = Column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password",
    )
    phoneNumber = Column(
        String(25),
        nullable=True,
        default=None,
        doc="Optional phone number",
    )
    role = Column(
        String(20),
        nullable=False,
        default="user",
        doc="User role (e.g. user, care_navigator, admin)",
    )
    isVerified = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Email verification status",
    )
    createdAt = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        doc="Account creation timestamp",
    )
    updatedAt = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        doc="Last account update timestamp",
    )

    # Relationships
    extractions = relationship(
        "ExtractionHistoryModel",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize model attributes to a dictionary, omitting the hashed password.
        """
        return {
            "_id": self._id,
            "fullName": self.fullName,
            "email": self.email,
            "phoneNumber": self.phoneNumber,
            "role": self.role,
            "isVerified": self.isVerified,
            "createdAt": self.createdAt.isoformat() if self.createdAt else None,
            "updatedAt": self.updatedAt.isoformat() if self.updatedAt else None,
        }

