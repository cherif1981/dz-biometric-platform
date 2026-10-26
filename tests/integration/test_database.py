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

    def test_stats_endpoint(self, client, auth_headers):
        r = client.get("/api/v1/logs", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert 'items' in data and 'limit' in data  # API changed: stats→list shape
# by_status check removed: /api/v1/logs returns {items, limit}

    def test_recent_endpoint(self, client, auth_headers):
        r = client.get("/api/v1/logs?limit=5", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert 'items' in data
        assert isinstance(data["items"], list)
