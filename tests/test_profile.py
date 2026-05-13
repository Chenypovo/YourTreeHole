# tests/test_profile.py
import pytest
from unittest.mock import MagicMock
from core.profile import UserProfile, DEFAULT_PROFILE


@pytest.fixture
def profile(tmp_path):
    return UserProfile(data_dir=str(tmp_path / "data"))


class TestUserProfile:
    def test_creates_default_profile(self, profile):
        text = profile.load()
        assert "用户画像" in text
        assert "基本信息" in text

    def test_save_and_load(self, profile):
        profile.save("## 测试画像\n- test")
        assert "测试画像" in profile.load()

    def test_get_unresolved_events_empty(self, profile):
        events = profile.get_unresolved_events()
        assert events == []

    def test_get_unresolved_events_parses(self, tmp_path):
        data_dir = str(tmp_path / "data2")
        p = tmp_path / "data2" / "user_profile.md"
        p.parent.mkdir(parents=True)
        p.write_text(
            "## 用户画像\n### 未闭环事件\n- [ ] 周五面试\n- [x] 已完成的事\n- [ ] 失眠问题\n",
            encoding="utf-8",
        )
        prof = UserProfile(data_dir=data_dir)
        events = prof.get_unresolved_events()
        assert len(events) == 2
        assert "周五面试" in events[0]
        assert "失眠问题" in events[1]

    def test_update_calls_llm_and_saves(self, profile):
        from core.llm import LLMResponse
        mock_llm = MagicMock()
        mock_llm.chat.return_value = LLMResponse(content="## 更新的画像\n- 新信息", tool_calls=[])
        profile.update(mock_llm, "用户说他找到了新工作")
        assert "更新的画像" in profile.load()

    def test_update_does_not_crash_on_failure(self, profile):
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception("LLM error")
        profile.update(mock_llm, "test")  # should not raise
