"""
AI Tool Registry
Manages valid tools and handles lookup.
"""

import logging
from typing import Dict, List, Optional
from .base import Tool
from .definitions import register_default_tools

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Extensible registry for AI tools.
    Add new tools here to expand the agent's capabilities.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        # Auto-register defaults on init
        register_default_tools(self)
        self.discover_extensions()

    def discover_extensions(self):
        """Auto-discover tools from backend/ai/extensions/*.py"""
        import os
        import importlib.util

        ext_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "extensions")
        if not os.path.exists(ext_dir):
            return

        for filename in os.listdir(ext_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    module_name = f"backend.ai.extensions.{filename[:-3]}"
                    spec = importlib.util.spec_from_file_location(
                        module_name, os.path.join(ext_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Look for 'tools' list in module
                    if hasattr(module, "TOOLS"):
                        for tool in module.TOOLS:
                            if isinstance(tool, Tool):
                                logger.info("[EXTENSION] Loaded tool: %s from %s", tool.name, filename)
                                self.register(tool)
                except Exception as e:
                    logger.warning("[EXTENSION] Failed to load %s: %s", filename, e)

    def register(self, tool: Tool):
        """Register a new tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())


# Global registry instance
tool_registry = ToolRegistry()
