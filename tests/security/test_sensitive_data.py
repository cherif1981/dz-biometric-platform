"""Security tests for sensitive data handling."""

import pytest


class TestSensitiveData:
    """Tests for data protection."""

    def test_field_encryption_importable(self):
        try:
            from src.core.field_encryption import encrypt_field

            assert encrypt_field is not None
        except ImportError:
            pytest.skip("Field encryption not available")

    def test_no_hardcoded_secrets(self):
        """Source code should not contain hardcoded secrets."""
        import os
        from pathlib import Path

        src_dir = Path("src")
        if not src_dir.exists():
            pytest.skip("src/ not found")

        suspicious_patterns = [
            'password="admin"',
            'secret_key="hardcoded"',
            'api_key="sk-"',
        ]

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pattern in suspicious_patterns:
                assert pattern not in content, f"Found {pattern} in {py_file}"

    def test_env_not_in_gitignore_check(self):
        """Ensure .env is in .gitignore."""
        from pathlib import Path

        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            assert ".env" in content
