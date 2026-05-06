# core/context.py
from __future__ import annotations

import os
from typing import Any

from core.memory import Memory
from core.tools import ToolRegistry


class ContextManager:
    """Assembles the full message list for LLM calls."""

    def __init__(
        self,
        persona: str = "",
        memory: Memory | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self.persona = persona
        self.memory = memory
        self.tool_registry = tool_registry

    @classmethod
    def from_file(
        cls,
        persona_path: str,
        memory: Memory | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> ContextManager:
        """Create a ContextManager with persona loaded from a file."""
        with open(persona_path, "r", encoding="utf-8") as f:
            persona = f.read().strip()
        return cls(persona=persona, memory=memory, tool_registry=tool_registry)

    def build(self, user_input: str) -> list[dict[str, Any]]:
        """Build the full message list for an LLM call.

        Structure:
        1. System prompt (persona + long-term memory recall)
        2. Short-term conversation history
        3. Current user message
        """
        messages: list[dict[str, Any]] = []

        # Build system prompt
        system_parts: list[str] = []
        if self.persona:
            system_parts.append(self.persona)

        # Add long-term memory recall if memory is available
        if self.memory:
            memories = self.memory.recall(user_input)
            if memories:
                memory_text = "\n".join(f"- {m}" for m in memories)
                system_parts.append(f"\n长期记忆:\n{memory_text}")

        if system_parts:
            messages.append({"role": "system", "content": "\n".join(system_parts)})

        # Add short-term conversation history
        if self.memory:
            history = self.memory.get_context()
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_input})

        return messages
