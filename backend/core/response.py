"""
Standardized API Response Helpers.
Ensures consistent response format across all endpoints.
"""

from fastapi.responses import JSONResponse
from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel
from backend.core.logging import get_trace_id

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = "OK"
    trace_id: Optional[str] = None

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int

class CursorPaginationMeta(BaseModel):
    next_cursor: Optional[str] = None
    has_more: bool = False
    limit: int

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    message: str = "OK"
    pagination: PaginationMeta
    trace_id: Optional[str] = None

class CursorPaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    message: str = "OK"
    pagination: CursorPaginationMeta
    trace_id: Optional[str] = None

def success_response(
    data: Any = None,
    message: str = "OK",
    status_code: int = 200,
) -> dict:
    """Return a standardized success response dictionary compatible with StandardResponse."""
    return {"success": True, "data": data, "message": message, "trace_id": get_trace_id()}

def error_response(
    message: str = "Error",
    status_code: int = 400,
    details: Any = None,
) -> JSONResponse:
    """Return a standardized error response. JSONResponse is fine here since standard error models are handled globally."""
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": details, "message": message, "trace_id": get_trace_id()},
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
        "trace_id": get_trace_id()
    }

def cursor_paginated_response(
    data: list,
    limit: int,
    next_cursor: Optional[str] = None,
    has_more: bool = False,
    message: str = "OK",
) -> dict:
    """Return a standardized cursor paginated response dictionary compatible with CursorPaginatedResponse."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "pagination": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "limit": limit,
        },
        "trace_id": get_trace_id()
    }
