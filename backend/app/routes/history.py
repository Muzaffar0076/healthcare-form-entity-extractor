"""
Extraction History API endpoints.

Allows authenticated users to save, retrieve, view, and delete their previous
healthcare form extraction records.
Strictly isolated per user — users can never view or modify another user's records.
Zero logging of healthcare form text or extracted medical entities.
"""

from collections import Counter
import logging
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.middleware.auth import get_current_user
from backend.app.models.history import ExtractionHistoryModel
from backend.app.models.user import UserModel
from backend.app.schemas import (
    HistoryCreateRequest,
    HistoryDeleteResponse,
    HistoryDetailResponse,
    HistoryEntitiesContainer,
    HistoryItemSummary,
    PaginatedHistoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["Extraction History"])


def _calculate_entity_metrics(entities_data: Any) -> tuple[dict[str, int], int]:
    """
    Calculate entity counts grouped by label and total count from stored JSON.
    """
    if isinstance(entities_data, dict):
        raw_list = entities_data.get("entities", [])
    elif isinstance(entities_data, list):
        raw_list = entities_data
    else:
        raw_list = []

    counts: dict[str, int] = dict(Counter(e.get("label", "UNKNOWN") for e in raw_list if isinstance(e, dict)))
    total = len(raw_list)
    return counts, total


def _format_preview(text: str, max_length: int = 120) -> str:
    """
    Generate a clean single-line preview of the original form text.
    """
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length].rstrip() + "..."


@router.post("", response_model=HistoryDetailResponse, status_code=status.HTTP_201_CREATED)
def create_history_record(
    payload: HistoryCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryDetailResponse:
    """
    Save a healthcare form extraction record for the currently authenticated user.
    Validates form text, entity labels, and character offsets.
    """
    record = ExtractionHistoryModel(
        user_id=current_user._id,
        form_text=payload.form_text,
        extracted_entities=payload.extracted_entities.model_dump(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    entity_counts, total_entities = _calculate_entity_metrics(record.extracted_entities)

    logger.info(
        "Extraction history record created [recordId=%s, userId=%s, entityCount=%d]",
        record.id,
        current_user._id,
        total_entities,
    )

    return HistoryDetailResponse(
        id=record.id,
        user_id=record.user_id,
        form_text=record.form_text,
        extracted_entities=HistoryEntitiesContainer(**record.extracted_entities),
        created_at=record.created_at.isoformat(),
        entity_counts=entity_counts,
        total_entities=total_entities,
    )


@router.get("", response_model=PaginatedHistoryResponse)
def get_user_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedHistoryResponse:
    """
    Retrieve paginated extraction history belonging exclusively to the authenticated user.
    Records are sorted by newest first.
    """
    base_query = db.query(ExtractionHistoryModel).filter(
        ExtractionHistoryModel.user_id == current_user._id
    )

    total = base_query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 1
    offset = (page - 1) * limit

    records = (
        base_query.order_by(ExtractionHistoryModel.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: list[HistoryItemSummary] = []
    for r in records:
        counts, count_total = _calculate_entity_metrics(r.extracted_entities)
        items.append(
            HistoryItemSummary(
                id=r.id,
                user_id=r.user_id,
                form_text_preview=_format_preview(r.form_text),
                created_at=r.created_at.isoformat(),
                entity_counts=counts,
                total_entities=count_total,
            )
        )

    return PaginatedHistoryResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{record_id}", response_model=HistoryDetailResponse)
def get_history_detail(
    record_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryDetailResponse:
    """
    Retrieve one extraction history record.
    Returns 404 if the record does not exist or belongs to another user.
    """
    record = (
        db.query(ExtractionHistoryModel)
        .filter(
            ExtractionHistoryModel.id == record_id,
            ExtractionHistoryModel.user_id == current_user._id,
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction history record not found.",
        )

    entity_counts, total_entities = _calculate_entity_metrics(record.extracted_entities)

    return HistoryDetailResponse(
        id=record.id,
        user_id=record.user_id,
        form_text=record.form_text,
        extracted_entities=HistoryEntitiesContainer(**record.extracted_entities),
        created_at=record.created_at.isoformat(),
        entity_counts=entity_counts,
        total_entities=total_entities,
    )


@router.delete("/{record_id}", response_model=HistoryDeleteResponse)
def delete_history_record(
    record_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryDeleteResponse:
    """
    Delete a specific extraction history record.
    Verifies ownership before deletion. Returns 404 if not found.
    """
    record = (
        db.query(ExtractionHistoryModel)
        .filter(
            ExtractionHistoryModel.id == record_id,
            ExtractionHistoryModel.user_id == current_user._id,
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction history record not found.",
        )

    db.delete(record)
    db.commit()

    logger.info(
        "Extraction history record deleted [recordId=%s, userId=%s]",
        record_id,
        current_user._id,
    )

    return HistoryDeleteResponse(
        message="Extraction history record deleted successfully.",
        id=record_id,
    )

