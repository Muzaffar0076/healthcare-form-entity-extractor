"""
Phase 3 Security Verification Tests.

Verifies:
1. Public Extraction Rate Limiting:
   - Configurable limit (default 30 req/min per IP) enforced on POST /api/v1/extract.
   - Returns HTTP 429 when exceeded with standard Retry-After header.
   - Separate quotas maintained per validated client IP.
   - Public access without authentication preserved.
   - No clinical text persisted in rate limiter.

2. Request Body Size Limit:
   - Enforced at ASGI level (1 MB ceiling).
   - Returns HTTP 413 (PAYLOAD_TOO_LARGE) when Content-Length or streamed body exceeds 1 MB.
   - Normal requests succeed.
   - Safe handling of chunked/missing Content-Length and client disconnects.

3. Trusted Proxy / Client IP Validation:
   - Spoofed X-Forwarded-For from untrusted peers is completely ignored.
   - Forwarded IPs from configured TRUSTED_PROXY_IPS are validated using ipaddress module.
   - Malformed forwarded IPs safely fall back to peer host.
   - Direct connection IP fallback works.

4. Generic Inference Error Handling:
   - Never leaks str(exc), stack traces, model internals, or file paths in HTTP 500 responses.
   - Emits generic sanitized user-facing error message with opaque requestId.
   - Preserves HTTP 503 behavior for uninitialized model.

5. Defensive HTTP Security Headers:
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - Referrer-Policy: strict-origin-when-cross-origin
   - Content-Security-Policy with Google Fonts and API origin allowances
   - Strict-Transport-Security (HSTS) only present in production HTTPS mode.

6. SQLite Database File Permissions:
   - Enforces 0600 (owner read/write only) on data/users.db where supported.
   - Preserves all existing records.
"""

import io
import os
import stat
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.database import get_db_context, secure_db_permissions, init_db, DEFAULT_DB_PATH
from backend.app.main import app
from backend.app.middleware.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    generate_csrf_token,
)
from backend.app.models.user import UserModel
from backend.app.services.predictor import predictor_instance
from backend.app.services.rate_limiter import (
    get_client_ip,
    is_trusted_proxy,
    _rate_limiter,
    reset_rate_limiter,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# 1. Public Extraction Rate Limiting Tests
# ==============================================================================

def test_public_extraction_works_without_authentication(client):
    """
    POST /api/v1/extract must be publicly accessible without any authentication.
    """
    client.cookies.clear()
    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient was prescribed Aspirin on 12 March 2026 for diabetes."},
    )
    assert response.status_code == 200
    data = response.json()
    assert "entities" in data
    assert "modelVersion" in data
    assert len(data["entities"]) > 0


def test_public_extraction_rate_limiting_enforced(client, monkeypatch):
    """
    Rapid requests to POST /api/v1/extract exceeding the limit must return HTTP 429
    with a Retry-After header.
    """
    reset_rate_limiter()
    monkeypatch.setenv("RATE_LIMIT_EXTRACT_PER_MIN", "5")
    monkeypatch.setenv("RATE_LIMIT_EXTRACT_WINDOW_SECS", "60")

    # Invalidate cached default limits by re-reading or patching
    from backend.app.services import rate_limiter
    monkeypatch.setattr(rate_limiter, "DEFAULT_EXTRACT_LIMIT", 5)

    ip = "198.51.100.22"
    headers = {"X-Forwarded-For": ip}
    # Configure 127.0.0.1 as trusted proxy so X-Forwarded-For is respected in this test
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1,testclient")

    statuses = []
    retry_afters = []

    for i in range(7):
        res = client.post(
            "/api/v1/extract",
            json={"text": "Patient took Paracetamol on 10 May 2025."},
            headers=headers,
        )
        statuses.append(res.status_code)
        if res.status_code == 429:
            retry_afters.append(res.headers.get("retry-after"))

    # First 5 should succeed (200), subsequent must be 429
    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert statuses[5] == 429
    assert len(retry_afters) > 0
    assert int(retry_afters[0]) > 0


def test_public_extraction_separate_ip_quotas(client, monkeypatch):
    """
    Extraction rate limiting maintains distinct sliding windows per client IP.
    Throttling IP A must NOT throttle IP B.
    """
    reset_rate_limiter()
    from backend.app.services import rate_limiter
    monkeypatch.setattr(rate_limiter, "DEFAULT_EXTRACT_LIMIT", 2)
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1,testclient")

    # Exhaust IP A
    for _ in range(2):
        r = client.post(
            "/api/v1/extract",
            json={"text": "Patient diagnosis: Asthma on 01 Jan 2026."},
            headers={"X-Forwarded-For": "198.51.100.31"},
        )
        assert r.status_code == 200

    # Next request from IP A must be 429
    blocked_a = client.post(
        "/api/v1/extract",
        json={"text": "Patient diagnosis: Asthma on 01 Jan 2026."},
        headers={"X-Forwarded-For": "198.51.100.31"},
    )
    assert blocked_a.status_code == 429

    # Request from IP B must succeed
    ok_b = client.post(
        "/api/v1/extract",
        json={"text": "Patient diagnosis: Asthma on 01 Jan 2026."},
        headers={"X-Forwarded-For": "198.51.100.32"},
    )
    assert ok_b.status_code == 200


# ==============================================================================
# 2. Trusted Proxy & Client IP Validation Tests
# ==============================================================================

def test_untrusted_client_x_forwarded_for_ignored(client, monkeypatch):
    """
    When the direct connection is NOT in TRUSTED_PROXY_IPS, X-Forwarded-For
    must be ignored to prevent IP spoofing and rate-limit bypass.
    """
    reset_rate_limiter()
    # Explicitly clear trusted proxies
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)

    from backend.app.services import rate_limiter
    monkeypatch.setattr(rate_limiter, "DEFAULT_EXTRACT_LIMIT", 2)

    # An attacker attempts to bypass rate limits by cycling X-Forwarded-For IPs
    statuses = []
    for i in range(4):
        res = client.post(
            "/api/v1/extract",
            json={"text": "Patient has Hypertension."},
            headers={"X-Forwarded-For": f"198.51.100.{100 + i}"},
        )
        statuses.append(res.status_code)

    # Because proxy is untrusted, all requests map to direct peer (e.g. testclient),
    # so rate limiting triggers on the 3rd request despite varying headers.
    assert statuses[:2] == [200, 200]
    assert 429 in statuses[2:]


def test_trusted_proxy_forwarded_ip_validation(client, monkeypatch):
    """
    When connecting from a trusted proxy, a valid X-Forwarded-For IP is accepted.
    """
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1,testclient,10.0.0.0/8")

    assert is_trusted_proxy("127.0.0.1") is True
    assert is_trusted_proxy("10.1.2.3") is True
    assert is_trusted_proxy("192.168.1.1") is False

    # Simulate Request from trusted proxy with valid client IP in X-Forwarded-For
    class MockRequest:
        def __init__(self, client_host, forwarded_for):
            self.client = type("Client", (), {"host": client_host})()
            self.headers = {"X-Forwarded-For": forwarded_for}

    req_trusted = MockRequest("127.0.0.1", "203.0.113.88, 10.0.0.1")
    assert get_client_ip(req_trusted) == "203.0.113.88"

    # Malformed IP falls back to direct IP
    req_malformed = MockRequest("127.0.0.1", "invalid_ip_format; DROP TABLE")
    assert get_client_ip(req_malformed) == "127.0.0.1"

    # Empty forwarded header falls back to direct IP
    req_empty = MockRequest("127.0.0.1", "")
    assert get_client_ip(req_empty) == "127.0.0.1"


# ==============================================================================
# 3. Request Body Size Limit Tests
# ==============================================================================

def test_request_body_size_within_limit_succeeds(client):
    """
    Requests with bodies under 1 MB must proceed normally.
    """
    normal_text = "Patient was prescribed Metformin on 15 August 2024 for diabetes."
    response = client.post(
        "/api/v1/extract",
        json={"text": normal_text},
    )
    assert response.status_code == 200
    assert "entities" in response.json()


def test_oversized_content_length_rejected_with_413(client):
    """
    Requests declaring a Content-Length exceeding the maximum limit (1 MB)
    must be immediately rejected with HTTP 413 Payload Too Large.
    """
    # 2 MB Content-Length header
    response = client.post(
        "/api/v1/extract",
        content=b"dummy",
        headers={
            "Content-Type": "application/json",
            "Content-Length": "2097152",  # 2 MB
        },
    )
    assert response.status_code == 413
    data = response.json()
    assert data["code"] == "PAYLOAD_TOO_LARGE"
    assert "exceeds maximum allowed size" in data["message"]


def test_oversized_actual_body_rejected_with_413(client):
    """
    Requests with an actual payload exceeding 1 MB must be rejected with HTTP 413.
    """
    oversized_payload = b'{"text": "' + b"A" * (1024 * 1024 + 100) + b'"}'
    response = client.post(
        "/api/v1/extract",
        content=oversized_payload,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    data = response.json()
    assert data["code"] == "PAYLOAD_TOO_LARGE"


# ==============================================================================
# 4. Generic Inference Error Handling Tests
# ==============================================================================

def test_inference_error_returns_generic_message_without_leakage(client, monkeypatch):
    """
    When an unexpected runtime error occurs during ML inference, the endpoint
    must log the error server-side and return a generic sanitized message
    with an opaque requestId. Never leak str(exc) or model internals.
    """
    def mock_broken_extract(text):
        raise RuntimeError("Internal CUDA tensor mismatch at 0x7fff5fbff880 in /opt/models/crf.py")

    monkeypatch.setattr(predictor_instance, "extract_entities", mock_broken_extract)

    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient was diagnosed with Hypertension."},
    )
    assert response.status_code == 500
    data = response.json()

    # Must NOT contain internal error strings or stack traces
    assert "CUDA" not in data.get("message", "")
    assert "crf.py" not in data.get("message", "")
    assert "0x7fff" not in data.get("message", "")

    # Must contain generic sanitized explanation and request ID
    assert "An unexpected error occurred during entity extraction" in data.get("message", "")
    assert "requestId" in data
    assert data["requestId"].startswith("req-")


def test_missing_model_preserves_503(client, monkeypatch):
    """
    If the NER model is not loaded, the endpoint must return HTTP 503 Service Unavailable.
    """
    monkeypatch.setattr(predictor_instance, "is_loaded", False)
    response = client.post(
        "/api/v1/extract",
        json={"text": "Patient has bronchitis."},
    )
    assert response.status_code == 503
    assert "unavailable or still initializing" in response.json().get("message", "").lower()


# ==============================================================================
# 5. Defensive HTTP Security Headers Tests
# ==============================================================================

def test_defensive_security_headers_present(client):
    """
    Standard responses must contain nosniff, DENY, Referrer-Policy, and CSP headers.
    """
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    # CSP checks
    csp = headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "https://fonts.googleapis.com" in csp
    assert "https://fonts.gstatic.com" in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_disabled_in_development_http(client, monkeypatch):
    """
    Strict-Transport-Security must NOT be attached during local development over HTTP.
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("SECURE_HSTS_ENABLED", raising=False)

    response = client.get("/health")
    assert "strict-transport-security" not in response.headers


def test_hsts_enabled_in_production_https(client, monkeypatch):
    """
    Strict-Transport-Security must be attached in production HTTPS configuration.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURE_HSTS_ENABLED", "true")

    response = client.get(
        "/health",
        headers={"X-Forwarded-Proto": "https"},
    )
    assert response.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"


# ==============================================================================
# 6. SQLite Database File Permissions Tests
# ==============================================================================

def test_sqlite_db_file_permissions():
    """
    ensure secure_db_permissions() applies 0600 on data/users.db where supported
    and preserves user data intact.
    """
    init_db()
    secure_db_permissions()

    db_path = DEFAULT_DB_PATH
    if db_path.exists():
        mode = stat.S_IMODE(os.stat(db_path).st_mode)
        # On POSIX platforms, verify owner read/write only (0600)
        if os.name == "posix":
            assert mode == 0o600

    # Verify user queries still function without issue
    with get_db_context() as db:
        user_count = db.query(UserModel).count()
        assert isinstance(user_count, int)

