from enum import Enum
from functools import wraps
from typing import Callable


class RiskLevel(Enum):
    SAFE = "SAFE"  # Read-only, no side effects
    WRITE = "WRITE"  # Standard operations (booking, payments)
    CRITICAL = "CRITICAL"  # Clinical/Permanent changes (requires confirmation)


# Global registry to store tool risk levels
TOOL_RISK_REGISTRY = {}


def risk_level(level: RiskLevel):
    """
    Decorator to mark the risk level of an AI tool handler.
    """

    def decorator(func: Callable) -> Callable:
        # Register the tool name (method name)
        tool_name = func.__name__
        TOOL_RISK_REGISTRY[tool_name] = level.value

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_tool_risk(tool_name: str) -> str:
    """Get risk level for a given tool name, default to WRITE."""
    return TOOL_RISK_REGISTRY.get(tool_name, "WRITE")
