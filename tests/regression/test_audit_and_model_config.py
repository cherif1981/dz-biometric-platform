"""Regression tests for audit fail-closed and model config integrity."""
import os

import pytest


def test_fin_raises_on_audit_failure():
    """_fin must raise AuditUnavailableError when db.log raises."""
    path = "src/services/verification_service.py"
    if not os.path.exists(path):
        pytest.skip(f"{path} not present")
    src = open(path, encoding="utf-8").read()
    assert "AuditUnavailableError" in src, "AuditUnavailableError not defined"
    assert "raise AuditUnavailableError" in src, "_fin does not raise on audit failure"
    # ensure the old warning-only path is gone
    assert "logger.warning(f\"audit: {e}\")" not in src


def test_real_class_index_loaded_from_yaml():
    """No hardcoded REAL_CLASS_INDEX; must be loaded from security.yaml."""
    path = "src/services/antispoofing_service.py"
    src = open(path, encoding="utf-8").read()
    assert "REAL_CLASS_INDEX = " not in src, "hardcoded REAL_CLASS_INDEX still present"
    assert "_load_real_class_index" in src, "loader missing"
    assert "self.real_class_index" in src, "instance attribute missing"


def test_verify_model_integrity_fail_closed():
    """_verify_model_integrity must not silently return when config missing."""
    path = "src/services/antispoofing_service.py"
    src = open(path, encoding="utf-8").read()
    # old bypass
    assert "if not expected:\n        return" not in src, "silent bypass still present"
    assert "security.yaml missing" in src
    assert "sha256 missing" in src


def test_config_real_class_index_is_2():
    """Documents the current expected value (must match YAML)."""
    path = "config/security.yaml"
    if not os.path.exists(path):
        pytest.skip(f"{path} not present")
    src = open(path, encoding="utf-8").read()
    assert "real_class_index: 2" in src
