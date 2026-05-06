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

    def test_current_user_message_sent_once(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="喵～", tool_calls=[])

        agent.run("你好")

        sent_messages = agent.llm.chat.call_args.kwargs["messages"]
        user_messages = [m for m in sent_messages if m["role"] == "user" and m["content"] == "你好"]
        assert len(user_messages) == 1

    def test_memory_gating_saves_stable_user_fact(self, tmp_path):
        llm = MagicMock(spec=["chat"])
        memory = Memory(chroma_path=str(tmp_path / "agent_memory_gate"))
        registry = ToolRegistry()
        context = ContextManager(persona="你是一只猫", memory=memory, tool_registry=registry)
        agent = Agent(
            llm=llm,
            memory=memory,
            tools=registry,
            context_manager=context,
            enable_memory_gating=True,
        )

        llm.chat.side_effect = [
            LLMResponse(content="我记住啦，以后会优先考虑暗色主题。", tool_calls=[]),
            LLMResponse(
                content='{"should_save": true, "memory": "用户偏好暗色主题", "category": "preference"}',
                tool_calls=[],
            ),
        ]

        result = agent.run("我喜欢暗色主题")

        assert "暗色主题" in result
        recalled = memory.recall("用户喜欢什么主题", top_k=3)
        assert any("暗色主题" in item for item in recalled)
        assert llm.chat.call_count == 2

    def test_memory_gating_skips_transient_request(self, tmp_path):
        llm = MagicMock(spec=["chat"])
        memory = Memory(chroma_path=str(tmp_path / "agent_memory_skip"))
        registry = ToolRegistry()
        context = ContextManager(persona="你是一只猫", memory=memory, tool_registry=registry)
        agent = Agent(
            llm=llm,
            memory=memory,
            tools=registry,
            context_manager=context,
            enable_memory_gating=True,
        )

        llm.chat.side_effect = [
            LLMResponse(content="README 在项目根目录。", tool_calls=[]),
            LLMResponse(
                content='{"should_save": false, "memory": "", "category": "transient"}',
                tool_calls=[],
            ),
        ]

        agent.run("README 在哪")

        assert memory.long_term_count == 0
        assert llm.chat.call_count == 2


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
