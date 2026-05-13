# tests/test_context.py
import pytest
from unittest.mock import MagicMock
from core.context import ContextManager
from core.memory import FileMemory
from core.profile import UserProfile


@pytest.fixture
def context(tmp_path):
    data_dir = str(tmp_path / "ctx_test")
    memory = FileMemory(data_dir=data_dir)
    profile = UserProfile(data_dir=data_dir)
    return ContextManager(persona="你是一个温暖的倾听者", memory=memory, profile=profile)


class TestContextManager:
    def test_build_includes_system_prompt(self, context):
        messages = context.build("你好")
        assert messages[0]["role"] == "system"
        assert "倾听者" in messages[0]["content"]

    def test_build_includes_user_input(self, context):
        messages = context.build("你好")
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "你好"

    def test_build_includes_short_term_history(self, context):
        context.memory.add_message("user", "早上好")
        context.memory.add_message("assistant", "嗯嗯")
        messages = context.build("今天怎样")
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert any("早上好" in m["content"] for m in user_msgs)

    def test_build_includes_profile(self, context):
        context.profile.save("## 用户画像\n### 基本信息\n- 程序员")
        messages = context.build("你好")
        assert "程序员" in messages[0]["content"]

    def test_build_includes_memories(self, context):
        context.memory.save_memory("用户喜欢猫", "偏好")
        messages = context.build("你好")
        assert "喜欢猫" in messages[0]["content"]

    def test_build_with_emotion(self, tmp_path):
        data_dir = str(tmp_path / "ctx_emotion")
        memory = FileMemory(data_dir=data_dir)
        profile = UserProfile(data_dir=data_dir)
        mock_emotion = MagicMock()
        mock_emotion.get_mood_prompt.return_value = "你心情很好"
        ctx = ContextManager(persona="test", memory=memory, profile=profile, emotion=mock_emotion)
        messages = ctx.build("hi")
        assert "心情" in messages[0]["content"]

    def test_persona_file_load(self, tmp_path):
        data_dir = str(tmp_path / "ctx_file")
        persona_file = tmp_path / "persona.md"
        persona_file.write_text("你是一只猫", encoding="utf-8")
        memory = FileMemory(data_dir=data_dir)
        profile = UserProfile(data_dir=data_dir)
        ctx = ContextManager.from_file(persona_path=str(persona_file), memory=memory, profile=profile)
        messages = ctx.build("hi")
        assert "猫" in messages[0]["content"]

    def test_persona_setter(self, context):
        context.persona = "新人格"
        messages = context.build("hi")
        assert "新人格" in messages[0]["content"]
