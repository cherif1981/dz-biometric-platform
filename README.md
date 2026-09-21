🇩🇿 DZ Biometric Platform

Algerian Digital Identity & Biometric Verification Platform

A modular platform for automated verification of Algerian identity documents using Document AI, OCR, Face Verification, and Liveness Detection.

«⚠️ Project Status: Early Development / MVP
This project is currently under active development and is not yet intended for production use.»

---

🎯 Overview

DZ Biometric Platform aims to provide a secure and modular infrastructure for digital identity verification based on Algerian biometric identity documents.

The platform combines:

- 📄 Identity document detection
- 🔍 OCR and data extraction
- 🧹 Image preprocessing and document normalization
- 👤 Face detection and verification
- 🛡️ Liveness / anti-spoofing
- 🔐 Authentication and authorization
- 📊 Verification sessions and audit logs
- 🗄️ PostgreSQL-based data management
- ⚡ Redis for caching and asynchronous processing

The long-term objective is to provide an API-first identity verification platform that can be integrated into governmental, financial, commercial, and digital services.

---

🏗️ Architecture

                         ┌─────────────────────┐
                         │       Client        │
                         │ Web / Mobile / API  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │      Backend        │
                         └──────────┬──────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
          │ PostgreSQL  │    │    Redis    │    │  AI Service │
          │  Database   │    │ Cache/Queue │    │             │
          └─────────────┘    └─────────────┘    └──────┬──────┘
                                                       │
                                      ┌────────────────┼────────────────┐
                                      │                │                │
                                      ▼                ▼                ▼
                                ┌──────────┐     ┌──────────┐     ┌──────────┐
                                │ Document │     │   OCR    │     │   Face   │
                                │   AI     │     │          │     │   AI     │
                                └──────────┘     └──────────┘     └──────────┘
                                                                    │
                                                                    ▼
                                                              ┌──────────┐
                                                              │Liveness  │
                                                              └──────────┘

---

🔄 Verification Pipeline

The verification process is designed as a multi-stage pipeline:

Identity Document
       │
       ▼
Document Detection
       │
       ▼
Image Quality Check
       │
       ▼
Perspective Correction
       │
       ▼
OCR
       │
       ▼
Data Extraction & Normalization
       │
       ▼
Data Validation
       │
       ├──────────────────────┐
       │                      │
       ▼                      ▼
Face Detection          Selfie / Face
       │                      │
       └──────────┬───────────┘
                  ▼
           Face Verification
                  │
                  ▼
          Liveness Detection
                  │
                  ▼
       Verification Engine
                  │
                  ▼
          Final Result

The final verification decision should be based on multiple signals rather than face similarity alone.

---

✨ Features

📄 Document Processing

- Identity document detection
- Document cropping
- Perspective correction
- Image quality assessment
- Document classification

🔍 OCR

- Arabic text recognition
- French / Latin text recognition
- Structured field extraction
- Text normalization
- Confidence scoring
- Data validation

👤 Face Verification

- Face detection
- Face embedding
- Face-to-face comparison
- Configurable similarity thresholds

🛡️ Liveness Detection

Designed to reduce presentation attacks such as:

- Printed photographs
- Screen replay
- Static images
- Other spoofing attempts

🔐 Security

Planned security capabilities include:

- JWT authentication
- Role-based access control
- Rate limiting
- Audit logging
- Secure secrets management
- Data retention policies
- Secure biometric data handling

---

🧩 Project Structure

dz-biometric-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── ai/
│   ├── document/
│   ├── ocr/
│   ├── face/
│   ├── liveness/
│   └── ...
│
├── database/
│
├── tests/
│
├── storage/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md

---

🚀 Getting Started

Requirements

Before running the project, make sure you have:

- Docker
- Docker Compose
- Git

Optional for local development:

- Python 3.11+
- PostgreSQL
- Redis

---

📥 Installation

Clone the repository:

git clone https://github.com/cherif1981/dz-biometric-platform.git
cd dz-biometric-platform

Create the environment file:

cp .env.example .env

Review and configure the environment variables before starting the services.

---

🐳 Run with Docker

Validate the Compose configuration:

docker compose config

Build the services:

docker compose build

Start the platform:

docker compose up

Run in detached mode:

docker compose up -d

Check running services:

docker compose ps

View logs:

docker compose logs -f

Stop the platform:

docker compose down

---

🔌 API

The backend is built with FastAPI and is designed to expose a versioned REST API.

Planned API structure:

/api/v1/auth
/api/v1/documents
/api/v1/ocr
/api/v1/face
/api/v1/verification
/api/v1/users
/api/v1/audit

Health Check

GET /health

Example:

{
  "status": "ok"
}

---

🔐 Verification API

The target workflow is:

POST /api/v1/verification

Input:

identity_document
selfie

Example response:

{
  "status": "verified",
  "document": {
    "type": "national_id",
    "fields": {}
  },
  "face": {
    "matched": true,
    "score": 0.94
  },
  "liveness": {
    "passed": true
  }
}

«The API contract is still evolving during MVP development.»

---

🗄️ Data Model

The platform is designed around verification sessions.

Core entities may include:

users
documents
document_extractions
verification_sessions
face_verifications
liveness_checks
audit_logs

A verification session connects the different stages of the process:

User
 │
 └── Verification Session
        │
        ├── Document
        ├── OCR Result
        ├── Face Verification
        ├── Liveness Check
        └── Audit Events

---

🔒 Privacy & Security

Biometric information and identity documents are highly sensitive.

The project therefore aims to follow privacy-by-design principles.

Data minimization

Only information required for the verification process should be collected.

Secure storage

Sensitive data should be encrypted and access-controlled.

Retention

Uploaded identity documents and biometric material should not be retained indefinitely.

A configurable retention policy is planned.

Logging

Logs should never contain:

- Raw identity documents
- Selfie images
- Face embeddings
- Authentication secrets
- Unnecessary personal information

---

🧪 Testing

Run the backend tests with:

pytest

The testing strategy will cover:

Unit Tests
    │
    ├── OCR
    ├── Document Processing
    ├── Face Verification
    └── Validation
         │
         ▼
Integration Tests
         │
         ▼
API Tests
         │
         ▼
End-to-End Tests

---

🛣️ Roadmap

Phase 1 — Infrastructure

- [x] Initial repository structure
- [x] Backend foundation
- [x] PostgreSQL integration
- [x] Docker foundation
- [ ] Resolve and validate Docker Compose configuration
- [ ] Health checks
- [ ] CI/CD

Phase 2 — Document AI

- [ ] Algerian identity document detection
- [ ] Document classification
- [ ] Image quality detection
- [ ] Perspective correction
- [ ] Document cropping

Phase 3 — OCR

- [ ] Arabic OCR
- [ ] French OCR
- [ ] Structured field extraction
- [ ] Confidence scores
- [ ] Field validation
- [ ] Normalization

Phase 4 — Biometrics

- [ ] Face detection
- [ ] Face embeddings
- [ ] Face verification
- [ ] Liveness detection
- [ ] Anti-spoofing evaluation

Phase 5 — Verification Engine

- [ ] Verification sessions
- [ ] Multi-signal verification
- [ ] Verification policies
- [ ] Explainable verification results
- [ ] Audit trail

Phase 6 — Security

- [ ] RBAC
- [ ] Rate limiting
- [ ] Encryption
- [ ] Secure storage
- [ ] Data retention
- [ ] Security testing

Phase 7 — Frontend

- [ ] Authentication
- [ ] Dashboard
- [ ] Document capture
- [ ] Selfie capture
- [ ] Verification status
- [ ] Administration interface

---

🧭 Development Principles

The project follows several principles:

API First

The backend should provide a clean API that can be consumed by web and mobile applications.

Modular AI

OCR, document processing, face verification, and liveness should remain independent components.

Privacy by Design

Privacy and data minimization should be considered from the beginning rather than added later.

Security by Design

Authentication, authorization, auditing, encryption, and secure storage are part of the architecture.

Testable Architecture

Each major component should be independently testable.

---

📊 Project Status

Component| Status
Repository structure| 🟢 Initial
Backend| 🟡 Development
Database| 🟡 Development
Docker| 🟡 Development
Document AI| 🟡 Development
OCR| 🟡 Development
Face Verification| 🟡 Development
Liveness| 🟡 Planned
Frontend| 🟡 Planned
Production Security| 🔴 Not ready
Production Deployment| 🔴 Not ready

---

🤝 Contributing

Contributions, ideas, bug reports, and technical discussions are welcome.

Before submitting a pull request:

1. Create a feature branch.
2. Add or update tests.
3. Keep changes focused.
4. Update the documentation when necessary.
5. Make sure Docker and tests pass.

---

⚖️ Disclaimer

This project is intended for research, development, and experimentation.

It should not be used for production identity verification until the security, privacy, biometric accuracy, liveness detection, legal, and operational requirements have been properly evaluated.

---

📄 License

See the "LICENSE" (LICENSE) file for the applicable license.

---

🇩🇿 Vision

DZ Biometric Platform aims to provide a modular foundation for secure digital identity verification adapted to the Algerian context.

Document
   +
Identity Data
   +
Face
   +
Liveness
   +
Security
        │
        ▼
Trusted Digital Identity Verification