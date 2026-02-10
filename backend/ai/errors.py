"""
AI System Errors.
Typed exceptions for better error handling and frontend feedback.
"""

from typing import Optional, Dict, Any


class AIException(Exception):
    """Base exception for all AI-related errors."""

    def __init__(
        self,
        message: str,
        code: str = "ai_error",
        debug_info: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.debug_info = debug_info
        super().__init__(self.message)


class AIValidationError(AIException):
    """Input validation failed (e.g. missing required field)."""

    def __init__(
        self,
        message: str,
        code: str = "validation_error",
        debug_info: Optional[Dict] = None,
    ):
        super().__init__(message, code=code, debug_info=debug_info)


class AINotFoundError(AIException):
    """Resource not found (e.g. patient not found)."""

    def __init__(
        self, message: str, code: str = "not_found", debug_info: Optional[Dict] = None
    ):
        super().__init__(message, code=code, debug_info=debug_info)


class AIPermissionError(AIException):
    """User does not have permission to execute this tool."""

    def __init__(
        self,
        message: str = "ليس لديك صلاحية للقيام بهذا الإجراء.",
        debug_info: Optional[Dict] = None,
    ):
        super().__init__(message, code="permission_denied", debug_info=debug_info)


class AIBusinessError(AIException):
    """Business rule violation (e.g. duplicate patient, insufficient funds)."""

    def __init__(
        self,
        message: str,
        code: str = "business_rule_violation",
        debug_info: Optional[Dict] = None,
    ):
        super().__init__(message, code=code, debug_info=debug_info)


class AIExecutionError(AIException):
    """Unexpected error during tool execution (e.g. DB crash, unknown error)."""

    def __init__(
        self,
        message: str,
        original_error: Exception = None,
        code: str = "execution_failed",
        debug_info: Dict = None,
    ):
        if not debug_info and original_error:
            debug_info = {"original_error": str(original_error)}
        super().__init__(message, code=code, debug_info=debug_info)


class AISystemError(AIException):
    """Infrastructure failure (e.g. LLM quota, parsing error, timeouts)."""

    def __init__(self, message: str, debug_info: Optional[Dict] = None):
        super().__init__(message, code="system_error", debug_info=debug_info)
