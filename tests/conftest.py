"""Pytest configuration and shared fixtures."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def app():
    """Create FastAPI test application."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["ENVIRONMENT"] = "testing"

    from src.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_id_image():
    """Return sample ID image bytes."""
    import io
    from PIL import Image

    img = Image.new("RGB", (400, 300), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def sample_selfie():
    """Return sample selfie image bytes."""
    import io
    from PIL import Image

    img = Image.new("RGB", (300, 300), color=(200, 200, 220))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()
