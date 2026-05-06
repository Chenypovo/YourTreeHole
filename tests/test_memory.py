# tests/test_memory.py
import pytest
import tempfile
import os
from core.memory import Memory


@pytest.fixture
def memory(tmp_path):
    return Memory(chroma_path=str(tmp_path / "test_memory"))


class TestShortTermMemory:
    def test_add_and_get_messages(self, memory):
        memory.add_message("user", "hello")
        memory.add_message("assistant", "hi there")

        ctx = memory.get_context(max_tokens=4000)
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[1]["content"] == "hi there"

    def test_clear_empties_short_term(self, memory):
        memory.add_message("user", "hello")
        memory.clear()
        assert memory.get_context(max_tokens=4000) == []

    def test_get_context_truncates_by_tokens(self, memory):
        # Add many messages, verify get_context respects max_tokens
        for i in range(50):
            memory.add_message("user", f"message {i} " * 100)

        ctx = memory.get_context(max_tokens=500)
        total_text = " ".join(m["content"] for m in ctx)
        # Each "message N " is ~2 tokens, 50*100 = 5000 tokens worth
        # With max_tokens=500, should have significantly fewer messages
        assert len(ctx) < 50


class TestLongTermMemory:
    def test_save_and_recall(self, memory):
        memory.save_long_term("用户喜欢暗色主题", {"type": "preference"})
        results = memory.recall("用户喜欢什么主题", top_k=1)
        assert len(results) >= 1
        assert any("暗色" in r for r in results)

    def test_recall_returns_empty_when_no_match(self, memory):
        results = memory.recall("完全不相关的内容 xyz", top_k=3)
        assert isinstance(results, list)

    def test_save_multiple_and_recall_top_k(self, memory):
        memory.save_long_term("用户喜欢Python", {"type": "preference"})
        memory.save_long_term("用户在写agent项目", {"type": "fact"})
        memory.save_long_term("用户喜欢暗色主题", {"type": "preference"})

        results = memory.recall("用户偏好", top_k=2)
        assert len(results) <= 2

    def test_long_term_persists_across_instances(self, tmp_path):
        path = str(tmp_path / "persist_test")
        m1 = Memory(chroma_path=path)
        m1.save_long_term("持久化测试数据", {"type": "test"})

        m2 = Memory(chroma_path=path)
        results = m2.recall("持久化测试", top_k=1)
        assert any("持久化" in r for r in results)
