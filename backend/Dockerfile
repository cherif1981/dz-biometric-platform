FROM python:3.11-slim

<<<<<<< HEAD
=======
# اعتماديات النظام لـ OpenCV و Tesseract
RUN apt-get update && apt-get install -y \
    libgl1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

>>>>>>> f2d72cbd4e3f9478b21a8bd5746d3ae28b8b53ce
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

<<<<<<< HEAD
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
=======
COPY ai/ ./ai/
COPY backend/ ./backend/

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
>>>>>>> f2d72cbd4e3f9478b21a8bd5746d3ae28b8b53ce
