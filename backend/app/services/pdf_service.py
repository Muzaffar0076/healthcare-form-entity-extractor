"""
PDF Processing Service for Healthcare Form Entity Extractor.

Extracts text from uploaded healthcare PDF documents using PyMuPDF (fitz).
Implements security controls:
- File signature / magic bytes validation (%PDF-).
- Memory-safe stream processing with zero permanent file retention.
- Rejection of corrupted or encrypted/password-protected PDFs.
- Scanned / image-only PDF detection with clear guidance on OCR.
- Extracted text paragraph preservation.
"""

import io
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
import pymupdf

logger = logging.getLogger(__name__)

# Configurable maximum PDF file size in bytes (default: 10 MB)
DEFAULT_MAX_PDF_FILE_BYTES = 10 * 1024 * 1024
MAX_PDF_FILE_BYTES = int(os.getenv("MAX_PDF_FILE_BYTES", str(DEFAULT_MAX_PDF_FILE_BYTES)))


class PDFProcessingError(HTTPException):
    """Base exception for PDF processing errors."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


def validate_pdf_bytes(file_bytes: bytes, filename: str) -> None:
    """
    Validate that raw bytes represent a valid PDF file.
    1. Checks byte length against MAX_PDF_FILE_BYTES.
    2. Validates PDF magic header bytes (b"%PDF").
    """
    if not file_bytes or len(file_bytes) == 0:
        raise PDFProcessingError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF file is empty (0 bytes).",
        )

    if len(file_bytes) > MAX_PDF_FILE_BYTES:
        limit_mb = MAX_PDF_FILE_BYTES // (1024 * 1024)
        raise PDFProcessingError(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"The uploaded PDF file exceeds the maximum allowed size of {limit_mb} MB.",
        )

    # Magic bytes check: PDF specification requires files to begin with "%PDF-"
    # Allow small offset (up to 1024 bytes) for legacy/scanned header preambles
    header_chunk = file_bytes[:1024]
    if b"%PDF" not in header_chunk:
        raise PDFProcessingError(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file signature. The uploaded file is not a valid PDF document.",
        )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename to prevent directory traversal and header injection.
    """
    basename = Path(filename).name
    # Remove null bytes and path separators
    clean = basename.replace("\x00", "").replace("/", "").replace("\\", "").strip()
    return clean or "uploaded_document.pdf"


def ocr_fallback_extension_point(doc: pymupdf.Document) -> Optional[str]:
    """
    Extension point for Optical Character Recognition (OCR) on scanned PDFs.
    
    Currently, the application does not have an external OCR engine (like Tesseract)
    installed to avoid heavyweight system dependencies. This function serves as the
    architectural hook for future OCR pipeline integration.
    """
    # Architecture hook: If an OCR engine (e.g. pytesseract / easyocr) is configured,
    # image extraction and raster OCR would be executed here.
    return None


def extract_text_from_pdf(
    file_bytes: bytes,
    filename: str,
) -> tuple[str, dict]:
    """
    Extract readable text and document metadata from PDF bytes.

    Args:
        file_bytes: In-memory byte content of the PDF.
        filename: Original uploaded filename.

    Returns:
        tuple of (extracted_text, metadata_dict)

    Raises:
        HTTPException (400, 413, 422) if validation or extraction fails.
    """
    safe_name = sanitize_filename(filename)
    validate_pdf_bytes(file_bytes, safe_name)

    doc: Optional[pymupdf.Document] = None
    try:
        # Open PDF directly from memory stream to prevent unsafe filesystem persistence
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        logger.warning("Corrupted or malformed PDF upload: %s", exc)
        raise PDFProcessingError(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded PDF file is corrupted or could not be parsed.",
        )

    try:
        # 1. Check for password encryption
        if doc.is_encrypted:
            raise PDFProcessingError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded PDF is password-protected or encrypted. Please remove the password and retry.",
            )

        page_count = len(doc)
        if page_count == 0:
            raise PDFProcessingError(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded PDF contains no pages.",
            )

        # 2. Extract text page by page, preserving paragraph boundaries
        page_texts: list[str] = []
        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            # "text" layout preserves paragraphs and logical line feeds
            text = page.get_text("text")
            if text and text.strip():
                page_texts.append(text.strip())

        combined_text = "\n\n".join(page_texts).strip()

        # 3. Detect scanned / image-only PDFs with no extractable text
        if not combined_text:
            # Check if optional OCR extension point can extract text
            ocr_text = ocr_fallback_extension_point(doc)
            if ocr_text and ocr_text.strip():
                combined_text = ocr_text.strip()
            else:
                raise PDFProcessingError(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "The uploaded PDF contains no extractable text. The document may be "
                        "scanned or image-based. Optical Character Recognition (OCR) is required "
                        "for scanned documents."
                    ),
                )

        metadata = {
            "fileName": safe_name,
            "pageCount": page_count,
            "fileSizeBytes": len(file_bytes),
            "characterCount": len(combined_text),
        }

        return combined_text, metadata

    finally:
        # Ensure document handle is cleanly closed
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass

