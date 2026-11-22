"""
Entity extraction route.

Hardened with Phase 3 Public API Security Controls:
- Unauthenticated public access preserved.
- IP-based sliding window rate limiting before model inference.
- Sanitized generic error responses with zero internal detail leakage.
- Opaque request ID tracking and zero persistence/logging of patient form text.
"""

import logging
import uuid
from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from backend.app.schemas import (
    EntityItem,
    ExtractRequest,
    ExtractResponse,
    PDFExtractResponse,
    PDFMetadata,
)
from backend.app.services.pdf_service import extract_text_from_pdf
from backend.app.services.predictor import predictor_instance
from backend.app.services.rate_limiter import check_extraction_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Extraction"])


@router.post("/extract", response_model=ExtractResponse)
def extract_entities(request: Request, payload: ExtractRequest) -> ExtractResponse:
    """
    Extract healthcare entities (DATE, MEDICATION, CONDITION) from input text.
    Publicly accessible endpoint protected by IP rate limiting.
    """
    # 1. Enforce IP-based rate limiting before expensive ML inference
    check_extraction_rate_limit(request)

    # 2. Check model availability
    if not predictor_instance.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NER model is unavailable or still initializing.",
        )

    try:
        extracted = predictor_instance.extract_entities(payload.text)
        entities = [EntityItem(**e) for e in extracted]

        return ExtractResponse(
            text=payload.text,
            entities=entities,
            modelVersion=predictor_instance.model_version,
        )
    except Exception as exc:
        req_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
        # Server-side logging with request ID.
        # CRITICAL: Never log payload.text or extracted clinical information!
        logger.error(
            "Inference error during entity extraction [requestId=req-%s]: %s",
            req_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during entity extraction. Please try again later.",
        )


@router.post("/extract/pdf", response_model=PDFExtractResponse)
async def extract_entities_from_pdf(
    request: Request,
    file: UploadFile = File(..., description="Healthcare PDF document to process."),
) -> PDFExtractResponse:
    """
    Upload and extract healthcare entities from a PDF document.
    Publicly accessible endpoint protected by IP rate limiting and size constraints.
    Zero permanent retention of uploaded binary files.
    """
    # 1. Enforce IP rate limiting before PDF parsing and inference
    check_extraction_rate_limit(request)

    # 2. Validate file presence, extension, and content type
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PDF file was provided in the upload request.",
        )

    lower_name = file.filename.lower()
    if not lower_name.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF documents (.pdf) are supported.",
        )

    if file.content_type:
        allowed_mimes = {"application/pdf", "application/x-pdf", "binary/octet-stream"}
        if file.content_type.lower() not in allowed_mimes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MIME type '{file.content_type}'. Expected 'application/pdf'.",
            )

    # 3. Check model availability
    if not predictor_instance.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NER model is unavailable or still initializing.",
        )

    # 4. Read file content safely
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded PDF file stream.",
        )

    # 5. Extract text and metadata using PyMuPDF service
    text, meta = extract_text_from_pdf(content, file.filename)

    # 6. Pass extracted text to existing BiLSTM-CRF inference pipeline
    try:
        extracted = predictor_instance.extract_entities(text)
        entities = [EntityItem(**e) for e in extracted]

        return PDFExtractResponse(
            text=text,
            entities=entities,
            modelVersion=predictor_instance.model_version,
            metadata=PDFMetadata(**meta),
        )
    except HTTPException:
        raise
    except Exception as exc:
        req_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
        logger.error(
            "Inference error during PDF entity extraction [requestId=req-%s]: %s",
            req_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during entity extraction. Please try again later.",
        )
