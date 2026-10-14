"""
FastAPI application entrypoint for Healthcare Form Entity Extractor.

Compliant with PRD Section 08 (API Specification) and HLD Section 06.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from backend.app.routes import extraction_router, health_router, model_router
from backend.app.services.predictor import predictor_instance


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Loads the trained BiLSTM-CRF model once at startup to keep extraction stateless and fast.
    """
    print("Initializing Healthcare Form Entity Extractor service...")
    try:
        predictor_instance.load()
        print("Model and vocabulary loaded successfully.")
    except Exception as exc:
        print(f"Warning: Model failed to load at startup: {exc}")
    yield
    print("Shutting down Healthcare Form Entity Extractor service.")


app = FastAPI(
    title="Healthcare Form Entity Extractor API",
    description=(
        "Named Entity Recognition REST API based on BiLSTM-CRF for extracting "
        "dates, medications, and conditions from patient-facing medical forms."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom structured error handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Versioned API routes (/api/v1)
app.include_router(extraction_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(model_router, prefix="/api/v1")

# Top-level health route compatibility (/health)
app.include_router(health_router)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    return {
        "service": "Healthcare Form Entity Extractor API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
