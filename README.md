# DZ Biometric Platform

منصة للتعرف على البطاقات البيومترية الجزائرية (OCR + التحقق من الوجه).

## المكونات

- **backend/** : FastAPI + PostgreSQL + JWT
- **ai/** : خدمة مستقلة (كشف البطاقة، OCR، التعرف على الوجه، التحقق)
- **frontend/** : (قيد التطوير)
- **storage/** : تخزين مؤقت للصور

## التشغيل السريع

```bash
cp .env.example .env
docker compose up --build