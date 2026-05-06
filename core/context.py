# core/context.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.memory import Memory
from core.tools import ToolRegistry


class ContextManager:
    """Assembles the full message list for LLM calls."""

    def __init__(
        self,
        persona: str,
        memory: Memory,
        tool_registry: ToolRegistry,
    ):
        self._persona = persona
        self._memory = memory
        self._tool_registry = tool_registry

    @property
    def memory(self) -> Memory:
        """Public read-only access to the memory instance."""
        return self._memory

    @classmethod
    def from_file(
        cls,
        persona_path: str,
        memory: Memory,
        tool_registry: ToolRegistry,
    ) -> ContextManager:
        """Create ContextManager with persona loaded from a markdown file."""
        persona = Path(persona_path).read_text(encoding="utf-8").strip()
        return cls(persona=persona, memory=memory, tool_registry=tool_registry)

    def build(self, user_input: str) -> list[dict[str, str]]:
        """Build the full message list for an LLM call.

        Structure:
        1. System prompt (persona + long-term memory recall)
        2. Short-term conversation history
        3. Current user message
        """
        system_prompt = self._build_system_prompt()

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        # Add short-term conversation history
        history = self._memory.get_context(max_tokens=3000)
        messages.extend(history)

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        return messages

    def _build_system_prompt(self) -> str:
        """Build system prompt: persona + long-term memory."""
        parts = [self._persona]

        # Recall relevant long-term memories (use persona as query for general context)
        memories = self._memory.recall(self._persona, top_k=5)
        if memories:
            parts.append("\n\n## 关于用户的记忆:")
            for mem in memories:
                parts.append(f"- {mem}")

        return "\n".join(parts)
