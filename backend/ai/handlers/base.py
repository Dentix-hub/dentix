from typing import Dict, Any
from sqlalchemy.orm import Session
from ... import models


class BaseHandler:
    """Base class for all AI Tool Handlers."""

    def __init__(self, db: Session, user: models.User):
        self.db = db
        self.user = user
        self.tenant_id = user.tenant_id

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generic execute method to be overridden if needed, or used for common logic."""
        raise NotImplementedError("Subclasses must implement specific tool methods.")
