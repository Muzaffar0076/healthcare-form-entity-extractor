"""
Unit and integration tests for User Authentication & Registration module.

Tests:
- POST /api/auth/register (success, duplicate email, password mismatch, weak password)
- POST /api/auth/login (success, invalid credentials, non-existent user)
- GET  /api/auth/me (authenticated user profile, unauthorized, invalid token)
- POST /api/auth/logout (session termination)
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """
    TestClient context manager ensures FastAPI lifespan initializes database and model.
    """
    with TestClient(app) as test_client:
        yield test_client


def test_register_success(client):
    """
    Valid registration should return 201, JWT token, and sanitized user profile.
    """
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "fullName": "Test Doctor",
        "email": unique_email,
        "password": "ValidPassword123!",
        "confirmPassword": "ValidPassword123!",
        "phoneNumber": "+1-555-0123",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["message"] == "User registered successfully."
    assert "token" not in data
    assert "tokenType" not in data
    assert "access_token" in response.cookies

    user = data["user"]
    assert "_id" in user
    assert user["fullName"] == "Test Doctor"
    assert user["email"] == unique_email
    assert user["phoneNumber"] == "+1-555-0123"
    assert user["role"] == "user"
    assert user["isVerified"] is True
    assert "createdAt" in user
    assert "updatedAt" in user
    # Critical security check: password must NEVER be in response
    assert "password" not in user


def test_register_duplicate_email(client):
    """
    Registering with an already existing email must return 409 Conflict.
    """
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "fullName": "First User",
        "email": email,
        "password": "Password123!",
        "confirmPassword": "Password123!",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt registration with duplicate email
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert "already exists" in data.get("message", "")


def test_register_password_mismatch(client):
    """
    Registration with non-matching confirmPassword must return 422.
    """
    payload = {
        "fullName": "Mismatch User",
        "email": "mismatch@example.com",
        "password": "Password123!",
        "confirmPassword": "DifferentPassword456!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "Passwords do not match" in data.get("message", "")


def test_register_weak_password(client):
    """
    Password shorter than 8 chars or missing numbers must be rejected with 422.
    """
    payload = {
        "fullName": "Weak Password User",
        "email": "weak@example.com",
        "password": "short",
        "confirmPassword": "short",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_register_invalid_email(client):
    """
    Invalid email format must return 422.
    """
    payload = {
        "fullName": "Invalid Email",
        "email": "not-an-email",
        "password": "Password123!",
        "confirmPassword": "Password123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_login_success(client):
    """
    Registered user can log in with email and password to receive JWT token.
    """
    email = f"login_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    # 1. Register
    reg_res = client.post(
        "/api/auth/register",
        json={
            "fullName": "Login Tester",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )
    assert reg_res.status_code == 201

    # 2. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["message"] == "Login successful."
    assert "token" not in data
    assert "tokenType" not in data
    assert "access_token" in login_res.cookies
    assert data["user"]["email"] == email


def test_login_invalid_password(client):
    """
    Incorrect password must return 401 Unauthorized.
    """
    email = f"wrongpw_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    client.post(
        "/api/auth/register",
        json={
            "fullName": "Wrong PW Tester",
            "email": email,
            "password": password,
            "confirmPassword": password,
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid email address or password" in data.get("message", "")


def test_login_nonexistent_email(client):
    """
    Login with non-existent email must return 401 Unauthorized.
    """
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody_exists_here_xyz@example.com", "password": "Password123!"},
    )
    assert response.status_code == 401


def test_get_me_authenticated(client):
    """
    GET /api/auth/me with Bearer token must return current user's profile.
    """
    email = f"me_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "fullName": "Profile User",
            "email": email,
            "password": "Password123!",
            "confirmPassword": "Password123!",
            "phoneNumber": "+1-800-555-0100",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.cookies["access_token"]

    # Call /api/auth/me with Authorization header
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user = me_res.json()
    assert user["email"] == email
    assert user["fullName"] == "Profile User"
    assert user["phoneNumber"] == "+1-800-555-0100"
    assert "password" not in user


def test_get_me_unauthorized(client):
    """
    GET /api/auth/me without token must return 401.
    """
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client):
    """
    GET /api/auth/me with garbage token must return 401.
    """
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token-string"},
    )
    assert response.status_code == 401


def test_logout_success(client):
    """
    POST /api/auth/logout with Bearer token must return 200 OK.
    """
    email = f"logout_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "fullName": "Logout User",
            "email": email,
            "password": "Password123!",
            "confirmPassword": "Password123!",
        },
    )
    token = reg_res.cookies["access_token"]

    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully."

