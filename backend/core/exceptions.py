"""
Unified Exception Handling for Smart Clinic Management System.

This module provides:
- Custom exception classes for all error types
- Unified error response format
- Exception handler functions for FastAPI
- Logging integration

Usage in routers:
    from backend.core.exceptions import ValidationException, ResourceNotFoundException
    
    if not patient:
        raise ResourceNotFoundException("Patient", patient_id)
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime, timezone
import uuid
import logging
import traceback

logger = logging.getLogger(__name__)


# ============================================
# ERROR RESPONSE MODEL
# ============================================

class ErrorResponse(BaseModel):
    """Standardized error response format."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    trace_id: str
    timestamp: str
    path: Optional[str] = None


class ErrorEnvelope(BaseModel):
    """Error response envelope."""
    error: ErrorResponse


# ============================================
# CUSTOM EXCEPTION CLASSES
# ============================================

class BaseAppException(Exception):
    """
    Base exception for all application errors.
    
    Attributes:
        code: Error code (e.g., "VALIDATION_ERROR")
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
    """
    
    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(BaseAppException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, **(details or {})}
        )


class DatabaseException(BaseAppException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class AuthenticationException(BaseAppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationException(BaseAppException):
    """Raised when user lacks permission."""
    
    def __init__(self, message: str = "Access denied", required_role: Optional[str] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details={"required_role": required_role} if required_role else None
        )


class ResourceNotFoundException(BaseAppException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            code="NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class RateLimitException(BaseAppException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after}
        )


class ExternalServiceException(BaseAppException):
    """Raised when external service call fails."""
    
    def __init__(self, service_name: str, message: str = "External service error"):
        super().__init__(
            message=f"{service_name}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service_name}
        )


class AIServiceException(BaseAppException):
    """Raised when AI service operations fail."""
    
    def __init__(self, message: str = "AI service error", operation: Optional[str] = None):
        super().__init__(
            message=message,
            code="AI_SERVICE_ERROR",
            status_code=503,
            details={"operation": operation} if operation else None
        )


class TenantException(BaseAppException):
    """Raised for tenant-related errors (isolation violations, etc.)."""
    
    def __init__(self, message: str = "Tenant operation error"):
        super().__init__(
            message=message,
            code="TENANT_ERROR",
            status_code=403
        )


class ConflictException(BaseAppException):
    """Raised when resource conflict occurs (duplicate, etc.)."""
    
    def __init__(self, message: str, resource_type: Optional[str] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details={"resource_type": resource_type} if resource_type else None
        )


class BusinessRuleException(BaseAppException):
    """Raised when business logic rule is violated."""
    
    def __init__(self, message: str, rule: Optional[str] = None):
        super().__init__(
            message=message,
            code="BUSINESS_RULE_VIOLATION",
            status_code=400,
            details={"rule": rule} if rule else None
        )


# ============================================
# EXCEPTION HANDLERS
# ============================================

def create_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Optional[Dict] = None
) -> JSONResponse:
    """Create standardized error response."""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    
    error_response = ErrorEnvelope(
        error=ErrorResponse(
            code=code,
            message=message,
            details=details,
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            path=str(request.url.path)
        )
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


async def handle_app_exception(request: Request, exc: BaseAppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        f"Application error: {exc.code} - {exc.message}",
        extra={
            "trace_id": getattr(request.state, "trace_id", None),
            "code": exc.code,
            "path": request.url.path
        }
    )
    
    return create_error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details
    )


async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    
    # Format errors for response
    formatted_errors = []
    for err in errors:
        field = ".".join(str(loc) for loc in err.get("loc", []))
        formatted_errors.append({
            "field": field,
            "message": err.get("msg", "Validation error"),
            "type": err.get("type", "unknown")
        })
    
    logger.info(
        f"Validation error on {request.url.path}",
        extra={"errors": formatted_errors}
    )
    
    return create_error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": formatted_errors}
    )


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    message = "HTTP Error"
    details = None

    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", message)
        details = exc.detail
    else:
        message = str(exc.detail) if exc.detail else message

    return create_error_response(
        request=request,
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=message,
        details=details
    )


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    
    # Log full traceback for debugging
    logger.error(
        f"Unexpected error: {type(exc).__name__}: {exc}",
        extra={
            "trace_id": trace_id,
            "path": request.url.path,
            "traceback": traceback.format_exc()
        }
    )
    
    # Don't expose internal details to user
    return create_error_response(
        request=request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        details={"trace_id": trace_id}
    )


# ============================================
# REGISTRATION FUNCTION
# ============================================

def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app.
    
    Usage in main.py:
        from backend.core.exceptions import register_exception_handlers
        register_exception_handlers(app)
    """
    app.add_exception_handler(BaseAppException, handle_app_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_exception)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_generic_exception)
    
    logger.info("Exception handlers registered")
