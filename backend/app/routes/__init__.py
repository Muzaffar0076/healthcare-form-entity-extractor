"""
Routes package for Healthcare Form Entity Extractor.
"""

from .auth import router as auth_router
from .extraction import router as extraction_router
from .health import router as health_router
from .history import router as history_router
from .model import router as model_router

__all__ = ["auth_router", "extraction_router", "health_router", "history_router", "model_router"]
