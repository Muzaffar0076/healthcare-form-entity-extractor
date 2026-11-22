"""
Authentication API routes: registration, login, current user profile, logout, and CSRF tokens.

Hardened with Phase 1 & Phase 2 Security Controls:
- SEC-01: Secure cryptographic keys
- SEC-02: CORS origin protection
- SEC-03: Rate limiting on registration and login endpoints
- SEC-04: Unique JTI claims and persistent token revocation
- SEC-05: HttpOnly cookie authentication and CSRF token binding
- SEC-06: Bcrypt password hashing (cost factor 12) strictly enforcing <= 72 UTF-8 bytes
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user, security
from backend.app.middleware.csrf import generate_csrf_token, set_csrf_cookie
from backend.app.models.user import UserModel
from backend.app.schemas import (
    AuthResponse,
    AuthTokenResponse,
    CSRFTokenResponse,
    LogoutResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from backend.app.services.auth_service import (
    ACCESS_TOKEN_COOKIE,
    authenticate_user,
    clear_auth_cookies,
    create_access_token,
    create_user,
    get_user_by_email,
    revoke_token,
    set_auth_cookies,
)
from backend.app.services.rate_limiter import (
    check_login_rate_limit,
    check_registration_rate_limit,
    record_failed_login,
    record_successful_login,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/csrf-token",
    response_model=CSRFTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve CSRF Token",
    description="Returns a signed, time-bound CSRF token and sets the csrf_token cookie.",
)
def get_csrf_token(request: Request, response: Response) -> CSRFTokenResponse:
    """
    Issue a new cryptographically signed CSRF token for state-changing requests.
    If authenticated via cookie, binds to active session jti; otherwise binds to 'anon'.
    """
    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    binding = "anon"
    if cookie_token:
        try:
            from backend.app.services.auth_service import decode_access_token
            payload = decode_access_token(cookie_token, verify_exp=False)
            binding = payload.get("jti") or "anon"
        except Exception:
            binding = "anon"
    token = set_csrf_cookie(response, session_binding=binding)
    return CSRFTokenResponse(csrfToken=token)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user account with bcrypt password hashing, sets HttpOnly auth cookies, and returns user profile.",
)
def register(
    request: Request,
    response: Response,
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """
    Register a new user with unique email, validated password, and optional phone number.
    Rate-limited per IP. Sets HttpOnly access_token cookie (JWT is never exposed in response body).
    """
    # SEC-03: Rate limiting check
    check_registration_rate_limit(request)

    existing_user = get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # SEC-06: Create user with bcrypt password hashing (cost factor 12)
    user = create_user(db, payload)
    token = create_access_token(
        data={"sub": user._id, "email": user.email, "role": user.role}
    )

    # SEC-05: Set HttpOnly access_token cookie and readable csrf_token cookie (bound to jti)
    csrf_token = set_auth_cookies(response, token)

    return AuthResponse(
        message="User registered successfully.",
        user=UserResponse(**user.to_dict()),
        csrfToken=csrf_token,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate existing user",
    description="Authenticates user credentials using bcrypt, sets HttpOnly auth cookies, and returns user profile.",
)
def login(
    request: Request,
    response: Response,
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """
    Authenticate user using email and password.
    Rate-limited per IP and account cooldown. Sets HttpOnly access_token cookie (JWT is never exposed in response body).
    """
    # SEC-03: Rate limiting and cooldown check
    check_login_rate_limit(request, payload.email)

    # SEC-06: Verifies bcrypt password hash
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        record_failed_login(request, payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failure tracking on success
    record_successful_login(request, payload.email)

    token = create_access_token(
        data={"sub": user._id, "email": user.email, "role": user.role}
    )

    # SEC-05: Set HttpOnly access_token cookie and readable csrf_token cookie (bound to jti)
    csrf_token = set_auth_cookies(response, token)

    return AuthResponse(
        message="Login successful.",
        user=UserResponse(**user.to_dict()),
        csrfToken=csrf_token,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user profile",
    description="Retrieves the profile information of the currently authenticated user (supports both HttpOnly cookies and Bearer tokens).",
)
def get_me(
    request: Request,
    response: Response,
    current_user: UserModel = Depends(get_current_user),
) -> UserResponse:
    """
    Get profile data for the active user session. Also refreshes the CSRF token cookie bound to session jti.
    """
    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    binding = "anon"
    if cookie_token:
        try:
            from backend.app.services.auth_service import decode_access_token
            payload = decode_access_token(cookie_token, verify_exp=False)
            binding = payload.get("jti") or "anon"
        except Exception:
            binding = "anon"
    set_csrf_cookie(response, session_binding=binding)
    return UserResponse(**current_user.to_dict())


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out active session",
    description="Revokes the active JWT token server-side, terminates the session, and clears authentication cookies.",
)
def logout(
    request: Request,
    response: Response,
    current_user: UserModel = Depends(get_current_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """
    Log out active user session:
    1. Revokes JWT token in server-side blacklist.
    2. Clears HttpOnly access_token and csrf_token cookies.
    """
    # Extract token from either cookie or header
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token and credentials and credentials.credentials:
        token = credentials.credentials

    # SEC-04: Server-side token revocation
    if token:
        revoke_token(db, token)

    # SEC-05: Clear cookies
    clear_auth_cookies(response)

    return LogoutResponse(message="Logged out successfully.")
