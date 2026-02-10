from backend.database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Text,
    Date,
    ForeignKey,
    Index,
    JSON,
    func
)
from sqlalchemy.orm import relationship
from datetime import datetime
