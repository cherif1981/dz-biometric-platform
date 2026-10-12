# Architecture

## Layers
- **API (FastAPI)** → routes & validation
- **Services** → business orchestration
- **Repositories** → DB access
- **Modules** → ML/DSP: OCR, face, liveness, encryption
- **Workers (Celery)** → heavy async jobs (batch OCR, embedding indexing)

## Data flow — Identity verification
1. Client uploads document + selfie
2. `document_reader` validates quality, crops card
3. `ocr` extracts fields (AR + FR)
4. `face_verification` compares selfie ↔ photo in document
5. `liveness` rejects spoofs
6. `encryption` seals sensitive fields before persistence
7. `audit` logs every decision