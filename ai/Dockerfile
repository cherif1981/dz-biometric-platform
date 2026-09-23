FROM python:3.10-slim

# System dependencies for Tesseract + face_recognition (dlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-fra \
    cmake \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy AI service code
COPY ai/ ./ai/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "ai.main:app", "--host", "0.0.0.0", "--port", "8001"]