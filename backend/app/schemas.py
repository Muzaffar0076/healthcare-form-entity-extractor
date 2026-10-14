"""
Pydantic schemas for the Healthcare Form Entity Extractor API.

Compliant with PRD Section 08 (API Specification).
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class ExtractRequest(BaseModel):
    """
    Request payload for text extraction.
    """

    text: str = Field(
        ...,
        description="Patient-facing healthcare text to extract entities from.",
        json_schema_extra={"example": "I was prescribed Aspirin on 12 March 2026 for diabetes."},
    )

    @field_validator("text")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Text input cannot be empty.")
        if len(value) > 20000:
            raise ValueError("Text input exceeds maximum allowed length of 20,000 characters.")
        return value


class EntityItem(BaseModel):
    """
    Structured entity representation with character boundaries.
    """

    text: str = Field(..., description="The matched entity substring.")
    label: str = Field(..., description="Entity category: DATE, MEDICATION, or CONDITION.")
    start: int = Field(..., description="0-indexed start character offset in original text.")
    end: int = Field(..., description="0-indexed end character offset in original text.")
    confidence: Optional[float] = Field(
        None, description="Confidence score between 0.0 and 1.0 where supported."
    )


class ExtractResponse(BaseModel):
    """
    Response returned by POST /api/v1/extract.
    """

    text: str
    entities: list[EntityItem]
    modelVersion: str


class HealthResponse(BaseModel):
    """
    Response returned by GET /health.
    """

    status: str = Field("healthy", description="Status string: healthy or degraded.")
    modelLoaded: bool = Field(True, description="Whether the NER model is loaded in memory.")
    modelVersion: str = Field("bilstm-crf-v1", description="Loaded model version.")


class ModelMetadataResponse(BaseModel):
    """
    Response returned by GET /model.
    """

    model_name: str
    model_version: str
    architecture: str
    entities: list[str]
    metrics: dict[str, Any]
    device: str


class ErrorResponse(BaseModel):
    """
    Standardized structured error response.
    """

    code: str
    message: str
    requestId: Optional[str] = None
