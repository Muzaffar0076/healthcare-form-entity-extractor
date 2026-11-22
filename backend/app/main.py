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

import os
import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import init_db, secure_db_permissions
from backend.app.middleware.csrf import CSRFProtectionMiddleware, get_allowed_origins
from backend.app.middleware.error_handler import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from backend.app.middleware.security import (
    RequestBodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from backend.app.routes import (
    auth_router,
    extraction_router,
    health_router,
    history_router,
    model_router,
)
from backend.app.services.auth_service import get_jwt_secret_key
from backend.app.services.predictor import predictor_instance


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    - SEC-01: Validates cryptographic secret configuration.
    - Initializes SQLite database tables.
    - Loads trained BiLSTM-CRF model at startup.
    """
    print("Initializing Healthcare Form Entity Extractor service...")

    # SEC-01: Fail startup in production if secret is missing or insecure
    get_jwt_secret_key()

    try:
        init_db()
        print("User database initialized successfully.")
    except Exception as exc:
        print(f"Warning: Database failed to initialize: {exc}")

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

# SEC-09: Defensive HTTP Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# SEC-08: ASGI-level Request Body Size Limit Middleware (1 MB default ceiling)
app.add_middleware(RequestBodySizeLimitMiddleware)

# SEC-05: CSRF Protection Middleware
app.add_middleware(CSRFProtectionMiddleware)

# SEC-02: Strict CORS origin whitelisting (fail-closed in production, localhost in development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom structured error handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Authentication routes (/api/auth and /api/v1/auth)
app.include_router(auth_router, prefix="/api")
app.include_router(auth_router, prefix="/api/v1")

# Versioned API routes (/api/v1)
app.include_router(extraction_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api")
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
