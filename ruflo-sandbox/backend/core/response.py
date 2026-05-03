"""
Standardized API Response Helpers.
Ensures consistent response format across all endpoints.
"""

from fastapi.responses import JSONResponse
from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = "OK"

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    message: str = "OK"
    pagination: PaginationMeta

def success_response(
    data: Any = None,
    message: str = "OK",
    status_code: int = 200,
) -> dict:
    """Return a standardized success response dictionary compatible with StandardResponse."""
    return {"success": True, "data": data, "message": message}

def error_response(
    message: str = "Error",
    status_code: int = 400,
    details: Any = None,
) -> JSONResponse:
    """Return a standardized error response. JSONResponse is fine here since standard error models are handled globally."""
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": details, "message": message},
    )

def paginated_response(
    data: list,
    total: int,
    page: int = 1,
    per_page: int = 20,
    message: str = "OK",
) -> dict:
    """Return a standardized paginated response dictionary compatible with PaginatedResponse."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        },
    }
