# tests/test_context.py
import pytest
from unittest.mock import MagicMock
from core.context import ContextManager
from core.memory import Memory


@pytest.fixture
def context(tmp_path):
    memory = Memory(chroma_path=str(tmp_path / "ctx_test"))
    tools = MagicMock()
    tools.get_schemas.return_value = [
        {"type": "function", "function": {"name": "test_tool"}}
    ]
    persona_text = "你是一只猫"
    return ContextManager(persona=persona_text, memory=memory, tool_registry=tools)


class TestContextManager:
    def test_build_includes_system_prompt(self, context):
        messages = context.build("你好")
        assert messages[0]["role"] == "system"
        assert "你是一只猫" in messages[0]["content"]

    def test_build_includes_user_input(self, context):
        messages = context.build("你好")
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "你好"

    def test_build_includes_short_term_history(self, context):
        context.memory.add_message("user", "早上好")
        context.memory.add_message("assistant", "喵～早上好")

        messages = context.build("今天天气怎么样")
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert any("早上好" in m["content"] for m in user_msgs)

    def test_build_includes_long_term_recall(self, context):
        context.memory.save_long_term("用户喜欢暗色主题", {"type": "preference"})

        messages = context.build("帮我选个主题")
        system_content = messages[0]["content"]
        assert "暗色" in system_content

    def test_build_message_ordering(self, context):
        context.memory.add_message("user", "hi")
        context.memory.add_message("assistant", "hello")

        messages = context.build("new question")
        assert messages[0]["role"] == "system"
        # History messages in the middle
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "new question"

    def test_persona_file_load(self, tmp_path):
        persona_file = tmp_path / "persona.md"
        persona_file.write_text("你是一只狗")

        memory = Memory(chroma_path=str(tmp_path / "persona_test"))
        tools = MagicMock()
        tools.get_schemas.return_value = []

        ctx = ContextManager.from_file(
            persona_path=str(persona_file),
            memory=memory,
            tool_registry=tools,
        )
        messages = ctx.build("hi")
        assert "你是一只狗" in messages[0]["content"]
