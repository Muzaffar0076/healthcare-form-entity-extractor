"""
Phase 1 Security Verification Tests.

Verifies:
- SEC-01: JWT Secret Management (production startup failure on missing/insecure keys).
- SEC-02: Strict CORS origin whitelisting (rejection of unauthorized origins).
- SEC-03: Rate Limiting on registration and login endpoints (HTTP 429 & Retry-After).
- SEC-04: JWT Unique JTI claim, server-side revocation on logout, and rejection of revoked tokens.
- Token expiration enforcement.
"""

from datetime import timedelta
import os
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.auth_service import (
    create_access_token,
    decode_access_token,
    get_jwt_secret_key,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# SEC-01: JWT Secret Management Tests
# ==============================================================================

def test_jwt_secret_production_enforcement(monkeypatch):
    """
    In production mode, missing or insecure JWT secrets must fail startup immediately.
    """
    # 1. Missing secret in production
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        get_jwt_secret_key()
    assert "JWT_SECRET_KEY environment variable is required in production" in str(exc_info.value)

    # 2. Insecure / short secret in production (< 32 chars)
    monkeypatch.setenv("JWT_SECRET_KEY", "too-short-secret")
    with pytest.raises(RuntimeError) as exc_info2:
        get_jwt_secret_key()
    assert "The configured JWT_SECRET_KEY is insecure" in str(exc_info2.value)

    # 3. Secure 32+ character key in production
    secure_key = "a" * 32
    monkeypatch.setenv("JWT_SECRET_KEY", secure_key)
    assert get_jwt_secret_key() == secure_key


def test_jwt_secret_development_fallback(monkeypatch):
    """
    In development mode, a missing secret key falls back gracefully with a warning.
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    secret = get_jwt_secret_key()
    assert len(secret) >= 32


# ==============================================================================
# SEC-02: CORS Origin Whitelisting Tests
# ==============================================================================

def test_cors_allowed_origin(client):
    """
    Whitelisted origins must receive proper Access-Control headers and credentials.
    """
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin(client):
    """
    Non-whitelisted origins must NOT receive Access-Control-Allow-Origin headers.
    """
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://untrusted-malicious-domain.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # The header must either be omitted or not match the malicious origin
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != "http://untrusted-malicious-domain.com"
    assert allow_origin != "*"


# ==============================================================================
# SEC-03: Rate Limiting Tests
# ==============================================================================

def test_registration_rate_limiting(client):
    """
    Rapid registration requests exceeding the threshold must return HTTP 429.
    """
    # Attempt rapid registrations from the same client IP
    responses = []
    for i in range(15):
        email = f"spam_reg_{uuid.uuid4().hex[:6]}@example.com"
        r = client.post(
            "/api/auth/register",
            json={
                "fullName": f"Spam User {i}",
                "email": email,
                "password": "Password123!",
                "confirmPassword": "Password123!",
            },
        )
        responses.append(r)

    # At least one of the requests must be blocked with HTTP 429
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes

    rate_limited_res = next(r for r in responses if r.status_code == 429)
    assert "Retry-After" in rate_limited_res.headers
    data = rate_limited_res.json()
    assert "Too many registration requests" in data.get("message", "")


def test_login_account_cooldown_rate_limiting(client):
    """
    Repeated failed login attempts for a specific account must trigger a cooldown (HTTP 429).
    """
    target_email = f"cooldown_{uuid.uuid4().hex[:8]}@example.com"

    # Register the target account first
    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Cooldown Target",
            "email": target_email,
            "password": "CorrectPassword123!",
            "confirmPassword": "CorrectPassword123!",
        },
        headers={"X-Forwarded-For": "198.51.100.1"},
    )
    # If already rate-limited on IP, handle gracefully
    if reg.status_code == 429:
        pytest.skip("Skipping due to previous IP throttling")

    # Send 6 consecutive failed password attempts for this specific account
    login_statuses = []
    for i in range(7):
        r = client.post(
            "/api/auth/login",
            json={"email": target_email, "password": "WrongPassword999!"},
            headers={"X-Forwarded-For": f"198.51.100.{10 + i}"},  # Vary IP to isolate account cooldown
        )
        login_statuses.append(r.status_code)

    # After exceeding 5 failures, the response must be HTTP 429
    assert 429 in login_statuses


# ==============================================================================
# SEC-04: JWT JTI and Token Revocation Tests
# ==============================================================================

def test_jwt_contains_unique_jti():
    """
    Generated JWTs must include a unique UUID v4 'jti' claim.
    """
    token1 = create_access_token({"sub": "user-1", "email": "u1@test.com", "role": "user"})
    token2 = create_access_token({"sub": "user-1", "email": "u1@test.com", "role": "user"})

    payload1 = decode_access_token(token1)
    payload2 = decode_access_token(token2)

    assert "jti" in payload1
    assert "jti" in payload2
    assert payload1["jti"] != payload2["jti"]
    assert len(payload1["jti"]) == 36


def test_logout_revokes_token(client):
    """
    Logging out must revoke the token server-side, preventing subsequent use on /me.
    """
    unique_email = f"revoked_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": "Revoke Tester",
            "email": unique_email,
            "password": "Password123!",
            "confirmPassword": "Password123!",
        },
        headers={"X-Forwarded-For": f"203.0.113.{uuid.uuid4().int % 250}"},
    )
    assert reg.status_code == 201
    token = reg.cookies["access_token"]

    # 1. Verify token works before logout
    me_before = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_before.status_code == 200

    # 2. Call logout
    logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully."

    # 3. Verify the same token is now REJECTED
    me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401
    assert "revoked" in me_after.json().get("message", "").lower()


def test_token_expiration(client):
    """
    Expired tokens must be rejected with HTTP 401.
    """
    expired_token = create_access_token(
        {"sub": "user-expired", "email": "exp@test.com", "role": "user"},
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json().get("message", "").lower()

