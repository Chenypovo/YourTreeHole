# core/agent.py
from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from core.context import ContextManager
from core.llm import LLMClient, LLMResponse
from core.memory import Memory
from core.tools import ToolRegistry


class Agent:
    """ReAct (Reason-Act-Observe) loop agent.

    Orchestrates: receive user input -> build context -> call LLM ->
    if tool calls, execute tools and loop -> if text reply, store and return.
    """

    def __init__(
        self,
        llm: LLMClient,
        memory: Memory,
        tools: ToolRegistry,
        context_manager: ContextManager,
        max_iterations: int = 10,
        enable_memory_gating: bool = False,
    ):
        self.llm = llm
        self.memory = memory
        self.tools = tools
        self.context_manager = context_manager
        self.max_iterations = max_iterations
        self.enable_memory_gating = enable_memory_gating

    def run(self, user_input: str) -> str:
        """Run one conversation turn using the ReAct loop."""
        messages = self.context_manager.build(user_input)
        self.memory.add_message("user", user_input)
        tool_schemas = self.tools.get_schemas() or None

        response = None
        for _ in range(self.max_iterations):
            response = self.llm.chat(messages=messages, tools=tool_schemas)

            if not response.has_tool_calls:
                self.memory.add_message("assistant", response.content)
                self._maybe_save_long_term(user_input, response.content)
                return response.content

            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            })

            for tc in response.tool_calls:
                func = tc["function"]
                args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                result = self.tools.execute(func["name"], args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        if response and response.content:
            return response.content
        return "抱歉，我处理这个请求时遇到了困难喵。"

    def run_stream(self, user_input: str) -> Generator[tuple[str, str | None], None, None]:
        """Run one turn with streaming. Yields (token, tool_name) tuples.
        tool_name is set when a tool is being executed, None for normal tokens.
        """
        messages = self.context_manager.build(user_input)
        self.memory.add_message("user", user_input)
        tool_schemas = self.tools.get_schemas() or None

        response = None
        for _ in range(self.max_iterations):
            full_content = ""
            tool_calls_map: dict[int, dict[str, Any]] = {}

            for token, final in self.llm.chat_stream(messages=messages, tools=tool_schemas):
                if token:
                    full_content += token
                    yield (token, None)
                if final:
                    response = final

            if not response or not response.has_tool_calls:
                if response:
                    self.memory.add_message("assistant", response.content)
                    self._maybe_save_long_term(user_input, response.content)
                yield ("", None)  # signal done
                return

            # Process tool calls
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            })

            for tc in response.tool_calls:
                func = tc["function"]
                args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                tool_name = func["name"]
                yield ("\n", tool_name)  # signal tool execution
                result = self.tools.execute(tool_name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        if response and response.content:
            self.memory.add_message("assistant", response.content)
            self._maybe_save_long_term(user_input, response.content)
        yield ("", None)

    def _maybe_save_long_term(self, user_input: str, assistant_output: str) -> None:
        """Ask the LLM whether this turn contains stable long-term memory worth saving."""
        if not self.enable_memory_gating:
            return
        if not user_input.strip() and not assistant_output.strip():
            return

        messages = [
            {
                "role": "system",
                "content": (
                    "You decide whether a conversation turn contains durable user memory worth saving.\n"
                    "Only save stable facts such as user preferences, identity, ongoing projects, goals, or recurring constraints.\n"
                    "Do not save temporary requests, one-off questions, tool outputs, or assistant-only phrasing.\n"
                    "Return strict JSON only with keys: should_save (boolean), memory (string), category (string)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User message:\n{user_input}\n\n"
                    f"Assistant reply:\n{assistant_output}\n\n"
                    "Decide whether to save one concise memory about the user."
                ),
            },
        ]

        try:
            decision = self.llm.chat(messages=messages, tools=None)
            payload = _parse_json_object(decision.content)
        except Exception:
            return

        if not payload.get("should_save"):
            return

        memory_text = str(payload.get("memory", "")).strip()
        if not memory_text:
            return

        metadata = {
            "source": "llm_gate",
            "category": str(payload.get("category", "general")).strip() or "general",
        }
        self.memory.save_long_term(memory_text, metadata)


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from plain text or fenced code output."""
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 3:
            raw = "\n".join(lines[1:-1]).strip()
    return json.loads(raw)

