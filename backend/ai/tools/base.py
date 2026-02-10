"""
Base Tool Definitions
"""

from pydantic import BaseModel
from typing import Optional, List, Callable, Any, Dict


class ToolDefinition(BaseModel):
    """Schema for tool parameters."""

    pass


class Tool:
    """
    Represents a registered tool that the AI can invoke.
    Enforces strict typing and role-based access.
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, str],
        complexity: str = "simple",
        allowed_roles: Optional[List[str]] = None,
        handler: Optional[Callable] = None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.complexity = complexity
        self.allowed_roles = allowed_roles or [
            "doctor",
            "admin",
            "super_admin",
        ]  # Default roles
        self.handler = handler

    def to_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI/Groq function schema format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {"type": "string", "description": v}
                        for k, v in self.parameters.items()
                    },
                    "required": list(self.parameters.keys()),
                },
            },
        }

    def __repr__(self):
        return f"<Tool {self.name} ({self.complexity})>"
