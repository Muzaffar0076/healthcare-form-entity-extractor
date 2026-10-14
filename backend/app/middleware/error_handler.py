"""
Custom exception handlers and middleware for structured API errors.

Complies with PRD Section 08 (Structured Error Responses).
"""

import uuid
from typing import Any
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle Starlette / FastAPI HTTPExceptions with structured payload.
    """
    req_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])

    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_503_SERVICE_UNAVAILABLE: "MODEL_UNAVAILABLE",
    }
    error_code = code_map.get(exc.status_code, "ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": error_code,
            "message": str(exc.detail),
            "requestId": f"req-{req_id}",
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation errors (Pydantic / missing fields).
    """
    req_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])

    messages = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "invalid")
        messages.append(f"{loc}: {msg}" if loc else msg)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "; ".join(messages),
            "requestId": f"req-{req_id}",
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected internal server errors.
    """
    req_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred. Please try again later.",
            "requestId": f"req-{req_id}",
        },
    )
