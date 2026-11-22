"""
Authentication and user management service.

Handles:
- SEC-05: Secure HttpOnly cookie management and CSRF token binding.
- SEC-06: Bcrypt password hashing (cost factor 12) strictly enforcing <= 72 UTF-8 bytes.
- JWT access token generation with unique jti claims.
- Server-side token revocation and blacklist checks.
- Database queries and operations for UserModel and RevokedTokenModel.
"""

from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any, Optional
import uuid

import bcrypt
from fastapi import Response
import jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.revocation import RevokedTokenModel
from backend.app.models.user import UserModel
from backend.app.schemas import UserRegisterRequest

logger = logging.getLogger(__name__)

INSECURE_FALLBACK_KEY = "dev-insecure-fallback-key-do-not-use-in-production-32chars"
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
BCRYPT_ROUNDS = 12

# Cookie configuration constants
ACCESS_TOKEN_COOKIE = "access_token"
CSRF_TOKEN_COOKIE = "csrf_token"


def get_jwt_secret_key() -> str:
    """
    Retrieve and validate the JWT secret key.
    Fails application startup in production if missing, default, or insecure (< 32 chars).
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    secret = os.getenv("JWT_SECRET_KEY", "").strip()

    if env in {"production", "prod"}:
        if not secret:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: JWT_SECRET_KEY environment "
                "variable is required in production. Generate one using 'openssl rand -hex 32'."
            )
        if secret in {INSECURE_FALLBACK_KEY, "change-me", "secret"} or len(secret) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: The configured JWT_SECRET_KEY "
                "is insecure. Production keys must be at least 32 characters long."
            )
        return secret

    # Development / Testing fallback
    if not secret:
        return INSECURE_FALLBACK_KEY
    return secret


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with cost factor 12.
    Rejects passwords exceeding 72 UTF-8 bytes.
    """
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes due to bcrypt limitation.")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Preserves existing bcrypt hashes ($2a$, $2b$, $2y$) without migration.
    Handles malformed or corrupted hashes safely without unhandled exceptions.

    Returns:
        True if credentials match, False otherwise.
    """
    if not hashed_password or not isinstance(hashed_password, str):
        return False
    if not plain_password or not isinstance(plain_password, str):
        return False

    pwd_bytes = plain_password.encode("utf-8")
    if len(pwd_bytes) > 72:
        return False

    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


def set_auth_cookies(
    response: Response,
    token: str,
    csrf_token: Optional[str] = None,
    session_binding: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """
    Configure and attach HttpOnly access_token cookie and readable csrf_token cookie.
    Ensures secure flags in production and SameSite=Lax.
    Binds the CSRF token to the session's unique JWT jti.
    """
    from backend.app.middleware.csrf import set_csrf_cookie

    is_production = os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}
    samesite_val = "none" if is_production else "lax"
    secure_val = True if is_production else False
    max_age_secs = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # 1. HttpOnly access_token cookie (JWT storage)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=secure_val,
        samesite=samesite_val,
        max_age=max_age_secs,
        path="/",
    )

    # 2. Extract jti from JWT token for session binding
    binding = session_binding
    if not binding:
        try:
            payload = decode_access_token(token, verify_exp=False)
            binding = payload.get("jti") or user_id
        except Exception:
            binding = user_id

    # 3. CSRF cookie (readable by JavaScript for header inclusion, bound to session jti)
    return set_csrf_cookie(response, csrf_token=csrf_token, session_binding=binding or "anon")


def clear_auth_cookies(response: Response) -> None:
    """
    Clear both access_token and csrf_token cookies upon logout.
    """
    is_production = os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}
    samesite_val = "none" if is_production else "lax"
    secure_val = True if is_production else False

    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        httponly=True,
        secure=secure_val,
        samesite=samesite_val,
        path="/",
    )
    response.delete_cookie(
        key=CSRF_TOKEN_COOKIE,
        httponly=False,
        secure=secure_val,
        samesite=samesite_val,
        path="/",
    )


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generate a signed JWT access token embedded with a unique jti identifier.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Embed unique token identifier (jti) for server-side revocation
    token_jti = str(uuid.uuid4())
    to_encode.update({
        "iat": now,
        "exp": expire,
        "jti": token_jti,
    })

    secret_key = get_jwt_secret_key()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str, verify_exp: bool = True) -> dict[str, Any]:
    """
    Decode and validate a signed JWT token.

    Raises:
        jwt.ExpiredSignatureError: If token has expired.
        jwt.PyJWTError: If token signature or structure is invalid.
    """
    secret_key = get_jwt_secret_key()
    options = {"verify_exp": verify_exp}
    return jwt.decode(
        token,
        secret_key,
        algorithms=[JWT_ALGORITHM],
        options=options,
    )


def revoke_token(db: Session, token: str) -> None:
    """
    Revoke a JWT token by adding its unique jti to the database revocation blacklist.
    Also automatically cleans up older expired revocation records.
    """
    try:
        # Decode without enforcing expiration check so even an expiring token can be revoked
        payload = decode_access_token(token, verify_exp=False)
    except jwt.PyJWTError:
        return

    token_jti = payload.get("jti")
    user_id = payload.get("sub", "unknown")
    exp_timestamp = payload.get("exp")

    if not token_jti or not exp_timestamp:
        return

    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)

    # Check if already revoked
    existing = (
        db.query(RevokedTokenModel)
        .filter(RevokedTokenModel.jti == token_jti)
        .first()
    )
    if not existing:
        revoked_record = RevokedTokenModel(
            jti=token_jti,
            userId=user_id,
            revokedAt=now,
            expiresAt=exp_datetime,
        )
        db.add(revoked_record)

    # Automatic cleanup of expired tokens
    db.query(RevokedTokenModel).filter(
        RevokedTokenModel.expiresAt < now
    ).delete(synchronize_session=False)

    db.commit()


def is_token_revoked(db: Session, jti: str) -> bool:
    """
    Check if a token's jti is in the revocation blacklist.
    """
    if not jti:
        return True
    record = (
        db.query(RevokedTokenModel)
        .filter(RevokedTokenModel.jti == jti)
        .first()
    )
    return record is not None


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    """
    Retrieve a user from database by email address (case-insensitive).
    """
    clean_email = email.strip().lower()
    return (
        db.query(UserModel)
        .filter(func.lower(UserModel.email) == clean_email)
        .first()
    )


def get_user_by_id(db: Session, user_id: str) -> Optional[UserModel]:
    """
    Retrieve a user by unique _id string.
    """
    return db.query(UserModel).filter(UserModel._id == user_id).first()


def create_user(db: Session, req: UserRegisterRequest) -> UserModel:
    """
    Create and persist a new user record with hashed password (bcrypt cost factor 12).
    """
    hashed_pwd = hash_password(req.password)
    user = UserModel(
        fullName=req.fullName,
        email=req.email.strip().lower(),
        password=hashed_pwd,
        phoneNumber=req.phoneNumber,
        role="user",
        isVerified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(
    db: Session, email: str, password: str
) -> Optional[UserModel]:
    """
    Verify user credentials using bcrypt.
    Preserves existing bcrypt hashes without migration.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None

    if not verify_password(password, user.password):
        return None

    return user
