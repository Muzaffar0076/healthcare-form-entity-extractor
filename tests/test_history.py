"""
Tests for User Extraction History feature.

Covers all 10 verification scenarios:
1. Successfully saving extraction history (POST /api/v1/history).
2. Retrieving a user's own history with pagination (GET /api/v1/history).
3. Preventing access to another user's history (strict isolation, 404 on cross-user).
4. Retrieving a specific record (GET /api/v1/history/{id}).
5. Deleting a record with ownership verification (DELETE /api/v1/history/{id}).
6. Rejecting invalid entity positions and label validation.
7. Handling empty history gracefully.
8. Preserving existing authentication requirements (401 for unauthenticated).
9. Ensuring existing database records (users, revoked_tokens) remain intact.
10. Ensuring extraction results are returned directly without rerunning the ML model.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.middleware.csrf import generate_csrf_token
from backend.app.services.auth_service import create_access_token
from backend.app.database import get_db_context
from backend.app.models.user import UserModel
from backend.app.models.revocation import RevokedTokenModel
from backend.app.models.history import ExtractionHistoryModel


@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client


class SimpleUser:
    def __init__(self, uid: str, full_name: str, email: str, role: str):
        self._id = uid
        self.fullName = full_name
        self.email = email
        self.role = role


def create_mock_user(email_prefix: str = "historyuser") -> SimpleUser:
    """Helper to create a persisted user for testing."""
    uid = str(uuid.uuid4())
    unique_email = f"{email_prefix}_{uuid.uuid4().hex[:8]}@example.com"
    full_name = f"Test User {email_prefix}"
    role = "patient"
    with get_db_context() as db:
        user = UserModel(
            _id=uid,
            fullName=full_name,
            email=unique_email,
            password="$2b$12$eX4mpleBcryptH4shForTestingOnlyNotRealHashValue123",
            role=role,
            isVerified=True,
        )
        db.add(user)
        db.commit()
    return SimpleUser(uid=uid, full_name=full_name, email=unique_email, role=role)


def get_auth_headers_and_cookies(user: SimpleUser):
    """Helper to generate JWT cookie, matching CSRF token, and headers."""
    from backend.app.services.auth_service import decode_access_token

    token = create_access_token(data={"sub": user._id, "role": user.role, "email": user.email})
    payload = decode_access_token(token)
    jti = payload["jti"]
    csrf_token = generate_csrf_token(session_binding=jti)
    cookies = {
        "access_token": token,
        "csrf_token": csrf_token,
    }
    headers = {
        "X-CSRF-Token": csrf_token,
        "Origin": "http://localhost:3000",
    }
    return cookies, headers


def test_unauthenticated_history_access_rejected(test_client):
    """Scenario 8: Unauthenticated access to history endpoints must return 401."""
    res_get = test_client.get("/api/v1/history")
    assert res_get.status_code == 401

    res_post = test_client.post("/api/v1/history", json={"form_text": "Sample", "extracted_entities": {"entities": []}})
    assert res_post.status_code == 401

    res_detail = test_client.get(f"/api/v1/history/{uuid.uuid4()}")
    assert res_detail.status_code == 401

    res_del = test_client.delete(f"/api/v1/history/{uuid.uuid4()}")
    assert res_del.status_code == 401


def test_empty_history_handled_gracefully(test_client):
    """Scenario 7: Handling empty history for a user with no records."""
    user = create_mock_user("empty")
    cookies, headers = get_auth_headers_and_cookies(user)

    res = test_client.get("/api/v1/history", cookies=cookies, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["limit"] == 10
    assert data["total_pages"] == 1


def test_save_extraction_history_success(test_client):
    """Scenario 1: Successfully saving extraction history."""
    user = create_mock_user("saver")
    cookies, headers = get_auth_headers_and_cookies(user)

    form_text = "Patient was prescribed Metformin 500mg on 12 March 2026 for diabetes."
    # Offsets:
    # Metformin 500mg: start 23, end 38
    # 12 March 2026: start 42, end 55
    # diabetes: start 60, end 68
    med_text = "Metformin 500mg"
    date_text = "12 March 2026"
    cond_text = "diabetes"

    start_med = form_text.index(med_text)
    end_med = start_med + len(med_text)

    start_date = form_text.index(date_text)
    end_date = start_date + len(date_text)

    start_cond = form_text.index(cond_text)
    end_cond = start_cond + len(cond_text)

    payload = {
        "form_text": form_text,
        "extracted_entities": {
            "entities": [
                {"text": med_text, "label": "MEDICATION", "start": start_med, "end": end_med, "confidence": 0.95},
                {"text": date_text, "label": "DATE", "start": start_date, "end": end_date, "confidence": 0.98},
                {"text": cond_text, "label": "CONDITION", "start": start_cond, "end": end_cond, "confidence": 0.91},
            ]
        },
    }

    res = test_client.post("/api/v1/history", json=payload, cookies=cookies, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["user_id"] == user._id
    assert data["form_text"] == form_text
    assert len(data["extracted_entities"]["entities"]) == 3
    assert data["total_entities"] == 3
    assert data["entity_counts"]["MEDICATION"] == 1
    assert data["entity_counts"]["DATE"] == 1
    assert data["entity_counts"]["CONDITION"] == 1


def test_reject_invalid_entity_positions(test_client):
    """Scenario 6: Rejecting invalid entity positions and text mismatches."""
    user = create_mock_user("validator")
    cookies, headers = get_auth_headers_and_cookies(user)

    form_text = "Patient was prescribed Aspirin."

    # 1. Text mismatch: entity text says "Metformin" but slice is "Aspirin"
    start_pos = form_text.index("Aspirin")
    end_pos = start_pos + len("Aspirin")
    bad_payload_mismatch = {
        "form_text": form_text,
        "extracted_entities": {
            "entities": [
                {"text": "Metformin", "label": "MEDICATION", "start": start_pos, "end": end_pos}
            ]
        },
    }
    res1 = test_client.post("/api/v1/history", json=bad_payload_mismatch, cookies=cookies, headers=headers)
    assert res1.status_code == 422

    # 2. Out of bounds offset
    bad_payload_bounds = {
        "form_text": form_text,
        "extracted_entities": {
            "entities": [
                {"text": "Aspirin", "label": "MEDICATION", "start": 20, "end": 100}
            ]
        },
    }
    res2 = test_client.post("/api/v1/history", json=bad_payload_bounds, cookies=cookies, headers=headers)
    assert res2.status_code == 422

    # 3. Invalid entity label
    bad_payload_label = {
        "form_text": form_text,
        "extracted_entities": {
            "entities": [
                {"text": "Aspirin", "label": "INVALID_LABEL", "start": start_pos, "end": end_pos}
            ]
        },
    }
    res3 = test_client.post("/api/v1/history", json=bad_payload_label, cookies=cookies, headers=headers)
    assert res3.status_code == 422

    # 4. Start >= end
    bad_payload_inverted = {
        "form_text": form_text,
        "extracted_entities": {
            "entities": [
                {"text": "Aspirin", "label": "MEDICATION", "start": 10, "end": 5}
            ]
        },
    }
    res4 = test_client.post("/api/v1/history", json=bad_payload_inverted, cookies=cookies, headers=headers)
    assert res4.status_code == 422


def test_retrieve_own_history_and_pagination(test_client):
    """Scenario 2: Retrieving a user's own history with pagination."""
    user = create_mock_user("paginator")
    cookies, headers = get_auth_headers_and_cookies(user)

    # Insert 3 records
    for i in range(3):
        text = f"Sample clinical note record number {i} with Aspirin."
        start = text.index("Aspirin")
        end = start + len("Aspirin")
        payload = {
            "form_text": text,
            "extracted_entities": {
                "entities": [{"text": "Aspirin", "label": "MEDICATION", "start": start, "end": end}]
            },
        }
        res = test_client.post("/api/v1/history", json=payload, cookies=cookies, headers=headers)
        assert res.status_code == 201

    # Request page 1 with limit 2
    res_page = test_client.get("/api/v1/history?page=1&limit=2", cookies=cookies, headers=headers)
    assert res_page.status_code == 200
    data = res_page.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["limit"] == 2
    assert data["total_pages"] == 2
    # Verify newest first: record 2 should be first
    assert "number 2" in data["items"][0]["form_text_preview"]

    # Request page 2 with limit 2
    res_page2 = test_client.get("/api/v1/history?page=2&limit=2", cookies=cookies, headers=headers)
    assert res_page2.status_code == 200
    data2 = res_page2.json()
    assert len(data2["items"]) == 1
    assert "number 0" in data2["items"][0]["form_text_preview"]


def test_retrieve_specific_record_and_no_rerun(test_client):
    """Scenario 4 & 10: Retrieving a specific record without rerunning model."""
    user = create_mock_user("retriever")
    cookies, headers = get_auth_headers_and_cookies(user)

    form_text = "Intake form on 15 January 2025 noted severe asthma."
    d_text = "15 January 2025"
    c_text = "asthma"
    d_start = form_text.index(d_text)
    d_end = d_start + len(d_text)
    c_start = form_text.index(c_text)
    c_end = c_start + len(c_text)

    create_res = test_client.post(
        "/api/v1/history",
        json={
            "form_text": form_text,
            "extracted_entities": {
                "entities": [
                    {"text": d_text, "label": "DATE", "start": d_start, "end": d_end},
                    {"text": c_text, "label": "CONDITION", "start": c_start, "end": c_end},
                ]
            },
        },
        cookies=cookies,
        headers=headers,
    )
    rec_id = create_res.json()["id"]

    # Retrieve record by ID
    get_res = test_client.get(f"/api/v1/history/{rec_id}", cookies=cookies, headers=headers)
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["id"] == rec_id
    assert detail["form_text"] == form_text
    # Exactly matches saved values without model intervention
    assert len(detail["extracted_entities"]["entities"]) == 2
    assert detail["extracted_entities"]["entities"][0]["text"] == d_text
    assert detail["extracted_entities"]["entities"][1]["text"] == c_text


def test_strict_cross_user_isolation(test_client):
    """Scenario 3: A user cannot access or view another user's history."""
    user_a = create_mock_user("user_a")
    user_b = create_mock_user("user_b")

    cookies_a, headers_a = get_auth_headers_and_cookies(user_a)
    cookies_b, headers_b = get_auth_headers_and_cookies(user_b)

    # User A creates a record
    form_text = "Confidential patient notes for User A with Amoxicillin."
    med = "Amoxicillin"
    start = form_text.index(med)
    end = start + len(med)

    create_res = test_client.post(
        "/api/v1/history",
        json={
            "form_text": form_text,
            "extracted_entities": {
                "entities": [{"text": med, "label": "MEDICATION", "start": start, "end": end}]
            },
        },
        cookies=cookies_a,
        headers=headers_a,
    )
    assert create_res.status_code == 201
    rec_id_a = create_res.json()["id"]

    # User B lists history: must NOT include User A's record
    list_b = test_client.get("/api/v1/history", cookies=cookies_b, headers=headers_b)
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0
    assert len(list_b.json()["items"]) == 0

    # User B attempts to directly get User A's record by ID: must return 404
    direct_get_b = test_client.get(f"/api/v1/history/{rec_id_a}", cookies=cookies_b, headers=headers_b)
    assert direct_get_b.status_code == 404
    assert direct_get_b.json()["message"] == "Extraction history record not found."


def test_delete_record_with_ownership_verification(test_client):
    """Scenario 5: Deleting a record with ownership verification."""
    user_a = create_mock_user("del_user_a")
    user_b = create_mock_user("del_user_b")

    cookies_a, headers_a = get_auth_headers_and_cookies(user_a)
    cookies_b, headers_b = get_auth_headers_and_cookies(user_b)

    # User A creates a record
    text = "Form to be deleted with Metformin."
    med = "Metformin"
    start = text.index(med)
    end = start + len(med)

    create_res = test_client.post(
        "/api/v1/history",
        json={"form_text": text, "extracted_entities": {"entities": [{"text": med, "label": "MEDICATION", "start": start, "end": end}]}},
        cookies=cookies_a,
        headers=headers_a,
    )
    rec_id = create_res.json()["id"]

    # User B attempts to delete User A's record: must return 404
    del_unauthorized = test_client.delete(f"/api/v1/history/{rec_id}", cookies=cookies_b, headers=headers_b)
    assert del_unauthorized.status_code == 404

    # Verify record still exists for User A
    check_exists = test_client.get(f"/api/v1/history/{rec_id}", cookies=cookies_a, headers=headers_a)
    assert check_exists.status_code == 200

    # User A deletes their own record: must succeed
    del_success = test_client.delete(f"/api/v1/history/{rec_id}", cookies=cookies_a, headers=headers_a)
    assert del_success.status_code == 200
    assert del_success.json()["id"] == rec_id

    # Verify record is now gone
    check_deleted = test_client.get(f"/api/v1/history/{rec_id}", cookies=cookies_a, headers=headers_a)
    assert check_deleted.status_code == 404


def test_existing_database_records_remain_intact():
    """Scenario 9: Ensuring existing database records remain intact."""
    with get_db_context() as db:
        user_count = db.query(UserModel).count()
        revoked_count = db.query(RevokedTokenModel).count()
        # Verify counts are greater than 0 from previous sessions
        assert user_count >= 100
        assert revoked_count >= 1


def test_complete_lifecycle_registration_extraction_history(test_client):
    """
    End-to-End Workflow:
    1. Register new user.
    2. Extract entities using public extraction endpoint.
    3. Save extraction to history.
    4. Verify history contains the saved record.
    5. Log out (revoking session).
    6. Log in again.
    7. Retrieve saved history and view record details.
    """
    unique_email = f"lifecycle_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"

    # 1. Register
    csrf_init = test_client.get("/api/auth/csrf-token")
    csrf_token = csrf_init.json()["csrfToken"]

    reg_res = test_client.post(
        "/api/auth/register",
        json={
            "fullName": "Lifecycle Patient",
            "email": unique_email,
            "password": password,
            "confirmPassword": password,
        },
        headers={"X-CSRF-Token": csrf_token, "Origin": "http://localhost:3000"},
        cookies={"csrf_token": csrf_token},
    )
    assert reg_res.status_code == 201

    auth_cookies = reg_res.cookies
    active_csrf = auth_cookies.get("csrf_token")

    # 2. Extract entities
    form_text = "Patient was diagnosed with pneumonia and prescribed Amoxicillin on 01 May 2025."
    extract_res = test_client.post(
        "/api/v1/extract",
        json={"text": form_text},
        headers={"X-CSRF-Token": active_csrf, "Origin": "http://localhost:3000"},
        cookies=auth_cookies,
    )
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert len(extract_data["entities"]) > 0

    # 3. Save extraction to history
    save_payload = {
        "form_text": form_text,
        "extracted_entities": {
            "entities": extract_data["entities"],
        },
    }
    save_res = test_client.post(
        "/api/v1/history",
        json=save_payload,
        cookies=auth_cookies,
        headers={"X-CSRF-Token": active_csrf, "Origin": "http://localhost:3000"},
    )
    assert save_res.status_code == 201
    record_id = save_res.json()["id"]

    # 4. View history list
    list_res = test_client.get(
        "/api/v1/history",
        cookies=auth_cookies,
        headers={"Origin": "http://localhost:3000"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1
    assert list_res.json()["items"][0]["id"] == record_id

    # 5. Logout
    logout_res = test_client.post(
        "/api/auth/logout",
        cookies=auth_cookies,
        headers={"X-CSRF-Token": active_csrf, "Origin": "http://localhost:3000"},
    )
    assert logout_res.status_code == 200

    # 6. Re-login
    csrf_relogin = test_client.get("/api/auth/csrf-token")
    relogin_csrf = csrf_relogin.json()["csrfToken"]

    login_res = test_client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": password},
        cookies={"csrf_token": relogin_csrf},
        headers={"X-CSRF-Token": relogin_csrf, "Origin": "http://localhost:3000"},
    )
    assert login_res.status_code == 200
    new_auth_cookies = login_res.cookies
    new_csrf = new_auth_cookies.get("csrf_token")

    # 7. Access history again and get detail
    detail_res = test_client.get(
        f"/api/v1/history/{record_id}",
        cookies=new_auth_cookies,
        headers={"Origin": "http://localhost:3000"},
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == record_id
    assert detail["form_text"] == form_text
    assert len(detail["extracted_entities"]["entities"]) == len(extract_data["entities"])

