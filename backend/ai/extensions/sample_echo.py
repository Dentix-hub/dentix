from typing import Dict, Any
from backend.ai.tools.base import Tool

async def echo_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """Simple echo handler."""
    message = params.get("message", "No message provided")
    return {
        "success": True,
        "message": f"Echo: {message}",
        "original_params": params
    }

# Tool Definition
echo_tool = Tool(
    name="echo_test",
    description="A test tool that echoes the input message.",
    parameters={"message": "The text to echo back"},
    complexity="simple",
    allowed_roles=["doctor", "admin"],
    handler=echo_handler
)

# Export for discovery
TOOLS = [echo_tool]
