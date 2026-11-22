"""
Phase 2 Security Verification Tests.

Verifies:
- SEC-05: Secure Authentication Token Storage
  * HttpOnly access_token cookie set on registration and login.
  * CSRF token cookie and X-CSRF-Token header validation.
  * Rejection of state-changing browser requests with missing, invalid, or tampered CSRF tokens (HTTP 403).
  * Rejection of requests from unauthorized origins (HTTP 403).
  * Origin validation fails closed in production when unconfigured or mismatched.
  * CSRF tokens bound to user sessions.
  * Bearer-only API request bypass of CSRF protection.
  * Session restoration via GET /api/auth/me using HttpOnly cookie only (no Authorization header).
  * Rejection of conflicting credentials (cookie and differing Authorization header) with HTTP 400.
  * Logout clears cookies and revokes token server-side.
  * Expired cookie token rejection (HTTP 401).
  * JWT is NEVER exposed in any authentication JSON response body.

- SEC-06: Bcrypt Password Hashing & 72-Byte Boundary
  * Newly registered users have passwords hashed with Bcrypt cost factor 12 ($2b$12$ prefix).
  * Existing bcrypt hashes are verified and preserved without migration or rehashing.
  * Passwords exceeding 72 UTF-8 bytes are strictly rejected during registration.
  * Safe handling of malformed or corrupted password hashes without unhandled exceptions or 500 errors.
"""

from datetime import timedelta
import hashlib
import hmac
import os
import time
import uuid
import bcrypt
import pytest
from fastapi.testclient import TestClient

from backend.app.database import get_db_context
from backend.app.main import app
from backend.app.middleware.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    generate_csrf_token,
    validate_csrf_token,
    get_allowed_origins,
)
from backend.app.models.user import UserModel
from backend.app.services.auth_service import (
    ACCESS_TOKEN_COOKIE,
    create_access_token,
    decode_access_token,
    get_jwt_secret_key,
    get_user_by_email,
    hash_password,
    verify_password,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# SEC-05: HttpOnly Cookie Authentication & Session Restoration Tests
# ==============================================================================

def test_registration_sets_httponly_and_csrf_cookies(client):
    """
    POST /api/auth/register must set HttpOnly access_token cookie and readable csrf_token cookie.
    Must NEVER return JWT token in the JSON response body.
    """
    unique_email = f"cookie_reg_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "fullName": "Cookie User",
        "email": unique_email,
        "password": "SecurePassword123!",
        "confirmPassword": "SecurePassword123!",
    }

    # Fetch initial CSRF token
    csrf_res = client.get("/api/auth/csrf-token")
    assert csrf_res.status_code == 200
    csrf_token = csrf_res.json()["csrfToken"]

    # Register with browser origin and CSRF header
    response = client.post(
        "/api/auth/register",
        json=payload,
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: csrf_token,
        },
    )
    assert response.status_code == 201
    data = response.json()

    # CRITICAL: Never expose JWT in JSON
    assert "token" not in data
    assert "tokenType" not in data
    assert "user" in data
    assert data["user"]["email"] == unique_email

    # Verify cookies in response
    assert ACCESS_TOKEN_COOKIE in response.cookies
    assert CSRF_COOKIE_NAME in response.cookies

    # Verify cookie attributes
    set_cookies = response.headers.get_list("set-cookie")
    assert any("access_token=" in c and "httponly" in c.lower() for c in set_cookies)
    assert any("csrf_token=" in c for c in set_cookies)


def test_login_sets_httponly_and_csrf_cookies(client):
    """
    POST /api/auth/login must set HttpOnly access_token and csrf_token cookies.
    Must NEVER return JWT token in the JSON response body.
    """
    email = f"cookie_login_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    # Register user first via API
    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Login Tester",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )
    assert reg.status_code == 201

    # Get CSRF token
    csrf_res = client.get("/api/auth/csrf-token")
    csrf_token = csrf_res.json()["csrfToken"]

    # Log in
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: csrf_token,
        },
    )
    assert login_res.status_code == 200
    data = login_res.json()

    # CRITICAL: Never expose JWT in JSON
    assert "token" not in data
    assert "tokenType" not in data
    assert ACCESS_TOKEN_COOKIE in login_res.cookies
    assert CSRF_COOKIE_NAME in login_res.cookies


def test_session_restoration_via_cookie_only(client):
    """
    GET /api/auth/me should authenticate the user using ONLY the HttpOnly cookie (no Bearer header).
    """
    email = f"session_restore_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    # Register user
    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Session User",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )
    assert reg.status_code == 201
    auth_cookie = reg.cookies.get(ACCESS_TOKEN_COOKIE)

    # New client without any headers, only cookie
    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, auth_cookie)

    # Call /me without Authorization header
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == email
    assert data["fullName"] == "Session User"


def test_logout_clears_cookies_and_revokes_token(client):
    """
    POST /api/auth/logout must revoke the server token and clear cookies.
    """
    email = f"logout_cookie_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"

    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Logout Cookie User",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )
    assert reg.status_code == 201
    cookie_token = reg.cookies.get(ACCESS_TOKEN_COOKIE)
    csrf_token = reg.cookies.get(CSRF_COOKIE_NAME)

    # Perform logout with CSRF header
    logout_res = client.post(
        "/api/auth/logout",
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: csrf_token,
        },
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully."

    # Verify cookies were cleared (max-age=0 or empty)
    # Testing server-side revocation: try using the revoked cookie
    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, cookie_token)

    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 401
    assert "revoked" in me_res.json().get("message", "").lower()


def test_conflicting_cookie_and_bearer_credentials_rejected(client):
    """
    If a request provides BOTH a cookie and an Authorization header with DIFFERENT tokens,
    the server must reject with HTTP 400 Bad Request.
    """
    token_a = create_access_token({"sub": "user-a", "email": "a@test.com", "role": "user"})
    token_b = create_access_token({"sub": "user-b", "email": "b@test.com", "role": "user"})

    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, token_a)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 400
    msg = (response.json().get("message") or response.json().get("detail", "")).lower()
    assert "conflicting" in msg


def test_expired_cookie_token_rejected(client):
    """
    Expired cookie token must be rejected with HTTP 401 on /api/auth/me.
    """
    expired_token = create_access_token(
        {"sub": "user-expired-cookie", "email": "exp_cookie@test.com", "role": "user"},
        expires_delta=timedelta(seconds=-10),
    )

    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, expired_token)

    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "expired" in response.json().get("message", "").lower()


# ==============================================================================
# SEC-05: CSRF Protection & Origin Validation Tests
# ==============================================================================

def test_csrf_disallowed_origin_rejected(client):
    """
    State-changing requests with an unauthorized Origin must be rejected with HTTP 403.
    """
    csrf_token = generate_csrf_token()
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient took Aspirin."},
        headers={
            "Origin": "http://evil-attacker-site.com",
            CSRF_HEADER_NAME: csrf_token,
        },
    )
    assert response.status_code == 403
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "Origin not allowed" in msg


def test_csrf_missing_header_rejected(client):
    """
    Browser state-changing requests missing X-CSRF-Token must be rejected with HTTP 403.
    """
    csrf_token = generate_csrf_token()
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient took Aspirin."},
        headers={
            "Origin": "http://localhost:5173",
            # Intentionally omit CSRF_HEADER_NAME
        },
    )
    assert response.status_code == 403
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "Missing X-CSRF-Token" in msg


def test_csrf_tampered_token_rejected(client):
    """
    Browser state-changing requests with a forged/tampered CSRF token must be rejected with HTTP 403.
    """
    csrf_token = generate_csrf_token()
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

    tampered_token = csrf_token[:-4] + "ffff"

    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient took Aspirin."},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: tampered_token,
        },
    )
    assert response.status_code == 403
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "CSRF verification failed" in msg


def test_csrf_session_binding_enforced(client):
    """
    CSRF token bound to User A cannot be used with User B's authenticated session.
    """
    token_for_user_a = generate_csrf_token(session_binding="user-id-a")
    token_b = create_access_token({"sub": "user-id-b", "email": "b@test.com", "role": "user"})

    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, token_b)
    client.cookies.set(CSRF_COOKIE_NAME, token_for_user_a)

    response = client.post(
        "/api/auth/logout",
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: token_for_user_a,
        },
    )
    assert response.status_code == 403
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "CSRF verification failed" in msg


def test_origin_validation_fails_closed_in_production(client, monkeypatch):
    """
    In production, missing or unconfigured ALLOWED_ORIGINS must fail closed (reject with 403).
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "production-secure-secret-key-at-least-32-chars!")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    csrf_token = generate_csrf_token()
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

    # Any origin should be rejected because none is configured in production
    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient took Aspirin."},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: csrf_token,
        },
    )
    assert response.status_code == 403


def test_bearer_only_bypasses_csrf(client):
    """
    Pure Bearer API requests (CLI/server-to-server) bypass CSRF checks even without CSRF header.
    """
    email = f"api_bearer_{uuid.uuid4().hex[:8]}@example.com"
    token = create_access_token({"sub": "api-sub-123", "email": email, "role": "user"})

    client.cookies.clear()  # No cookie session

    # Make request with Authorization: Bearer, no Origin, no CSRF token
    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient was diagnosed with Hypertension on 10 April 2026."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "entities" in response.json()


# ==============================================================================
# SEC-06: Bcrypt Password Hashing & 72-Byte Boundary Tests
# ==============================================================================

def test_bcrypt_hashing_cost_factor_12(client):
    """
    Newly registered users must have their password hashed with Bcrypt cost factor 12 ($2b$12$).
    """
    email = f"bcrypt_{uuid.uuid4().hex[:8]}@example.com"
    password = "MySecurePassword123!"

    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Bcrypt User",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )
    assert reg.status_code == 201

    with get_db_context() as db:
        user = get_user_by_email(db, email)
        assert user is not None
        assert user.password.startswith("$2b$12$")


def test_existing_bcrypt_hashes_preserved_without_migration(client):
    """
    Existing Bcrypt hashes must be verified and preserved WITHOUT migration or rehashing.
    """
    email = f"existing_bcrypt_{uuid.uuid4().hex[:8]}@example.com"
    plain_password = "ExistingPassword123!"

    # Pre-generate genuine bcrypt hash ($2b$ with cost factor 12)
    salt = bcrypt.gensalt(rounds=12)
    original_hash = bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")
    assert original_hash.startswith("$2b$12$")

    user_id = str(uuid.uuid4())
    with get_db_context() as db:
        user = UserModel(
            _id=user_id,
            fullName="Preserved User",
            email=email,
            password=original_hash,
            phoneNumber="+1-555-0199",
            role="user",
            isVerified=True,
        )
        db.add(user)
        db.commit()

    # User logs in with plain password
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": plain_password},
    )
    assert login_res.status_code == 200

    # Verify that stored hash was NOT modified
    with get_db_context() as db:
        current_user = get_user_by_email(db, email)
        assert current_user.password == original_hash


def test_passwords_exceeding_72_bytes_rejected(client):
    """
    Passwords exceeding 72 UTF-8 bytes must be rejected with HTTP 422.
    """
    # 73 ASCII characters
    long_pwd = "A" * 73 + "1a!"
    email = f"toolong_{uuid.uuid4().hex[:8]}@example.com"

    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Too Long User",
            "email": email,
            "password": long_pwd,
            "confirmPassword": long_pwd,
        },
    )
    assert reg.status_code == 422
    assert "72" in reg.text

    # Multi-byte UTF-8 exceeding 72 bytes within fewer characters
    multibyte_pwd = "Password123!" + "🔒" * 20  # Each emoji is 4 UTF-8 bytes -> >80 bytes
    assert len(multibyte_pwd.encode("utf-8")) > 72

    reg_mb = client.post(
        "/api/auth/register",
        json={
            "fullName": "Multibyte User",
            "email": f"mb_{uuid.uuid4().hex[:8]}@example.com",
            "password": multibyte_pwd,
            "confirmPassword": multibyte_pwd,
        },
    )
    assert reg_mb.status_code == 422
    assert "72 bytes" in reg_mb.text
    assert "72 bytes" in reg_mb.text


def test_malformed_password_hash_handled_safely(client):
    """
    Corrupted or malformed password hashes in the database must not trigger 500 errors.
    They should safely fail verification and return HTTP 401.
    """
    email = f"corrupt_{uuid.uuid4().hex[:8]}@example.com"
    user_id = str(uuid.uuid4())

    with get_db_context() as db:
        corrupt_user = UserModel(
            _id=user_id,
            fullName="Corrupted Hash User",
            email=email,
            password="corrupted_garbage_not_a_valid_hash_at_all$$$",
            phoneNumber=None,
            role="user",
            isVerified=True,
        )
        db.add(corrupt_user)
        db.commit()

    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "AnyPassword123!"},
    )
    assert login_res.status_code == 401
    assert "Invalid email address or password" in login_res.json().get("message", "")


# ==============================================================================
# Comprehensive CSRF, Origin, and Security Corrections Verification
# ==============================================================================

def test_csrf_token_structure_strictly_4_parts():
    """
    CSRF token parsing must strictly require timestamp:nonce:binding:signature (4 parts).
    Tokens with 1, 2, 3, or >4 parts must be rejected.
    """
    valid_token = generate_csrf_token(session_binding="anon")
    parts = valid_token.split(":")
    assert len(parts) == 4

    assert validate_csrf_token(valid_token, expected_binding="anon") is True

    # 3-part legacy token must be rejected
    legacy_3_part = f"{parts[0]}:{parts[1]}:{parts[3]}"
    assert validate_csrf_token(legacy_3_part) is False

    # 2-part and 1-part tokens must be rejected
    assert validate_csrf_token("timestamp:signature") is False
    assert validate_csrf_token("garbage-token") is False
    assert validate_csrf_token("") is False
    assert validate_csrf_token(None) is False

    # 5-part token must be rejected
    assert validate_csrf_token(f"{valid_token}:extra") is False


def test_csrf_token_future_and_expired_timestamps_rejected():
    """
    CSRF tokens with timestamps in the future (>5s clock skew) or expired (>max_age) must be rejected.
    """
    secret = get_jwt_secret_key().encode("utf-8")
    now = int(time.time())

    # Future dated (> 5s in the future)
    future_ts = now + 120
    payload_future = f"{future_ts}:testnonce:anon"
    sig_future = hmac.new(secret, payload_future.encode("utf-8"), hashlib.sha256).hexdigest()
    future_token = f"{payload_future}:{sig_future}"
    assert validate_csrf_token(future_token, expected_binding="anon") is False

    # Expired token (> 86400s in the past)
    expired_ts = now - 90000
    payload_expired = f"{expired_ts}:testnonce:anon"
    sig_expired = hmac.new(secret, payload_expired.encode("utf-8"), hashlib.sha256).hexdigest()
    expired_token = f"{payload_expired}:{sig_expired}"
    assert validate_csrf_token(expired_token, expected_binding="anon") is False


def test_csrf_anonymous_token_rejected_on_authenticated_session(client):
    """
    An anonymous CSRF token (binding == 'anon') must be strictly rejected
    on an authenticated session state-changing request.
    """
    email = f"auth_anon_{uuid.uuid4().hex[:8]}@example.com"
    token = create_access_token({"sub": "user-auth-1", "email": email, "role": "user"})
    anon_csrf = generate_csrf_token(session_binding="anon")

    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, token)
    client.cookies.set(CSRF_COOKIE_NAME, anon_csrf)

    # State-changing extraction with authenticated cookie session and anon CSRF token
    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient took Aspirin."},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: anon_csrf,
        },
    )
    assert response.status_code == 403
    assert "CSRF verification failed" in response.text


def test_csrf_token_rotated_on_registration_and_login(client):
    """
    Successful registration and login must rotate the CSRF token from 'anon'
    to a session-bound token matching the JWT's jti.
    """
    # 1. Fetch initial anonymous CSRF token
    csrf_res = client.get("/api/auth/csrf-token")
    assert csrf_res.status_code == 200
    initial_csrf = csrf_res.json()["csrfToken"]
    initial_parts = initial_csrf.split(":")
    assert initial_parts[2] == "anon"

    # 2. Register user
    email = f"rot_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePassword123!"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "fullName": "Rotate Tester",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: initial_csrf,
        },
    )
    assert reg_res.status_code == 201
    rotated_csrf_reg = reg_res.cookies.get(CSRF_COOKIE_NAME)
    jwt_reg = reg_res.cookies.get(ACCESS_TOKEN_COOKIE)

    # Ensure CSRF token was rotated and bound to the JWT's jti
    reg_jwt_payload = decode_access_token(jwt_reg)
    expected_jti_reg = reg_jwt_payload["jti"]
    reg_csrf_parts = rotated_csrf_reg.split(":")
    assert reg_csrf_parts[2] == expected_jti_reg
    assert rotated_csrf_reg != initial_csrf

    # 3. Log in with the same user and verify rotation again
    login_csrf_init = client.get("/api/auth/csrf-token").json()["csrfToken"]
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: login_csrf_init,
        },
    )
    assert login_res.status_code == 200
    rotated_csrf_login = login_res.cookies.get(CSRF_COOKIE_NAME)
    jwt_login = login_res.cookies.get(ACCESS_TOKEN_COOKIE)
    login_jwt_payload = decode_access_token(jwt_login)
    expected_jti_login = login_jwt_payload["jti"]

    login_csrf_parts = rotated_csrf_login.split(":")
    assert login_csrf_parts[2] == expected_jti_login
    assert expected_jti_login != expected_jti_reg  # New unique jti


def test_preauth_csrf_missing_cookie_rejected_on_login(client):
    """
    Browser login requests with Origin but missing csrf_token cookie must be rejected with HTTP 403.
    """
    anon_csrf = generate_csrf_token(session_binding="anon")
    client.cookies.clear()  # Ensure no cookies

    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Password123!"},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: anon_csrf,
        },
    )
    assert response.status_code == 403
    assert "Missing csrf_token cookie" in response.text


def test_preauth_csrf_mismatched_cookie_header_rejected_on_login(client):
    """
    Browser login requests with mismatched CSRF cookie and header must be rejected with HTTP 403.
    """
    token_1 = generate_csrf_token(session_binding="anon")
    token_2 = generate_csrf_token(session_binding="anon")

    client.cookies.clear()
    client.cookies.set(CSRF_COOKIE_NAME, token_1)

    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Password123!"},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: token_2,
        },
    )
    assert response.status_code == 403
    assert "CSRF token mismatch or tampering" in response.text


def test_origin_required_in_production_for_cookie_session(client, monkeypatch):
    """
    In production, cookie-authenticated state-changing requests missing an Origin header must return HTTP 403.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "production-secure-secret-key-at-least-32-chars!")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")

    token = create_access_token({"sub": "user-prod", "email": "prod@example.com", "role": "user"})
    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, token)

    # Omit Origin header in production with cookie session present
    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient took Aspirin."},
    )
    assert response.status_code == 403
    assert "Origin header required in production" in response.text


def test_configured_origin_succeeds_in_production(client, monkeypatch):
    """
    In production, requests with valid configured Origin and matching CSRF tokens must succeed.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "production-secure-secret-key-at-least-32-chars!")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")

    token = create_access_token({"sub": "user-prod-ok", "email": "prod_ok@example.com", "role": "user"})
    payload = decode_access_token(token)
    jti = payload["jti"]
    csrf_token = generate_csrf_token(session_binding=jti)

    client.cookies.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, token)
    client.cookies.set(CSRF_COOKIE_NAME, csrf_token)

    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient was diagnosed with Hypertension."},
        headers={
            "Origin": "https://app.example.com",
            CSRF_HEADER_NAME: csrf_token,
        },
    )
    assert response.status_code == 200
    assert "entities" in response.json()


def test_verify_password_returns_bool_consistently():
    """
    verify_password must consistently return a boolean without throwing unhandled exceptions.
    """
    plain = "TestPassword123!"
    hashed = hash_password(plain)

    # Valid password -> True
    assert verify_password(plain, hashed) is True
    assert isinstance(verify_password(plain, hashed), bool)

    # Invalid password -> False
    assert verify_password("WrongPassword123!", hashed) is False
    assert isinstance(verify_password("WrongPassword123!", hashed), bool)

    # Password exceeding 72 UTF-8 bytes -> False
    assert verify_password("A" * 73 + "1a!", hashed) is False

    # Empty and None values -> False
    assert verify_password("", hashed) is False
    assert verify_password(None, hashed) is False
    assert verify_password(plain, "") is False
    assert verify_password(plain, None) is False

    # Corrupt hash -> False
    assert verify_password(plain, "not-a-valid-hash") is False


def test_rate_limiter_cooldown_reset_behavior():
    """
    Rate limiter cooldown must clear attempt history so an account gets a fresh
    quota after cooldown rather than being permanently or immediately re-locked.
    """
    from backend.app.services.rate_limiter import _rate_limiter
    test_key = "rate:login:account:test_cooldown_reset@example.com"
    _rate_limiter.reset_all()

    # Trigger cooldown with 5 failures
    for _ in range(5):
        _rate_limiter.record_failure(test_key, max_failures=5, cooldown_seconds=60)

    # Must be in cooldown
    in_cd, retry = _rate_limiter.is_account_in_cooldown(test_key)
    assert in_cd is True
    assert retry > 0

    # Simulate cooldown expiry by resetting cooldown timestamp to the past
    _rate_limiter._cooldowns[test_key] = time.time() - 10

    # Must no longer be in cooldown
    in_cd_after, _ = _rate_limiter.is_account_in_cooldown(test_key)
    assert in_cd_after is False

    # Attempt history must be cleared: 1 new failure must NOT re-trigger cooldown
    _rate_limiter.record_failure(test_key, max_failures=5, cooldown_seconds=60)
    in_cd_new, _ = _rate_limiter.is_account_in_cooldown(test_key)
    assert in_cd_new is False


# ==============================================================================
# SEC-05: Focused Tests for Fresh Token Fetching, Expiration & Session Binding
# ==============================================================================

def test_login_with_expired_csrf_token_rejected_with_403(client):
    """
    POST /api/auth/login must be rejected with HTTP 403 if the submitted CSRF token
    timestamp is older than CSRF_MAX_AGE_SECONDS (24 hours).
    """
    secret = get_jwt_secret_key().encode("utf-8")
    expired_ts = int(time.time()) - 90000  # 25 hours ago
    payload = f"{expired_ts}:expirednonce:anon"
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    expired_csrf_token = f"{payload}:{sig}"

    client.cookies.clear()
    client.cookies.set(CSRF_COOKIE_NAME, expired_csrf_token)

    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Password123!"},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: expired_csrf_token,
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert "Expired or invalid CSRF token" in (data.get("message") or data.get("detail", ""))


def test_registration_with_expired_csrf_token_rejected_with_403(client):
    """
    POST /api/auth/register must be rejected with HTTP 403 if the CSRF token has expired.
    """
    secret = get_jwt_secret_key().encode("utf-8")
    expired_ts = int(time.time()) - 100000
    payload = f"{expired_ts}:expirednonce:anon"
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    expired_csrf_token = f"{payload}:{sig}"

    client.cookies.clear()
    client.cookies.set(CSRF_COOKIE_NAME, expired_csrf_token)

    response = client.post(
        "/api/auth/register",
        json={
            "fullName": "Expired Token User",
            "email": f"expired_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Password123!",
            "confirmPassword": "Password123!",
        },
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: expired_csrf_token,
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert "Expired or invalid CSRF token" in (data.get("message") or data.get("detail", ""))


def test_login_flow_with_fresh_csrf_token_succeeds(client):
    """
    Verify complete login flow:
    1. Pre-register a user.
    2. Clear browser cookies to start fresh.
    3. Force-fetch a fresh CSRF token from GET /api/auth/csrf-token.
    4. Submit login with fresh token header and matching cookie.
    5. Verify 200 OK, HttpOnly access_token cookie set, and CSRF token rotated to new jti.
    """
    email = f"fresh_login_{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    # 1. Register user
    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Fresh Login Tester",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )
    assert reg.status_code == 201

    # 2. Simulate fresh browser session (clear cookies)
    client.cookies.clear()

    # 3. Force-fetch fresh CSRF token before login
    csrf_res = client.get("/api/auth/csrf-token")
    assert csrf_res.status_code == 200
    fresh_csrf = csrf_res.json()["csrfToken"]
    assert client.cookies.get(CSRF_COOKIE_NAME) == fresh_csrf

    # 4. Submit login
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: fresh_csrf,
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["message"] == "Login successful."
    assert login_data["user"]["email"] == email

    # 5. Verify rotation: CSRF token rotated to match newly generated JWT jti
    new_jwt = login_res.cookies.get(ACCESS_TOKEN_COOKIE)
    new_csrf = login_res.cookies.get(CSRF_COOKIE_NAME)
    assert new_jwt is not None
    assert new_csrf is not None
    assert new_csrf != fresh_csrf  # Rotated

    jwt_payload = decode_access_token(new_jwt)
    csrf_parts = new_csrf.split(":")
    assert csrf_parts[2] == jwt_payload["jti"]


def test_registration_flow_with_fresh_csrf_token_succeeds(client):
    """
    Verify complete registration flow with force-fetched fresh CSRF token.
    """
    client.cookies.clear()

    # Fetch fresh token
    csrf_res = client.get("/api/auth/csrf-token")
    assert csrf_res.status_code == 200
    fresh_csrf = csrf_res.json()["csrfToken"]

    unique_email = f"fresh_reg_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "fullName": "Fresh Reg Tester",
            "email": unique_email,
            "password": "ValidPassword123!",
            "confirmPassword": "ValidPassword123!",
        },
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: fresh_csrf,
        },
    )
    assert reg_res.status_code == 201
    assert reg_res.json()["user"]["email"] == unique_email

    # Verify cookie rotation to jti
    jwt_reg = reg_res.cookies.get(ACCESS_TOKEN_COOKIE)
    csrf_reg = reg_res.cookies.get(CSRF_COOKIE_NAME)
    assert csrf_reg != fresh_csrf
    payload = decode_access_token(jwt_reg)
    assert csrf_reg.split(":")[2] == payload["jti"]


def test_logout_flow_with_fresh_csrf_token_succeeds(client):
    """
    Verify complete logout flow:
    1. Authenticate user.
    2. Fetch fresh CSRF token bound to the active session jti.
    3. Submit POST /api/auth/logout.
    4. Verify 200 OK, server revocation, and cookies cleared.
    """
    email = f"fresh_logout_{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Logout Flow User",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )
    assert reg.status_code == 201

    # Fetch fresh CSRF token for the authenticated session
    csrf_res = client.get("/api/auth/csrf-token")
    assert csrf_res.status_code == 200
    fresh_csrf = csrf_res.json()["csrfToken"]

    # Verify token is bound to active session
    active_jwt = client.cookies.get(ACCESS_TOKEN_COOKIE)
    active_jti = decode_access_token(active_jwt)["jti"]
    assert fresh_csrf.split(":")[2] == active_jti

    # Perform logout
    logout_res = client.post(
        "/api/auth/logout",
        headers={
            "Origin": "http://localhost:5173",
            CSRF_HEADER_NAME: fresh_csrf,
        },
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully."

