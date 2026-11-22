"""
Security middleware: Request body size limiting and defensive HTTP headers.

Implements Phase 3 Public API Security Controls:
- ASGI-level request body size limiter protecting against memory exhaustion DoS.
- Defensive HTTP security headers (nosniff, DENY, strict-origin, CSP, conditional HSTS).
"""

import os
import uuid
from typing import Optional
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEFAULT_MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(1024 * 1024)))  # 1 MB
DEFAULT_MAX_PDF_FILE_BYTES = int(os.getenv("MAX_PDF_FILE_BYTES", str(10 * 1024 * 1024)))  # 10 MB


class BodySizeExceededError(Exception):
    """Raised when an incoming request body exceeds the configured byte ceiling."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"Request body exceeds maximum allowed size of {limit} bytes.")


class RequestBodySizeLimitMiddleware:
    """
    ASGI middleware enforcing maximum request body size (in bytes).

    Protects against memory exhaustion and payload flooding DoS attacks.
    Evaluates Content-Length immediately and monitors streaming/chunked bodies
    as chunks arrive over the socket.
    Applies MAX_PDF_FILE_BYTES for PDF upload endpoints and MAX_REQUEST_BODY_BYTES elsewhere.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_body_bytes: Optional[int] = None,
        max_pdf_bytes: Optional[int] = None,
    ) -> None:
        self.app = app
        self.max_body_bytes = (
            max_body_bytes if max_body_bytes is not None else DEFAULT_MAX_REQUEST_BODY_BYTES
        )
        self.max_pdf_bytes = (
            max_pdf_bytes if max_pdf_bytes is not None else DEFAULT_MAX_PDF_FILE_BYTES
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        is_pdf_endpoint = path.rstrip("/").endswith("/extract/pdf")
        effective_limit = self.max_pdf_bytes if is_pdf_endpoint else self.max_body_bytes

        # 1. Early rejection based on Content-Length header
        headers = Headers(scope=scope)
        content_length_str = headers.get("content-length")
        if content_length_str:
            try:
                content_length = int(content_length_str)
                if content_length > effective_limit:
                    req_id = str(uuid.uuid4())[:8]
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body exceeds maximum allowed size of {effective_limit} bytes.",
                            "requestId": f"req-{req_id}",
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        # 2. Monitored stream for chunked or missing Content-Length bodies
        total_received = 0
        response_started = False

        async def monitored_receive() -> Message:
            nonlocal total_received
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                total_received += len(chunk)
                if total_received > effective_limit:
                    raise BodySizeExceededError(effective_limit)
            return message

        async def monitored_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, monitored_receive, monitored_send)
        except BodySizeExceededError:
            if not response_started:
                req_id = str(uuid.uuid4())[:8]
                response = JSONResponse(
                    status_code=413,
                    content={
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Request body exceeds maximum allowed size of {effective_limit} bytes.",
                        "requestId": f"req-{req_id}",
                    },
                )
                await response(scope, receive, send)


class SecurityHeadersMiddleware:
    """
    ASGI middleware injecting defensive HTTP response headers.

    Headers attached:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy (CSP)
    - Strict-Transport-Security (HSTS, only in production HTTPS)
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_production = os.getenv("ENVIRONMENT", "development").lower() in {"production", "prod"}

        # Determine protocol / scheme
        headers = Headers(scope=scope)
        proto = headers.get("x-forwarded-proto", scope.get("scheme", "http")).lower()
        is_https = proto == "https" or os.getenv("SECURE_HSTS_ENABLED", "false").lower() in {"true", "1", "yes"}

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))

                def set_header(name: bytes, value: bytes) -> None:
                    # Replace if header already present, else append
                    for idx, (h_name, _) in enumerate(resp_headers):
                        if h_name.lower() == name.lower():
                            resp_headers[idx] = (name, value)
                            return
                    resp_headers.append((name, value))

                # 1. MIME-sniffing protection
                set_header(b"x-content-type-options", b"nosniff")

                # 2. Clickjacking protection
                set_header(b"x-frame-options", b"DENY")

                # 3. Referrer leakage protection
                set_header(b"referrer-policy", b"strict-origin-when-cross-origin")

                # 4. Content Security Policy (aligned with React, Vite & Google Fonts)
                from backend.app.middleware.csrf import get_allowed_origins

                extra_origins = " ".join(get_allowed_origins())
                connect_src = (
                    f"'self' http://localhost:8000 http://127.0.0.1:8000 http://localhost:5173 http://127.0.0.1:5173 {extra_origins}"
                ).strip()

                csp_value = (
                    "default-src 'self'; "
                    "script-src 'self'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "img-src 'self' data:; "
                    f"connect-src {connect_src}; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self'"
                )
                set_header(b"content-security-policy", csp_value.encode("utf-8"))

                # 5. HSTS (Strict-Transport-Security): ONLY in production HTTPS
                if is_production and is_https:
                    set_header(
                        b"strict-transport-security",
                        b"max-age=31536000; includeSubDomains",
                    )

                message["headers"] = resp_headers

            await send(message)

        await self.app(scope, receive, send_with_headers)

