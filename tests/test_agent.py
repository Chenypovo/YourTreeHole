# tests/test_agent.py
import pytest
import time
from unittest.mock import MagicMock
from core.agent import Agent
from core.llm import LLMResponse
from core.memory import FileMemory
from core.profile import UserProfile
from core.context import ContextManager


@pytest.fixture
def agent(tmp_path):
    data_dir = str(tmp_path / "agent_test")
    llm = MagicMock()
    memory = FileMemory(data_dir=data_dir)
    profile = UserProfile(data_dir=data_dir)
    context = ContextManager(
        persona="你是一个温暖的倾听者",
        memory=memory,
        profile=profile,
    )
    return Agent(llm=llm, memory=memory, profile=profile, context_manager=context)


class TestAgentSimpleChat:
    def test_simple_reply(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="我在听，继续说", tool_calls=[])
        result = agent.run("最近心情不好")
        assert result == "我在听，继续说"

    def test_conversation_stored(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="嗯嗯", tool_calls=[])
        agent.run("你好")
        ctx = agent.memory.get_context()
        assert any(m["content"] == "你好" for m in ctx)
        assert any(m["content"] == "嗯嗯" for m in ctx)

    def test_conversation_written_to_journal(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="我在听", tool_calls=[])
        agent.run("最近有点累")
        text = agent.memory.journal_file.read_text(encoding="utf-8")
        assert "最近有点累" in text
        assert "我在听" in text

    def test_message_sent_once(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="hi", tool_calls=[])
        agent.run("test")
        sent = agent.llm.chat.call_args.kwargs["messages"]
        user_msgs = [m for m in sent if m["role"] == "user" and m["content"] == "test"]
        assert len(user_msgs) == 1

    def test_no_tools_in_call(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="ok", tool_calls=[])
        agent.run("test")
        kwargs = agent.llm.chat.call_args.kwargs
        # No tools kwarg should be passed
        assert "tools" not in kwargs

    def test_emotion_process_turn_called(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="嗯", tool_calls=[])
        emotion = MagicMock()
        agent.attach_emotion(emotion)
        agent.run("test")
        time.sleep(0.5)  # wait for background thread
        emotion.process_turn.assert_called_once_with("test", "嗯")

    def test_memory_gating_saves(self, tmp_path):
        data_dir = str(tmp_path / "gate_test")
        llm = MagicMock()
        memory = FileMemory(data_dir=data_dir)
        profile = UserProfile(data_dir=data_dir)
        context = ContextManager(
            persona="test",
            memory=memory,
            profile=profile,
        )
        agent = Agent(
            llm=llm, memory=memory, profile=profile, context_manager=context,
            enable_memory_gating=True,
        )

        llm.chat.side_effect = [
            LLMResponse(content="记住了", tool_calls=[]),
            LLMResponse(content='{"should_save": true, "memory": "用户喜欢猫", "category": "偏好"}', tool_calls=[]),
        ]

        agent.run("我喜欢猫")
        time.sleep(0.5)
        entries = memory.list_memories()
        assert any("猫" in e["content"] for e in entries)

    def test_profile_update_triggers(self, tmp_path):
        data_dir = str(tmp_path / "profile_update")
        llm = MagicMock()
        memory = FileMemory(data_dir=data_dir)
        profile = UserProfile(data_dir=data_dir)
        context = ContextManager(
            persona="test",
            memory=memory,
            profile=profile,
        )
        agent = Agent(
            llm=llm, memory=memory, profile=profile, context_manager=context,
            profile_update_interval=2,
        )

        llm.chat.side_effect = [
            LLMResponse(content="ok", tool_calls=[]),
            LLMResponse(content="ok", tool_calls=[]),
            LLMResponse(content="ok", tool_calls=[]),
            # Third turn triggers profile update (turn 2 % 2 == 0)
            LLMResponse(content="## 更新的画像\n- test", tool_calls=[]),
        ]

        agent.run("first")
        agent.run("second")
        time.sleep(0.5)
        # Profile should have been updated after 2nd turn
        assert llm.chat.call_count >= 3  # 2 chat + 1 profile update
