"""
ORM Model for revoked JWT tokens (token blacklist).

Enforces server-side session invalidation upon user logout.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String
from backend.app.database import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class RevokedTokenModel(Base):
    """
    Table storing revoked JWT identifiers (jti) to invalidate active sessions.
    Records are automatically cleaned up after their expiration date has passed.
    """

    __tablename__ = "revoked_tokens"

    jti = Column(
        String(36),
        primary_key=True,
        index=True,
        doc="Unique JWT identifier (UUID v4)",
    )
    userId = Column(
        String(36),
        nullable=False,
        index=True,
        doc="Identifier of user who owned the token",
    )
    revokedAt = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        doc="Timestamp when the token was revoked",
    )
    expiresAt = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Original expiration timestamp of the token",
    )

