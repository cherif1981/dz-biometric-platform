FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-fra \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# تحميل نموذج InsightFace مسبقاً
RUN python -c "from insightface.app import FaceAnalysis; \
    app = FaceAnalysis(name='buffalo_l'); app.prepare(ctx_id=0, det_size=(640, 640))"

# تحميل نموذج Liveness
RUN mkdir -p ai/liveness/models && \
    wget -q -O ai/liveness/models/MiniFASNetV2.onnx \
    "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx"

COPY . .

CMD ["python", "-c", "print('AI service ready')"]