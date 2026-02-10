"""
Standardized API Response Helpers.
Ensures consistent response format across all endpoints.
"""

from fastapi.responses import JSONResponse
from typing import Any, Optional


def success_response(
    data: Any = None,
    message: str = "OK",
    status_code: int = 200,
) -> JSONResponse:
    """Return a standardized success response."""
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "data": data, "message": message},
    )


def error_response(
    message: str = "Error",
    status_code: int = 400,
    details: Any = None,
) -> JSONResponse:
    """Return a standardized error response."""
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
) -> JSONResponse:
    """Return a standardized paginated response."""
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": data,
            "message": message,
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page,
            },
        },
    )
