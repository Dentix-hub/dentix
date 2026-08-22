import importlib
import logging
import sys


def test_audit_logger_import_does_not_require_a_writable_log_file(monkeypatch):
    """Production startup must not depend on writing beside application code."""

    def reject_file_handler(*args, **kwargs):
        raise PermissionError("application directory is read-only")

    monkeypatch.setattr(logging, "FileHandler", reject_file_handler)
    sys.modules.pop("backend.utils.audit_logger", None)

    audit_logger = importlib.import_module("backend.utils.audit_logger")

    assert audit_logger.logger.name == "smart_clinic"
