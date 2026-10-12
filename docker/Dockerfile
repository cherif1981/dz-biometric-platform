FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# System deps for OpenCV + Tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra \
    curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src/ ./src/
COPY docs/ ./docs/ 2>/dev/null || true

EXPOSE 8000
HEALTHCHECK CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]