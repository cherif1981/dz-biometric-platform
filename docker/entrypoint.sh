#!/usr/bin/env bash
set -e
echo "[entrypoint] starting DZ Biometric Platform..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS:-2}"