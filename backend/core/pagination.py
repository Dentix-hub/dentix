"""
Cursor Pagination Infrastructure
"""

import base64
import json
from typing import Optional, Any, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query
from sqlalchemy import desc

class CursorParams(BaseModel):
    cursor: Optional[str] = Field(None, description="Cursor for pagination")
    limit: int = Field(20, ge=1, le=100, description="Number of items to return")

def encode_cursor(data: dict) -> str:
    """Encode a dictionary to a base64 string cursor."""
    json_str = json.dumps(data)
    return base64.urlsafe_b64encode(json_str.encode()).decode('utf-8')

def decode_cursor(cursor: str) -> Optional[dict]:
    """Decode a base64 string cursor back to a dictionary."""
    if not cursor:
        return None
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode('utf-8')
        return json.loads(json_str)
    except Exception:
        return None

def apply_cursor_pagination(
    query: Query,
    model: Any,
    cursor_params: CursorParams,
    sort_column_name: str = "id",
    descending: bool = True
) -> Tuple[Query, Optional[str], bool]:
    """
    Apply cursor pagination to an SQLAlchemy query.

    Args:
        query: SQLAlchemy Query object
        model: SQLAlchemy model class
        cursor_params: CursorParams object containing limit and cursor
        sort_column_name: Name of the column to sort and paginate by
        descending: Whether to sort descending

    Returns:
        Tuple of (paginated_query, next_cursor, has_more)
    """
    sort_column = getattr(model, sort_column_name)

    # 1. Apply sort
    if descending:
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # 2. Apply cursor filter
    decoded_cursor = decode_cursor(cursor_params.cursor)
    if decoded_cursor and sort_column_name in decoded_cursor:
        cursor_val = decoded_cursor[sort_column_name]
        if descending:
            query = query.filter(sort_column < cursor_val)
        else:
            query = query.filter(sort_column > cursor_val)

    # 3. Apply limit (+1 to check if there are more)
    # limit + 1 allows us to determine has_more
    query = query.limit(cursor_params.limit + 1)

    return query

def build_cursor_response(items: list, limit: int, sort_column_name: str = "id") -> Tuple[list, Optional[str], bool]:
    """
    Given a list of items fetched with limit + 1, return the items, next_cursor, and has_more flag.
    """
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = None
    if items:
        last_item = items[-1]
        # Handle both dicts and ORM objects
        val = getattr(last_item, sort_column_name, None) if not isinstance(last_item, dict) else last_item.get(sort_column_name)

        # Datetime serialization helper
        if hasattr(val, "isoformat"):
            val = val.isoformat()

        if val is not None:
            next_cursor = encode_cursor({sort_column_name: val})

    return items, next_cursor, has_more
