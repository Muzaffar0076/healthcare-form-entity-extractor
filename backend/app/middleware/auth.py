"""
Authentication middleware and FastAPI security dependencies.

Implements SEC-05:
- Dual-mode authentication supporting both HttpOnly cookies and Bearer tokens.
- Rejection of conflicting cookie and Authorization header credentials (HTTP 400).
- Server-side revocation blacklist check.
- Extraction and validation of active UserModel.
"""

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import UserModel
from backend.app.services.auth_service import (
    ACCESS_TOKEN_COOKIE,
    decode_access_token,
    get_user_by_id,
    is_token_revoked,
)

# HTTP Bearer scheme with auto_error=False to allow cookie-only requests
security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> UserModel:
    """
    Extracts, validates, and decodes the JWT access token from either:
    1. HttpOnly access_token cookie (primary for browsers), or
    2. Authorization: Bearer <token> header (for API/CLI clients).

    Rejects conflicting credentials if both cookie and header are provided with differing tokens.
    Rejects revoked, expired, or malformed tokens.
    """
    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    header_token = credentials.credentials if (credentials and credentials.credentials) else None

    # SEC-05: Reject conflicting cookie and Bearer credentials
    if cookie_token and header_token and cookie_token != header_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflicting authentication credentials provided (cookie and Authorization header mismatch).",
        )

    # Select available token
    token = cookie_token or header_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        token_jti: Optional[str] = payload.get("jti")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing subject identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check server-side revocation blacklist
        if token_jti and is_token_revoked(db, token_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this session no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """
    Ensures the authenticated user account is verified and active.
    """
    if not current_user.isVerified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is unverified or disabled.",
        )
    return current_user
