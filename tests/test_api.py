"""
Unit and integration tests for FastAPI backend endpoints.

Validates TEST-001 through TEST-005 and PRD Section 12 (API Testing).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """
    TestClient context manager ensures FastAPI lifespan loads the model.
    """
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    """
    GET /health should return 200 with healthy status and model version.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["modelLoaded"] is True
    assert "modelVersion" in data


def test_api_v1_health_check(client):
    """
    GET /api/v1/health should match /health.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_extract_valid_text(client):
    """
    TEST-001: Valid extraction should return 200, original text, and entity list.
    """
    text = "The patient was prescribed Aspirin on 12 March 2026 for diabetes."
    response = client.post("/api/v1/extract", json={"text": text})
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == text
    assert "entities" in data
    assert isinstance(data["entities"], list)
    assert len(data["entities"]) > 0

    # Verify entity schema
    first_ent = data["entities"][0]
    assert "text" in first_ent
    assert "label" in first_ent
    assert "start" in first_ent
    assert "end" in first_ent
    assert "confidence" in first_ent
    assert first_ent["label"] in {"DATE", "MEDICATION", "CONDITION"}


def test_extract_empty_text(client):
    """
    TEST-002: Empty text should return 422 with structured validation error.
    """
    response = client.post("/api/v1/extract", json={"text": "   "})
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "Text input cannot be empty" in data["message"]
    assert "requestId" in data


def test_extract_wrong_type(client):
    """
    TEST-003: Wrong data type for text should return 422.
    """
    response = client.post("/api/v1/extract", json={"text": 12345})
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_extract_no_entities(client):
    """
    TEST-005: Text with no healthcare entities returns empty entity list.
    """
    response = client.post(
        "/api/v1/extract",
        json={"text": "Hello world, this is a general sentence without any medical mentions."},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["entities"], list)


def test_get_model_metadata(client):
    """
    GET /api/v1/model should return 200 with model architecture and metrics.
    """
    response = client.get("/api/v1/model")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "Healthcare Form Entity Extractor"
    assert data["architecture"] == "BiLSTM-CRF"
    assert "DATE" in data["entities"]


def test_get_model_card(client):
    """
    GET /api/v1/model-card should return 200 with model details and disclaimer.
    """
    response = client.get("/api/v1/model-card")
    assert response.status_code == 200
    data = response.json()
    assert "model_details" in data
    assert "intended_use" in data
    assert "disclaimer" in data
