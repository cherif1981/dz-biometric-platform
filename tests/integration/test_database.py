"""Integration tests for audit database."""
import os
import pytest
from pathlib import Path


class TestAuditDB:
    """Tests for AuditDB."""

    def test_audit_db_import(self):
        try:
            from src.services.audit_db import AuditDB
            assert AuditDB is not None
        except ImportError:
            pytest.skip("AuditDB not available")

    def test_audit_db_init(self, tmp_path):
        from src.services.audit_db import AuditDB
        db = AuditDB()
        assert db is not None

    def test_stats_endpoint(self, client):
        r = client.get("/audit/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "by_status" in data

    def test_recent_endpoint(self, client):
        r = client.get("/audit/recent?limit=5")
        assert r.status_code == 200
        data = r.json()
        assert "records" in data
        assert isinstance(data["records"], list)
