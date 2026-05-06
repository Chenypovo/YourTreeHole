# tests/test_agent.py
import json
import pytest
from unittest.mock import MagicMock, patch
from core.agent import Agent
from core.llm import LLMResponse
from core.memory import Memory
from core.tools import ToolRegistry, tool
from core.context import ContextManager


@pytest.fixture
def agent(tmp_path):
    llm = MagicMock(spec=["chat"])
    memory = Memory(chroma_path=str(tmp_path / "agent_test"))
    registry = ToolRegistry()
    context = ContextManager(persona="你是一只猫", memory=memory, tool_registry=registry)
    return Agent(llm=llm, memory=memory, tools=registry, context_manager=context)


class TestAgentBasicLoop:
    def test_simple_text_reply(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="喵～你好！", tool_calls=[])

        result = agent.run("你好")

        assert result == "喵～你好！"
        agent.llm.chat.assert_called_once()

    def test_tool_call_then_reply(self, agent, tmp_path):
        # First call: LLM wants to call a tool
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "greet", "arguments": json.dumps({"name": "world"})},
        }

        @tool(name="greet", description="Greet someone")
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        agent.tools.register(greet)

        agent.llm.chat.side_effect = [
            LLMResponse(content="", tool_calls=[tool_call]),   # First: tool call
            LLMResponse(content="喵～已打招呼！", tool_calls=[]),  # Second: final reply
        ]

        result = agent.run("跟world打个招呼")

        assert result == "喵～已打招呼！"
        assert agent.llm.chat.call_count == 2

    def test_conversation_history_stored(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="喵～", tool_calls=[])

        agent.run("你好")

        ctx = agent.memory.get_context()
        assert any(m["content"] == "你好" for m in ctx)
        assert any(m["content"] == "喵～" for m in ctx)


class TestAgentLoopSafety:
    def test_max_iterations_stops_loop(self, agent):
        # LLM always returns a tool call — would loop forever
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "greet", "arguments": json.dumps({"name": "loop"})},
        }

        @tool(name="greet", description="Greet")
        def greet(name: str) -> str:
            return f"Hi, {name}"

        agent.tools.register(greet)
        agent.llm.chat.return_value = LLMResponse(content="", tool_calls=[tool_call])

        result = agent.run("test")

        # Should stop after max iterations and return something
        assert isinstance(result, str)
        assert agent.llm.chat.call_count == 10  # default max_iterations

    def test_tool_error_handled_gracefully(self, agent):
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "boom", "arguments": "{}"},
        }

        @tool(name="boom", description="Always fails")
        def boom():
            raise RuntimeError("kaboom")

        agent.tools.register(boom)

        agent.llm.chat.side_effect = [
            LLMResponse(content="", tool_calls=[tool_call]),
            LLMResponse(content="工具出错了喵", tool_calls=[]),
        ]

        result = agent.run("执行boom")
        assert result == "工具出错了喵"
