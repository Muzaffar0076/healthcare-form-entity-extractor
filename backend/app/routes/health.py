"""
Health check route.
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.schemas import HealthResponse
from backend.app.services.predictor import predictor_instance

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Returns service and model health status.
    """
    if not predictor_instance.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NER model artifact is unavailable or failed to load.",
        )

    return HealthResponse(
        status="healthy",
        modelLoaded=True,
        modelVersion=predictor_instance.model_version,
    )
