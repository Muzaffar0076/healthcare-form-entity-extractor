# Security Policy and Architecture

## 1. Overview and Threat Model

**Healthcare Form Entity Extractor** is an intelligent assistant designed to extract clinical dates, medications, and medical conditions from patient-facing medical forms. The system consists of:
- A **FastAPI** backend exposing a public Named Entity Recognition (NER) inference API and protected user authentication endpoints.
- A **BiLSTM-CRF** neural network model with hybrid rule-based pre/post-processing for entity extraction.
- A **React + Vite** single-page application providing form input, live entity highlighting, and account management.
- An **SQLite** relational database managing user accounts and revoked token identifiers (`jti`).

### Threat Model Scope
The application defends against the following primary threat vectors:
1. **Denial of Service (DoS) & Resource Exhaustion:** Malicious actors sending oversized payloads or unbounded rapid-fire requests to consume memory or GPU/CPU inference threads.
2. **IP Spoofing & Header Injection:** Attackers forging `X-Forwarded-For` HTTP headers to bypass rate limits or poison logs.
3. **Cross-Site Request Forgery (CSRF) & Session Hijacking:** Forged state-changing requests or unauthorized access to authentication credentials stored in the browser.
4. **Credential Stuffing & Brute Force:** Automated attacks against user registration and authentication endpoints.
5. **Information Leakage & Data Privacy Risks:** Exposure of server stack traces, ML model internal structures, or patient clinical text in logs or responses.
6. **Unauthorized Database Access:** Unauthorized local OS users reading relational database files containing user hashes.

---

## 2. Security Architecture & Defensive Controls

### 2.1 Public Entity Extraction Pipeline (`POST /api/v1/extract`)
The extraction endpoint remains **fully public** to allow unregistered patients and care navigators to process healthcare forms without requiring an account. To protect this public endpoint from abuse:
- **Rate Limiting:** Enforces an IP-level rate limit (default: 30 requests/minute, configurable via `RATE_LIMIT_EXTRACT_PER_MIN` and `RATE_LIMIT_EXTRACT_WINDOW_SECS`). Exceeding requests receive an HTTP `429 Too Many Requests` status with an RFC-compliant `Retry-After` header.
- **Request Body Size Ceiling:** An ASGI-level middleware strictly limits incoming request bodies to 1 MB (`MAX_REQUEST_BODY_BYTES`, default `1048576`). Requests exceeding this size—whether declared via `Content-Length` or streamed incrementally via chunked transfer encoding—are immediately terminated with HTTP `413 PAYLOAD_TOO_LARGE` before model execution.
- **Generic Error Masking:** Unhandled inference exceptions return a standardized, generic error message along with an opaque `requestId`. Internal python exception details, tracebacks, and model state are never leaked to clients.
- **Service Availability Check:** If model weights or vocabulary files are missing or uninitialized, the endpoint returns HTTP `503 Service Unavailable` with a clean diagnostic response.

### 2.2 PDF Upload & Document Processing Pipeline (`POST /api/v1/extract/pdf`)
The application supports uploading healthcare documents in PDF format for automated text extraction and NER inference:
- **Zero Raw File Retention:** Uploaded PDF documents are processed entirely in-memory using PyMuPDF stream buffers. Binary PDF files are **never** persisted to server disks, databases, or temporary caches.
- **File Validation & Anti-Tampering:** Validates file extension (`.pdf`), MIME types (`application/pdf`), and verifies genuine `%PDF-` file signature magic bytes. Rejects non-PDF payloads before parsing.
- **Configurable Size Limits:** Enforces a dedicated 10 MB maximum size ceiling (`MAX_PDF_FILE_BYTES`), rejecting oversized uploads with HTTP 413 `PAYLOAD_TOO_LARGE`.
- **Encrypted & Corrupted Document Handling:** Password-protected/encrypted PDFs and corrupted binary streams are rejected with descriptive HTTP 422 errors without server crashing or information leakage.
- **Scanned Document Detection & OCR Hook:** Automatically detects when a PDF contains no extractable text (e.g. scanned or image-only documents) and returns HTTP 422 with guidance on Optical Character Recognition (OCR), providing a safe architecture extension point without falsely claiming OCR capabilities.
- **Rate Limiting:** Governed by the same sliding-window rate limiter (30 requests/minute per IP) to prevent document processing denial-of-service.

### 2.2 Client IP & Trusted Proxy Verification
To prevent IP spoofing attacks via forged `X-Forwarded-For` headers:
- The application inspects `X-Forwarded-For` **only if** the direct peer socket (`request.client.host`) matches a configured trusted proxy address in `TRUSTED_PROXY_IPS`.
- `TRUSTED_PROXY_IPS` supports comma-separated exact IP addresses, CIDR network blocks (e.g., `10.0.0.0/8`, `172.16.0.0/12`), and specific hostnames (e.g., `localhost`).
- Forwarded IP candidates are strictly parsed using Python's standard `ipaddress` library.
- If the direct peer is untrusted, all forwarded headers are ignored and the TCP socket peer IP is used as the canonical client IP.

### 2.3 Authentication & Session Security
- **Password Hashing:** Passwords are hashed using `bcrypt` with a cost factor of 12. Password inputs exceeding 72 UTF-8 bytes are strictly rejected prior to hashing to eliminate bcrypt truncation vulnerabilities.
- **Token Storage:** JWT access tokens are delivered and stored exclusively via `HttpOnly`, `Secure`, `SameSite=Lax` cookies. JavaScript running in the browser cannot read or exfiltrate the JWT.
- **Token Revocation (Denylist):** Every issued JWT includes a unique UUID (`jti`). Upon logout, the `jti` is persisted to a server-side revocation table (`revoked_tokens`) with its expiration timestamp. Authenticated endpoints verify that the presented `jti` is active and unrevoked.
- **Strict CORS Policy:** Wildcard origins (`*`) are disallowed. Allowed origins are strictly loaded from `ALLOWED_ORIGINS` with full credentials support (`allow_credentials=True`).

### 2.4 CSRF Protection
State-changing endpoints (`POST`, `PUT`, `PATCH`, `DELETE`) are protected by a signed Synchronizer Token Pattern:
- **Token Format:** `timestamp:nonce:binding:signature` signed using HMAC-SHA256 with the server's `JWT_SECRET_KEY`.
- **Binding:** Tokens for authenticated sessions are bound directly to the user's active `jti`. Tokens for unauthenticated flows (e.g., login, registration) are bound to a dedicated anonymous cookie.
- **Verification:** All signature and token comparisons use constant-time `hmac.compare_digest` to prevent timing attacks. In production, requests must provide matching `Origin` headers from authorized origins.

### 2.5 Defensive HTTP Security Headers
Every HTTP response carries protective headers enforced via ASGI middleware:
- `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing.
- `X-Frame-Options: DENY`: Prevents clickjacking by disabling embedding in iframes.
- `Referrer-Policy: strict-origin-when-cross-origin`: Controls referrer leakage.
- `Content-Security-Policy`: Restricts resource execution to `self`, allowing necessary inline styles and fonts for the React UI.
- `Strict-Transport-Security`: (Optional) Emits HSTS headers when `SECURE_HSTS_ENABLED=true` in production HTTPS environments.

### 2.6 Database File Permissions
During initialization on Unix/POSIX systems, the application sets file permissions of `0600` (`-rw-------`) on the SQLite database (`data/users.db`), ensuring only the running operating system user has read and write access.

---

## 3. Data Retention & Healthcare Privacy

### 3.1 Public Extraction Zero-Persistence Policy
Form text submitted anonymously to the public entity extraction API (`POST /api/v1/extract`) is treated as volatile:
- Text is processed **in-memory only** during tokenization, rule matching, and BiLSTM-CRF inference.
- Form text is **never** written to the database, cached to temporary disk storage, or logged to application output.
- Server logs record request metadata (method, path, HTTP status, execution latency, and anonymized request identifiers), but explicitly omit the request payload.

### 3.2 Authenticated User Extraction History & Explicit Consent Policy
To support patients and care navigators who wish to track and review previous medical form analyses, the application provides an authenticated Extraction History feature (`POST /api/v1/history`, `GET /api/v1/history`, `GET /api/v1/history/{id}`, `DELETE /api/v1/history/{id}`):
- **Explicit User Consent Required:** Persistence is disabled by default. The application requires explicit user consent before storing any extraction history. Unauthenticated users cannot save history.
- **Stored Information:** When an authenticated user gives explicit consent and saves an extraction, the database stores:
  1. The original submitted healthcare form text.
  2. Extracted entities (labels, character offsets `start`/`end`, and confidence).
  3. Creation timestamp and associated `user_id`.
- **User Ownership & Permanent Deletion:** Each extraction record is strictly isolated to the authenticated user. Users can review their saved records and permanently delete individual records or their entire history at any time.
- **Access Controls & Storage Security:** Stored in the SQLite database (`data/users.db`) with `0600` file permission enforcement (POSIX owner-only read/write). Cross-user access is blocked at the database query layer (queries filter strictly by `user_id == current_user._id`, returning 404 for unauthorized accesses).
- **Zero Logging:** Form text and extracted medical entities are never logged to console or log streams during history creation, retrieval, or deletion.

### 3.3 Non-HIPAA Compliance Notice
> **DISCLAIMER:**  
> The Healthcare Form Entity Extractor is an open-source educational and technical demonstration tool.  
> **This software is NOT certified for HIPAA compliance** (Health Insurance Portability and Accountability Act) and does not execute Business Associate Agreements (BAAs).  
> **DO NOT** process, transmit, or store real, non-synthetic Protected Health Information (PHI) in production environments without comprehensive external security reviews, organizational compliance audits, and appropriate legal and technological safeguards.

---

## 4. Multi-Worker Rate Limiting Notice

Rate limiting in the current architecture is managed by an in-memory sliding window cache (`InMemoryRateLimiter`).
- Rate limit buckets are maintained within the memory of the running Python worker process.
- When running multiple Uvicorn/ASGI workers behind a load balancer or reverse proxy, rate limits apply per worker process unless the proxy is configured with sticky sessions (e.g., IP hashing).
- For distributed multi-node deployments requiring shared rate limits across independent hosts, a centralized caching backend (such as Redis) may be integrated.

---

## 5. Security Vulnerability Reporting

If you identify a security vulnerability in this project:
1. **Do not open a public GitHub issue.**
2. Send a detailed vulnerability report privately to the maintainers or project administrators.
3. Include reproducible steps, proof-of-concept payloads, and relevant configuration details.
4. Allow reasonable time for investigation and patch development prior to public disclosure.

