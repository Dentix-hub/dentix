"""
Input Validators & Tool Security
Enforces strict checks on tool parameters and context.
"""

import re
from typing import Dict, Any


class ValidationError(Exception):
    pass


def validate_tool_access(tool: Any, user_role: str):
    """Ensure user has permission to use this tool."""
    if not tool.allowed_roles:
        return True  # Open tool

    if user_role not in tool.allowed_roles:
        raise ValidationError(
            f"Permission invalid for tool '{tool.name}'. Required: {tool.allowed_roles}"
        )


def sanitize_text(text: str) -> str:
    """Remove potential injection vectors from inputs."""
    # Basic removal of control chars and weird unicode
    if not text:
        return ""
    return re.sub(r"[^\w\s\u0600-\u06FF.,!?-]", "", text)


def validate_parameters(tool_name: str, params: Dict[str, Any]):
    """
    Validate parameters against tool definition.
    This acts as a second line of defense content guardrail.
    """
    # 1. Check for missing required parameters (implicit in tool def)
    # This logic can be expanded with specific schemas per tool

    # 2. Specific field validations
    if "amount" in params or "cost" in params:
        # Ensure numeric values are actually numeric
        for field in ["amount", "cost", "paid_amount"]:
            if field in params and params[field]:
                val = str(params[field]).replace(",", "")
                # Extract numbers if mixed with text (e.g. "1200 LE")
                num_match = re.search(r"\d+(\.\d+)?", val)
                if not num_match:
                    raise ValidationError(
                        f"Invalid numeric value for field '{field}': {params[field]}"
                    )

    if "patient_name" in params:
        name = params["patient_name"]
        if not name or len(name.strip()) < 2:
            raise ValidationError("Patient name is too short or empty.")

    return True
