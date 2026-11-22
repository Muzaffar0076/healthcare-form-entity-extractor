"""
CSRF Protection Middleware and Cryptographic Synchronizer Token Service.

Implements SEC-05:
- HMAC-signed, time-bound CSRF tokens.
- Origin validation against configured ALLOWED_ORIGINS.
- Double-submit validation comparing X-CSRF-Token header with csrf_token cookie.
- Automatic exemption for Bearer-only API requests (immune to ambient browser CSRF).
- Automatic rejection of missing, invalid, expired, or tampered tokens with HTTP 403.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.app.services.auth_service import get_jwt_secret_key

CSRF_HEADER_NAME = "x-csrf-token"
CSRF_COOKIE_NAME = "csrf_token"
ACCESS_TOKEN_COOKIE = "access_token"
CSRF_MAX_AGE_SECONDS = 86400  # 24 hours

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]


def get_allowed_origins() -> list[str]:
    """
    Retrieve configured allowed origins.
    - Explicit ALLOWED_ORIGINS takes precedence.
    - In production, missing or empty ALLOWED_ORIGINS fails closed (returns []).
    - Localhost origins are fallback only in non-production (development/test).
    """
    is_production = os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}
    raw = os.getenv("ALLOWED_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    if is_production:
        # Fails closed in production: no default origins permitted unless explicitly configured
        return []
    return list(DEFAULT_ALLOWED_ORIGINS)


def generate_csrf_token(session_binding: str = "anon") -> str:
    """
    Generate an HMAC-SHA256 signed, time-bound CSRF token bound to a session identifier.
    Format: timestamp:nonce:binding:signature (strict 4 parts)
    """
    secret = get_jwt_secret_key().encode("utf-8")
    ts = int(time.time())
    nonce = secrets.token_hex(16)
    binding = session_binding.strip() if session_binding else "anon"
    payload = f"{ts}:{nonce}:{binding}"
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def validate_csrf_token(
    token: Optional[str],
    expected_binding: Optional[str] = None,
    max_age_seconds: int = CSRF_MAX_AGE_SECONDS,
) -> bool:
    """
    Validate that a CSRF token:
    1. Has strict 4-part format: timestamp:nonce:binding:signature.
    2. Has a valid timestamp (not expired, not future-dated beyond 5s clock skew).
    3. Has a valid HMAC-SHA256 signature matching the exact signed payload.
    4. Matches the expected session binding (e.g. JWT jti) using constant-time comparison.
    5. Rejects anonymous tokens for authenticated sessions.
    """
    if not token or not isinstance(token, str):
        return False

    parts = token.split(":")
    if len(parts) != 4:
        return False

    ts_str, nonce, token_binding, signature = parts

    try:
        ts = int(ts_str)
    except ValueError:
        return False

    now = int(time.time())
    # Reject expired tokens or tokens with timestamps more than 5s in the future
    if (now - ts) > max_age_seconds or ts > (now + 5):
        return False

    secret = get_jwt_secret_key().encode("utf-8")
    payload = f"{ts_str}:{nonce}:{token_binding}"
    expected_sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        return False

    # Enforce session binding:
    # If expected_binding is provided:
    # - If expected_binding is for an authenticated session (not "anon"), reject anonymous token
    # - Verify constant-time match between token_binding and expected_binding
    if expected_binding:
        if expected_binding != "anon" and token_binding == "anon":
            return False
        if not hmac.compare_digest(token_binding, expected_binding):
            return False

    return True


def set_csrf_cookie(
    response: Response,
    csrf_token: Optional[str] = None,
    session_binding: str = "anon",
) -> str:
    """
    Attach the CSRF token cookie to a response.
    Readable by JavaScript (HttpOnly=False) for inclusion in the X-CSRF-Token header.
    """
    token = csrf_token or generate_csrf_token(session_binding=session_binding)
    is_production = os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}
    samesite_val = "none" if is_production else "lax"
    secure_val = True if is_production else False

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Must be readable by client JS to set X-CSRF-Token header
        secure=secure_val,
        samesite=samesite_val,
        max_age=CSRF_MAX_AGE_SECONDS,
        path="/",
    )
    return token


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware verifying Origin and CSRF tokens on state-changing requests.
    """

    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()

        # 1. Safe methods bypass CSRF verification (do not inject cookies into arbitrary GET requests)
        if method in SAFE_METHODS:
            return await call_next(request)

        # 2. Origin validation on state-changing requests
        is_production = os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}
        origin = request.headers.get("origin")
        allowed = get_allowed_origins()
        norm_allowed = [a.rstrip("/") for a in allowed]

        # Fail closed in production: state-changing browser requests must provide an Origin header
        has_cookie_session = ACCESS_TOKEN_COOKIE in request.cookies
        has_csrf_cookie = CSRF_COOKIE_NAME in request.cookies

        if is_production and not origin and (has_cookie_session or has_csrf_cookie):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"code": "FORBIDDEN", "message": "CSRF verification failed: Origin header required in production."},
            )

        if origin:
            norm_origin = origin.rstrip("/")
            if norm_origin not in norm_allowed:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"code": "FORBIDDEN", "message": "CSRF verification failed: Origin not allowed."},
                )

        # 3. Check for Bearer API exemption
        auth_header = request.headers.get("authorization", "")
        has_bearer = auth_header.lower().startswith("bearer ")
        cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)

        if has_bearer:
            # If both cookie and bearer are present:
            if cookie_token:
                bearer_token = auth_header[7:].strip()
                # If they match, explicit Bearer authentication is accepted and exempt from CSRF
                if cookie_token == bearer_token:
                    return await call_next(request)
                # If they do not match, allow request to reach auth middleware for 400 rejection
            else:
                # Pure Bearer request with no cookie session: bypass CSRF
                return await call_next(request)

        # 4. Determine if CSRF token verification is required
        # Required for:
        # a) Browser requests (Origin header present)
        # b) Requests presenting an ambient cookie session on state-changing endpoints
        # c) Explicit CSRF validation requests (header present)
        cookie_csrf = request.cookies.get(CSRF_COOKIE_NAME)
        header_csrf = request.headers.get(CSRF_HEADER_NAME)

        requires_csrf = False
        if origin:
            requires_csrf = True
        elif cookie_token:
            if request.url.path not in {"/api/auth/register", "/api/auth/login"}:
                requires_csrf = True
        elif header_csrf:
            requires_csrf = True

        if requires_csrf:
            if not header_csrf:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"code": "FORBIDDEN", "message": "CSRF verification failed: Missing X-CSRF-Token header."},
                )

            if not cookie_csrf:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"code": "FORBIDDEN", "message": "CSRF verification failed: Missing csrf_token cookie."},
                )

            # Determine expected session binding (prefer JWT jti for authenticated sessions, "anon" for unauthenticated)
            expected_binding = "anon"
            if cookie_token:
                try:
                    from backend.app.services.auth_service import decode_access_token
                    token_payload = decode_access_token(cookie_token, verify_exp=False)
                    expected_binding = token_payload.get("jti") or "anon"
                except Exception:
                    expected_binding = "anon"

            # Validate HMAC signature, expiry, and session binding of header token
            if not validate_csrf_token(header_csrf, expected_binding=expected_binding):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"code": "FORBIDDEN", "message": "CSRF verification failed: Expired or invalid CSRF token."},
                )

            # Validate cookie token and enforce double-submit matching
            if not validate_csrf_token(cookie_csrf, expected_binding=expected_binding) or not hmac.compare_digest(header_csrf, cookie_csrf):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"code": "FORBIDDEN", "message": "CSRF verification failed: CSRF token mismatch or tampering detected."},
                )

        response = await call_next(request)
        return response
