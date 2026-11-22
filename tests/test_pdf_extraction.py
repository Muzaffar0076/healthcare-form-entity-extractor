"""
Tests for PDF Uploader and Text Extraction feature.

Validates:
1. Valid PDF upload and entity extraction (dates, medications, conditions).
2. Multi-page PDF text extraction and paragraph preservation.
3. Rejecting invalid file extensions (.txt, .docx).
4. Rejecting invalid MIME types.
5. Rejecting corrupted PDF files.
6. Rejecting empty PDF files (0 bytes).
7. Detecting scanned / textless PDFs and returning clear 422 OCR error.
8. Rejecting encrypted/password-protected PDFs.
9. Enforcing maximum PDF file size limits (HTTP 413).
10. Preservation of existing text extraction endpoint (POST /api/v1/extract).
11. Integration with User Extraction History (saving PDF-derived extractions).
"""

import io
import uuid
import pytest
from fastapi.testclient import TestClient
import pymupdf

from backend.app.main import app
from backend.app.middleware.csrf import generate_csrf_token
from backend.app.services.auth_service import create_access_token, decode_access_token
from backend.app.database import get_db_context
from backend.app.models.user import UserModel


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_sample_pdf(pages_text: list[str]) -> bytes:
    """Helper to generate an in-memory PDF with specified text per page."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 50), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_valid_single_page_pdf_extraction(client):
    """Scenario 1: Upload a valid single-page healthcare PDF and extract entities."""
    sample_text = "Patient was prescribed Metformin 500mg on 12 March 2026 for diabetes."
    pdf_bytes = create_sample_pdf([sample_text])

    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("clinical_form.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert sample_text in data["text"]
    assert len(data["entities"]) >= 3
    assert data["modelVersion"] == "bilstm-crf-v1"
    assert data["metadata"]["fileName"] == "clinical_form.pdf"
    assert data["metadata"]["pageCount"] == 1
    assert data["metadata"]["fileSizeBytes"] == len(pdf_bytes)

    # Check extracted entity categories
    labels = {e["label"] for e in data["entities"]}
    assert "MEDICATION" in labels or "DATE" in labels or "CONDITION" in labels


def test_multi_page_pdf_extraction(client):
    """Scenario 2: Multi-page PDF text extraction and entity recognition."""
    page_1 = "Initial consultation on 15 January 2025 noted acute bronchitis."
    page_2 = "Discharge notes: Prescribed Amoxicillin 500mg twice daily."
    pdf_bytes = create_sample_pdf([page_1, page_2])

    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("medical_records_multipage.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "15 January 2025" in data["text"]
    assert "Amoxicillin" in data["text"]
    assert data["metadata"]["pageCount"] == 2
    assert len(data["entities"]) > 0


def test_reject_invalid_file_extension(client):
    """Scenario 3: Reject non-PDF file extensions."""
    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("notes.txt", io.BytesIO(b"Sample plain text"), "text/plain")},
    )
    assert response.status_code == 400
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "Only PDF documents (.pdf) are supported" in msg


def test_reject_invalid_mime_type(client):
    """Scenario 4: Reject non-PDF MIME types even if named .pdf."""
    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("fake.pdf", io.BytesIO(b"some fake content"), "image/png")},
    )
    assert response.status_code == 400
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "Invalid MIME type" in msg


def test_reject_corrupted_pdf(client):
    """Scenario 5: Reject malformed / corrupted PDF streams."""
    corrupted_data = b"%PDF-1.4\n%invalid_corrupted_stream_content_xyz_garbage_data"
    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("corrupted.pdf", io.BytesIO(corrupted_data), "application/pdf")},
    )
    assert response.status_code == 422
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "corrupted or could not be parsed" in msg


def test_reject_empty_file(client):
    """Scenario 6: Reject zero-byte uploaded files."""
    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "empty" in msg


def test_detect_textless_scanned_pdf(client):
    """Scenario 7: Detect scanned/image-only PDFs with no extractable text and return 422 with OCR guidance."""
    doc = pymupdf.open()
    doc.new_page()  # Blank page with no text
    textless_bytes = doc.tobytes()
    doc.close()

    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("scanned_blank.pdf", io.BytesIO(textless_bytes), "application/pdf")},
    )
    assert response.status_code == 422
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "no extractable text" in msg
    assert "Optical Character Recognition (OCR)" in msg


def test_reject_encrypted_pdf(client):
    """Scenario 8: Reject password-protected / encrypted PDFs."""
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Confidential records")
    encrypted_bytes = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret123")
    doc.close()

    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("encrypted.pdf", io.BytesIO(encrypted_bytes), "application/pdf")},
    )
    assert response.status_code == 422
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "password-protected or encrypted" in msg


def test_oversized_pdf_rejected(client, monkeypatch):
    """Scenario 9: Reject PDFs exceeding maximum allowed byte limit."""
    import backend.app.services.pdf_service as pdf_mod
    monkeypatch.setattr(pdf_mod, "MAX_PDF_FILE_BYTES", 300)  # Low limit for testing
    pdf_bytes = create_sample_pdf(["Aspirin 100mg on 12 March 2026."])
    assert len(pdf_bytes) > 300

    response = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("large.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 413
    msg = response.json().get("message") or response.json().get("detail", "")
    assert "exceeds the maximum allowed size" in msg


def test_existing_text_extraction_endpoint_preserved(client):
    """Scenario 10: Existing text extraction endpoint POST /api/v1/extract continues to function cleanly."""
    payload = {"text": "Prescribed Aspirin on 12 March 2026 for diabetes."}
    response = client.post("/api/v1/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == payload["text"]
    assert len(data["entities"]) > 0


def test_pdf_extraction_integrates_with_user_history(client):
    """Scenario 11: PDF-derived extraction results can be persisted to user history with consent."""
    # 1. Extract from PDF
    clinical_text = "Patient was diagnosed with asthma and prescribed Albuterol on 05 April 2025."
    pdf_bytes = create_sample_pdf([clinical_text])

    extract_res = client.post(
        "/api/v1/extract/pdf",
        files={"file": ("consultation.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert len(extract_data["entities"]) > 0

    # 2. Authenticate mock user
    unique_email = f"pdf_history_{uuid.uuid4().hex[:8]}@example.com"
    with get_db_context() as db:
        user = UserModel(
            _id=str(uuid.uuid4()),
            fullName="PDF Patient",
            email=unique_email,
            password="$2b$12$eX4mpleBcryptH4shForTestingOnlyNotRealHashValue123",
            role="patient",
            isVerified=True,
        )
        db.add(user)
        db.commit()
        uid = user._id

    token = create_access_token(data={"sub": uid, "role": "patient", "email": unique_email})
    jti = decode_access_token(token)["jti"]
    csrf = generate_csrf_token(session_binding=jti)

    # 3. Save to history
    save_payload = {
        "form_text": extract_data["text"],
        "extracted_entities": {
            "entities": extract_data["entities"],
        },
    }
    save_res = client.post(
        "/api/v1/history",
        json=save_payload,
        cookies={"access_token": token, "csrf_token": csrf},
        headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:3000"},
    )
    assert save_res.status_code == 201
    record_id = save_res.json()["id"]

    # 4. Retrieve saved history
    get_res = client.get(
        f"/api/v1/history/{record_id}",
        cookies={"access_token": token, "csrf_token": csrf},
        headers={"Origin": "http://localhost:3000"},
    )
    assert get_res.status_code == 200
    saved_record = get_res.json()
    assert saved_record["id"] == record_id
    assert clinical_text in saved_record["form_text"]
    assert len(saved_record["extracted_entities"]["entities"]) == len(extract_data["entities"])
