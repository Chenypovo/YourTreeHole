# tests/test_integration.py
"""Integration test: full agent loop with mocked LLM."""
import json
import pytest
from unittest.mock import MagicMock

from core.agent import Agent
from core.llm import LLMResponse
from core.memory import Memory
from core.tools import ToolRegistry, tool
from core.context import ContextManager


def test_full_agent_loop_with_tool_call(tmp_path):
    """Test a complete user->agent->tool->agent->user cycle."""
    # Setup
    llm = MagicMock()
    memory = Memory(chroma_path=str(tmp_path / "integration"))
    registry = ToolRegistry()

    @tool(name="calculator", description="Calculate math")
    def calculator(expression: str) -> str:
        return str(eval(expression))  # safe in test

    registry.register(calculator)

    context = ContextManager(
        persona="你是一只猫",
        memory=memory,
        tool_registry=registry,
    )

    agent = Agent(llm=llm, memory=memory, tools=registry, context_manager=context)

    # LLM first calls tool, then replies
    llm.chat.side_effect = [
        LLMResponse(content="", tool_calls=[{
            "id": "call_1",
            "name": "calculator",
            "arguments": json.dumps({"expression": "2+3"}),
        }]),
        LLMResponse(content="2+3=5喵！", tool_calls=[]),
    ]

    result = agent.run("2+3等于多少")

    assert result == "2+3=5喵！"
    assert llm.chat.call_count == 2

    # Verify history stored
    ctx = memory.get_context()
    assert any("2+3" in m["content"] for m in ctx)
    assert any("5喵" in m["content"] for m in ctx)
