WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai ./ai
COPY backend ./backend

ENV PYTHONPATH=/app/backend:/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]