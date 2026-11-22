FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to ensure proper wheel resolution
RUN pip install --no-cache-dir --upgrade pip

# Install lightweight CPU-only PyTorch using --extra-index-url so PyPI remains available for dependencies
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend, model architecture definitions, pre-trained weights, and vocabulary
COPY backend/ ./backend/
COPY training/ ./training/
COPY models/ ./models/
COPY data/processed/ ./data/processed/
COPY docs/ ./docs/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=10000

EXPOSE 10000

# Start FastAPI server on Render's dynamic $PORT
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
