FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev python3-dev \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Render sets PORT at runtime (default 10000)
EXPOSE 10000

CMD uvicorn src.main:app --host 0.0.0.0 --port $PORT
