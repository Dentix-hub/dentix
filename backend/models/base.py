"""
SQLAlchemy Models Base Facade
Exports common SQLAlchemy types used by all models to avoid repetitive imports.

SQLAlchemy 2.0 style: uses Mapped[] + mapped_column instead of Column.
"""
from backend.database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Enum,
    Date,
    Time,
    JSON,
    BigInteger,
    Numeric,
    func,
    Index,
    UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, date, time, timedelta, timezone

__all__ = [
    "Base",
    "Column",
    "Integer",
    "String",
    "Boolean",
    "DateTime",
    "Float",
    "Text",
    "ForeignKey",
    "Enum",
    "Date",
    "Time",
    "JSON",
    "BigInteger",
    "Numeric",
    "func",
    "Index",
    "UniqueConstraint",
    "relationship",
    "Mapped",
    "mapped_column",
    "datetime",
    "timezone"
]
