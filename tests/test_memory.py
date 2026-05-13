# tests/test_memory.py
import pytest
from core.memory import FileMemory


@pytest.fixture
def memory(tmp_path):
    return FileMemory(data_dir=str(tmp_path / "data"))


class TestShortTermMemory:
    def test_add_and_get_messages(self, memory):
        memory.add_message("user", "你好")
        memory.add_message("assistant", "嗨")
        ctx = memory.get_context()
        assert len(ctx) == 2
        assert ctx[0]["content"] == "你好"

    def test_clear_empties_short_term(self, memory):
        memory.add_message("user", "test")
        memory.clear()
        assert memory.get_context() == []

    def test_get_context_truncates_by_tokens(self, memory):
        for i in range(50):
            memory.add_message("user", f"msg {i} " * 100)
        ctx = memory.get_context(max_tokens=200)
        total = sum(len(m["content"]) // 4 for m in ctx)
        assert total <= 200


class TestLongTermMemory:
    def test_save_creates_memories_file(self, memory):
        memory.save_memory("用户喜欢暗色主题", "偏好")
        assert (memory.data_dir / "memories.md").exists()
        text = (memory.data_dir / "memories.md").read_text(encoding="utf-8")
        assert "暗色主题" in text

    def test_save_adds_date_header(self, memory):
        from datetime import date
        memory.save_memory("test", "general")
        text = (memory.data_dir / "memories.md").read_text(encoding="utf-8")
        assert date.today().isoformat() in text

    def test_save_multiple_same_day(self, memory):
        memory.save_memory("first", "general")
        memory.save_memory("second", "event")
        entries = memory.list_memories()
        assert len(entries) == 2
        assert entries[0]["content"] == "first"
        assert entries[1]["content"] == "second"

    def test_save_resolved_flag(self, memory):
        memory.save_memory("done thing", "event", resolved=True)
        entries = memory.list_memories()
        assert entries[0]["resolved"] is True

    def test_list_memories_empty(self, memory):
        assert memory.list_memories() == []

    def test_list_memories_parses_format(self, memory):
        memory.save_memory("用户喜欢猫", "偏好")
        memory.save_memory("周五面试", "事件")
        entries = memory.list_memories()
        assert len(entries) == 2
        assert entries[0]["category"] == "偏好"
        assert entries[1]["category"] == "事件"

    def test_delete_memory(self, memory):
        memory.save_memory("keep this", "general")
        memory.save_memory("delete this", "general")
        deleted = memory.delete_memory(2)
        assert deleted["content"] == "delete this"
        assert len(memory.list_memories()) == 1

    def test_delete_out_of_range_raises(self, memory):
        with pytest.raises(IndexError):
            memory.delete_memory(1)

    def test_get_recent_memories(self, memory):
        for i in range(10):
            memory.save_memory(f"mem {i}", "general")
        recent = memory.get_recent_memories(3)
        assert len(recent) == 3
        assert recent[-1]["content"] == "mem 9"

    def test_get_unresolved_events(self, memory):
        memory.save_memory("unresolved", "event")
        memory.save_memory("done", "event", resolved=True)
        unresolved = memory.get_unresolved_events()
        assert len(unresolved) == 1
        assert unresolved[0]["content"] == "unresolved"

    def test_resolve_memory(self, memory):
        memory.save_memory("pending", "event")
        memory.resolve_memory(1)
        entries = memory.list_memories()
        assert entries[0]["resolved"] is True

    def test_memory_count(self, memory):
        assert memory.memory_count == 0
        memory.save_memory("a", "general")
        memory.save_memory("b", "general")
        assert memory.memory_count == 2
