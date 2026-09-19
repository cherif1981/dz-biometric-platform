"""Shared pytest fixtures for all tests."""
import os
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure sub-packages are importable
for sub in ("backend", "ai"):
    p = ROOT / sub
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def sample_card_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_card.jpg"


@pytest.fixture(scope="session")
def sample_selfie_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_selfie.jpg"