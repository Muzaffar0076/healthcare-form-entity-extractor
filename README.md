# Healthcare Form Entity Extractor

An accessible, privacy-focused, AI-powered healthcare form entity extraction application designed to help patients, caregivers, and care navigators quickly parse and understand complex medical documents.

Built with a custom **BiLSTM-CRF** biomedical Named Entity Recognition (NER) pipeline, a secure **FastAPI** backend, and a modern **React (Vite)** SaaS dashboard.

---

## Overview

Clinical documentation—such as discharge summaries, clinical notes, lab reports, and prescription instructions—is often dense and difficult to navigate. The **Healthcare Form Entity Extractor** extracts and highlights three critical entity categories with character-exact offsets and confidence scores:

1. **`DATE`**: Appointment dates, discharge timestamps, onset times, and medication schedules.
2. **`MEDICATION`**: Prescribed pharmaceuticals, brand/generic drugs, dosages, and administration frequencies.
3. **`CONDITION`**: Diagnoses, symptoms, disorders, and clinical observations.

> **Important Disclaimer:** This application is designed strictly for information extraction and visual assistance to improve readability. It does **not** provide medical advice, diagnosis, or clinical decision support.

---

## Key Features

- **Biomedical Sequence Labeling**: Custom PyTorch BiLSTM-CRF model trained on biomedical clinical text, augmented with domain lexicons and regex fallbacks.
- **Interactive SaaS Dashboard**: Modern React interface supporting live entity highlighting, entity inspection drawers, document uploads (PDF/text), and confidence badges.
- **Light & Dark Theme**: Full theme support across the entire interface, with high-contrast accessibility-tested entity badges.
- **Enterprise-Grade Security Architecture**:
  - **Session-Bound CSRF Defense**: Cryptographic HMAC-SHA256 tokens bound to user JWT sessions (`jti`).
  - **Encrypted Storage**: Sensitive extraction history records encrypted at rest using AES-GCM (Fernet).
  - **Account Protection**: Argon2id password hashing, sliding refresh tokens, token revocation blocklists, and IP/user rate limiting.
  - **OWASP Hardening**: Strict Content Security Policy (CSP), HSTS, `X-Content-Type-Options`, and sanitized error outputs.
- **PDF & Plain Text Processing**: Support for raw clinical notes and multipage PDF documents via PyMuPDF.

---

## Tech Stack

- **Machine Learning**: PyTorch, BiLSTM-CRF, TorchCRF, NumPy
- **Backend API**: Python 3.10+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy, SQLite
- **Security & Cryptography**: PyJWT, Argon2-cffi, Cryptography (Fernet)
- **Frontend**: React 18, Vite, Lucide Icons, Modern CSS Design System
- **Testing**: Pytest, Pytest-Asyncio, HTTPX

---

## Project Structure

```text
healthcare-form-entity-extractor/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI application entrypoint
│       ├── database.py              # SQLite & SQLAlchemy engine
│       ├── schemas.py               # Pydantic validation schemas
│       ├── middleware/              # Auth, CSRF, Security headers, Rate limiter
│       ├── models/                  # Database models (User, History, Revocation)
│       ├── routes/                  # API endpoints (Auth, Extraction, History)
│       └── services/                # Predictor, PDF parser, Auth service
├── frontend/
│   ├── src/
│   │   ├── components/              # SaaS layout, Workspace, Modals, Highlights
│   │   ├── context/                 # AuthContext, ThemeContext
│   │   ├── services/                # API clients (authApi, historyApi, apiConfig)
│   │   └── utils/                   # Formatting helpers
│   ├── index.html
│   └── vite.config.js
├── models/
│   └── bilstm_crf_v1.pt             # Pre-trained BiLSTM-CRF PyTorch weights
├── data/
│   └── processed/
│       ├── vocab.json               # Word vocabulary index
│       └── labels.json              # Entity label map
├── tests/                           # 95+ unit and integration tests
├── .env.example                     # Environment template
├── requirements.txt                 # Backend dependencies
├── SECURITY.md                      # Security disclosure policy
└── PRD.md                           # Product Requirements Document
```

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm
- Git

---

### Backend Setup

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   *(Ensure you update `SECRET_KEY` and `ENCRYPTION_KEY` with strong random keys for production).*

4. **Run database migrations & initialize tables:**
   ```bash
   python3 -c "from backend.app.database import init_db; init_db()"
   ```

5. **Start the FastAPI server:**
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```
   The backend API will be available at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

---

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```
   The frontend will be running at `http://localhost:5173`.

---

## Running the Test Suite

Execute the full backend test suite covering security, authentication, CSRF, encryption, and extraction:

```bash
PYTHONPATH=. pytest tests/ -v
```

To run the frontend production build:

```bash
cd frontend && npm run build
```

---

## Security & Privacy Policy

This project strictly follows healthcare data privacy principles:
- Text submitted for single-pass entity extraction is processed in memory and not logged or stored without user consent.
- Authenticated users may opt-in to save extraction history, which is encrypted at rest using AES-GCM.
- For vulnerability reports or security practices, refer to [SECURITY.md](SECURITY.md).

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

