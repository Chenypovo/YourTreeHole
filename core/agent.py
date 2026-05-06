# core/agent.py
from __future__ import annotations

import json
from collections.abc import Generator

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
    ):
        self.llm = llm
        self.memory = memory
        self.tools = tools
        self.context_manager = context_manager
        self.max_iterations = max_iterations

    def run(self, user_input: str) -> str:
        """Run one conversation turn using the ReAct loop."""
        self.memory.add_message("user", user_input)
        messages = self.context_manager.build(user_input)
        tool_schemas = self.tools.get_schemas() or None

        response = None
        for _ in range(self.max_iterations):
            response = self.llm.chat(messages=messages, tools=tool_schemas)

            if not response.has_tool_calls:
                self.memory.add_message("assistant", response.content)
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
        self.memory.add_message("user", user_input)
        messages = self.context_manager.build(user_input)
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
        yield ("", None)


# For type hint in run_stream
from typing import Any
