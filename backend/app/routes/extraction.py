"""
Entity extraction route.
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.schemas import EntityItem, ExtractRequest, ExtractResponse
from backend.app.services.predictor import predictor_instance

router = APIRouter(tags=["Extraction"])


@router.post("/extract", response_model=ExtractResponse)
def extract_entities(payload: ExtractRequest) -> ExtractResponse:
    """
    Extract healthcare entities (DATE, MEDICATION, CONDITION) from input text.
    """
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error during entity extraction: {str(exc)}",
        )
