
"""
Smart Model Router
Decides which model to use based on query intent and complexity.
"""
from typing import Optional
from ..config import (
    MODEL_CARDS, DEFAULT_MODEL, COMPLEX_MODEL, 
    COMPLEX_KEYWORDS, COMPLEX_TOOLS
)

class SmartModelRouter:
    """
    Routes queries to appropriate models based on complexity.
    """
    
    @classmethod
    def select_model(cls, query: str, tool_name: Optional[str] = None) -> str:
        """
        Selects the best model for the task.
        Criteria:
        1. Tool Complexity (if tool is known)
        2. Query Keywords (semantic complexity)
        3. Length of input (longer = likely more complex)
        """
        
        # 1. Force complex model for specific tools
        if tool_name and tool_name in COMPLEX_TOOLS:
            return COMPLEX_MODEL

        # 2. Check for complexity keywords in user input
        query_lower = query.lower()
        for keyword in COMPLEX_KEYWORDS:
            if keyword in query_lower:
                return COMPLEX_MODEL

        # 3. Check for specific "Command" patterns that need accuracy
        if "detailed" in query_lower or "تفاصيل" in query_lower:
            return COMPLEX_MODEL

        # 4. Long context heuristic
        if len(query.split()) > 30:  # If input is very long
            return COMPLEX_MODEL

        # Default to faster/cheaper model
        return DEFAULT_MODEL
