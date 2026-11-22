"""
Pydantic schemas for the Healthcare Form Entity Extractor API.

Compliant with PRD Section 08 (API Specification).
"""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class PDFMetadata(BaseModel):
    """
    Metadata about an uploaded and processed PDF document.
    """

    fileName: str
    pageCount: int
    fileSizeBytes: int
    characterCount: int


class PDFExtractResponse(ExtractResponse):
    """
    Response returned by POST /api/v1/extract/pdf.
    Extends ExtractResponse with PDF document metadata.
    """

    metadata: PDFMetadata


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


# --- Authentication & User Schemas ---

import re
from pydantic import model_validator

# Standard RFC email pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

# Optional phone number pattern
PHONE_REGEX = re.compile(
    r"^\+?[0-9\s\-\(\)]{7,25}$"
)


class UserRegisterRequest(BaseModel):
    """
    Request payload for registering a new user account.
    """

    fullName: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
        json_schema_extra={"example": "Jane Doe"},
    )
    email: str = Field(
        ...,
        max_length=255,
        description="Unique email address",
        json_schema_extra={"example": "jane.doe@example.com"},
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Account password (8-72 characters, letters and numbers, max 72 UTF-8 bytes)",
        json_schema_extra={"example": "SecurePass123!"},
    )
    confirmPassword: str = Field(
        ...,
        description="Password confirmation, must match password",
        json_schema_extra={"example": "SecurePass123!"},
    )
    phoneNumber: Optional[str] = Field(
        None,
        max_length=25,
        description="Optional contact telephone number",
        json_schema_extra={"example": "+1-555-0199"},
    )

    @field_validator("fullName")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        return trimmed

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        norm = value.strip().lower()
        if not EMAIL_REGEX.match(norm):
            raise ValueError("Invalid email address format.")
        return norm

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        utf8_bytes = value.encode("utf-8")
        if len(utf8_bytes) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(utf8_bytes) > 72:
            raise ValueError("Password cannot exceed 72 bytes due to bcrypt limitation.")
        if not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one letter and one number.")
        return value

    @field_validator("phoneNumber")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not PHONE_REGEX.match(trimmed):
            raise ValueError("Invalid phone number format.")
        return trimmed

    @model_validator(mode="after")
    def verify_passwords_match(self) -> "UserRegisterRequest":
        if self.password != self.confirmPassword:
            raise ValueError("Passwords do not match.")
        return self


class UserLoginRequest(BaseModel):
    """
    Request payload for authenticating an existing user.
    """

    email: str = Field(
        ...,
        description="User email address",
        json_schema_extra={"example": "jane.doe@example.com"},
    )
    password: str = Field(
        ...,
        description="User password",
        json_schema_extra={"example": "SecurePass123!"},
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    """
    Public representation of user profile (passwords strictly excluded).
    """

    id: str = Field(..., alias="_id", description="Unique user identifier")
    fullName: str
    email: str
    phoneNumber: Optional[str] = None
    role: str = "user"
    isVerified: bool = True
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AuthResponse(BaseModel):
    """
    Authentication response with user profile and optional CSRF token.
    JWT is never exposed in response body and is delivered strictly via HttpOnly cookie.
    """

    message: str = "Authentication successful."
    user: UserResponse
    csrfToken: Optional[str] = None


# Alias for backward compatibility if imported elsewhere
AuthTokenResponse = AuthResponse


class LogoutResponse(BaseModel):
    """
    Response returned on user logout.
    """

    message: str = "Logged out successfully."


class CSRFTokenResponse(BaseModel):
    """
    Response returned by GET /api/auth/csrf-token.
    """

    csrfToken: str


# --- User Extraction History Schemas ---

from datetime import datetime

VALID_ENTITY_LABELS = {"DATE", "MEDICATION", "CONDITION"}


class HistoryEntityItem(BaseModel):
    """
    Single extracted entity with label and character positions.
    """

    text: str = Field(..., description="Matched entity substring.")
    label: str = Field(..., description="Entity category: DATE, MEDICATION, or CONDITION.")
    start: int = Field(..., ge=0, description="0-indexed start character offset in original text.")
    end: int = Field(..., gt=0, description="0-indexed end character offset in original text.")
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0 where supported."
    )

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        upper = value.strip().upper()
        if upper not in VALID_ENTITY_LABELS:
            raise ValueError(
                f"Invalid entity label '{value}'. Allowed labels are: {', '.join(sorted(VALID_ENTITY_LABELS))}."
            )
        return upper


class HistoryEntitiesContainer(BaseModel):
    """
    Container for extracted entities list.
    """

    entities: list[HistoryEntityItem] = Field(default_factory=list)


class HistoryCreateRequest(BaseModel):
    """
    Payload for saving an extraction to user history.
    """

    form_text: str = Field(
        ...,
        description="Original submitted healthcare form text.",
    )
    extracted_entities: HistoryEntitiesContainer = Field(
        ...,
        description="Container of extracted entities with labels and offsets.",
    )

    @field_validator("form_text")
    @classmethod
    def validate_form_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Form text cannot be empty.")
        if len(value) > 20000:
            raise ValueError("Form text exceeds maximum allowed length of 20,000 characters.")
        return value

    @model_validator(mode="after")
    def validate_entity_positions(self) -> "HistoryCreateRequest":
        text = self.form_text
        text_len = len(text)
        for idx, ent in enumerate(self.extracted_entities.entities):
            if ent.start >= ent.end:
                raise ValueError(
                    f"Entity at index {idx} has invalid offsets: start ({ent.start}) must be strictly less than end ({ent.end})."
                )
            if ent.end > text_len:
                raise ValueError(
                    f"Entity at index {idx} '{ent.text}' ends at offset {ent.end}, which exceeds form text length ({text_len})."
                )
            actual_slice = text[ent.start : ent.end]
            if actual_slice != ent.text:
                raise ValueError(
                    f"Entity at index {idx} text mismatch: expected '{ent.text}', but slice at [{ent.start}:{ent.end}] is '{actual_slice}'."
                )
        return self


class HistoryItemSummary(BaseModel):
    """
    Summary view of an extraction history item for paginated listings.
    """

    id: str
    user_id: str
    form_text_preview: str
    created_at: str
    entity_counts: dict[str, int]
    total_entities: int


class HistoryDetailResponse(BaseModel):
    """
    Detailed view of a single extraction history record.
    """

    id: str
    user_id: str
    form_text: str
    extracted_entities: HistoryEntitiesContainer
    created_at: str
    entity_counts: dict[str, int]
    total_entities: int


class PaginatedHistoryResponse(BaseModel):
    """
    Paginated list of user extraction history records.
    """

    items: list[HistoryItemSummary]
    total: int
    page: int
    limit: int
    total_pages: int


class HistoryDeleteResponse(BaseModel):
    """
    Response returned on successful deletion of a history record.
    """

    message: str = "Extraction history record deleted successfully."
    id: str



