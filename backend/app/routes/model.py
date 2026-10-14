"""
Model information and model-card routes.
"""

from typing import Any
from fastapi import APIRouter

from backend.app.schemas import ModelMetadataResponse
from backend.app.services.predictor import predictor_instance

router = APIRouter(tags=["Model Metadata"])


@router.get("/model", response_model=ModelMetadataResponse)
def get_model_metadata() -> ModelMetadataResponse:
    """
    Returns non-sensitive model metadata, version, and evaluation metrics.
    """
    return ModelMetadataResponse(
        model_name="Healthcare Form Entity Extractor",
        model_version=predictor_instance.model_version,
        architecture="BiLSTM-CRF",
        entities=["DATE", "MEDICATION", "CONDITION"],
        metrics=predictor_instance.metrics.get("test_metrics", {}),
        device=str(predictor_instance.device),
    )


@router.get("/model-card")
def get_model_card() -> dict[str, Any]:
    """
    Returns model card details, intended use, and limitations per PRD Section 21.
    """
    return {
        "model_details": {
            "name": "BiLSTM-CRF Healthcare Named Entity Recognition",
            "framework": "PyTorch",
            "task": "Sequence Labeling / NER",
            "version": predictor_instance.model_version,
            "target_entities": ["DATE", "MEDICATION", "CONDITION"],
        },
        "intended_use": [
            "Assisting non-native speakers and care navigators in identifying key entities in medical forms",
            "Accessibility and reading support",
            "Educational and demonstration prototype",
        ],
        "out_of_scope": [
            "Autonomous clinical diagnosis",
            "Prescription validation",
            "Treatment recommendation",
            "Emergency triage",
        ],
        "metrics_summary": predictor_instance.metrics.get("test_metrics", {}).get("micro", {}),
        "disclaimer": "This is an informational extraction prototype and does not provide medical advice.",
    }
