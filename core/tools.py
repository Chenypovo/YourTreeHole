# core/tools.py
from __future__ import annotations

import inspect
import traceback
from typing import Any, Callable


def tool(name: str, description: str) -> Callable:
    """Decorator that marks a function as a tool with metadata."""
    def decorator(func: Callable) -> Callable:
        func._tool_name = name
        func._tool_description = description
        return func
    return decorator


def _build_schema(func: Callable) -> dict[str, Any]:
    """Generate OpenAI function calling JSON schema from type annotations."""
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}

    for param_name, param in sig.parameters.items():
        if param.annotation is inspect.Parameter.empty:
            prop_type = "string"
        else:
            prop_type = type_map.get(param.annotation, "string")

        # Extract description from docstring or parameter name
        param_desc = param_name
        if func.__doc__:
            # Try to find parameter description in docstring
            for line in func.__doc__.split("\n"):
                stripped = line.strip()
                if stripped.startswith(":param ") and param_name in stripped:
                    param_desc = stripped.split(":", 2)[-1].strip()
                    break

        properties[param_name] = {"type": prop_type, "description": param_desc}

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": func._tool_name,
            "description": func._tool_description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict[str, Any]] = []

    def register(self, func: Callable) -> None:
        """Register a @tool-decorated function."""
        self._tools[func._tool_name] = func
        self._schemas.append(_build_schema(func))

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI tool calling format schemas."""
        return list(self._schemas)

    def execute(self, name: str, args: dict[str, Any]) -> str:
        """Execute a tool by name. Returns result string or error message."""
        if name not in self._tools:
            return f"Error: Tool '{name}' not found."

        try:
            result = self._tools[name](**args)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {e}\n{traceback.format_exc()}"
