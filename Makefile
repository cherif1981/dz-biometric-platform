.PHONY: help install dev test lint format clean run docker-build docker-up docker-down

help:
	@echo "DZ Biometric Platform - Available commands:"
	@echo "  make install      Install production dependencies"
	@echo "  make dev          Install development dependencies"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linters (ruff)"
	@echo "  make format       Format code (black)"
	@echo "  make clean        Clean temporary files"
	@echo "  make run          Run the FastAPI server"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-up    Start docker-compose"
	@echo "  make docker-down  Stop docker-compose"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-security:
	pytest tests/security/ -v

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ 2>/dev/null || true

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t dz-biometric-platform:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"
