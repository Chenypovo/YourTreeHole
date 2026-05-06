# core/agent.py
from __future__ import annotations

import json

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
        # Store user message in short-term memory
        self.memory.add_message("user", user_input)

        # Build initial context
        messages = self.context_manager.build(user_input)

        tool_schemas = self.tools.get_schemas() or None

        response = None
        for _ in range(self.max_iterations):
            response = self.llm.chat(
                messages=messages,
                tools=tool_schemas,
            )

            if not response.has_tool_calls:
                # Final reply — store and return
                self.memory.add_message("assistant", response.content)
                return response.content

            # Process tool calls
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            })

            for tc in response.tool_calls:
                args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                result = self.tools.execute(tc["name"], args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        # Hit max iterations
        if response and response.content:
            return response.content
        return "抱歉，我处理这个请求时遇到了困难喵。"
