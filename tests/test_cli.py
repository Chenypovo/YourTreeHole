# tests/test_cli.py
import pytest
from unittest.mock import MagicMock, patch
from cli.main import (
    COMMANDS,
    DEFAULT_PERSONA,
    SlashCommandCompleter,
    create_agent,
    handle_command,
    is_placeholder_persona,
    load_persona_text,
    persona_setup_needed,
    render_startup_banner,
    save_local_persona,
)
from core.config import AppConfig, AgentSettings, LLMSettings, MemorySettings, PersonaSettings, UISettings
from core.llm import LLMResponse


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.llm.model = "glm-5.1"
    agent.memory = MagicMock()
    agent.profile = MagicMock()
    agent.profile.load.return_value = "## 用户画像\n### 基本信息\n- 测试用户"
    agent.memory.list_memories.return_value = [
        {"content": "用户喜欢猫", "category": "偏好", "resolved": True, "date": "2026-05-13"},
    ]
    agent.memory.delete_memory.return_value = {"content": "删除的记忆", "category": "test", "resolved": False, "date": "2026-05-13"}
    return agent


class TestHandleCommand:
    def test_quit_returns_false(self, mock_agent):
        assert handle_command("/quit", mock_agent) is False

    def test_reset_clears_memory(self, mock_agent):
        handle_command("/reset", mock_agent)
        mock_agent.memory.clear.assert_called_once()

    def test_profile_shows_profile(self, mock_agent, capsys):
        handle_command("/profile", mock_agent)
        output = capsys.readouterr().out
        assert "测试用户" in output

    def test_memories_lists_entries(self, mock_agent, capsys):
        handle_command("/memories", mock_agent)
        output = capsys.readouterr().out
        assert "喜欢猫" in output

    def test_remember_adds_memory(self, mock_agent, capsys):
        handle_command("/remember test memory", mock_agent)
        mock_agent.memory.save_memory.assert_called_once_with("test memory", category="手动", resolved=True)

    def test_forget_deletes_memory(self, mock_agent, capsys):
        handle_command("/forget 1", mock_agent)
        mock_agent.memory.delete_memory.assert_called_once_with(1)

    def test_help_shows_commands(self, mock_agent, capsys):
        handle_command("/help", mock_agent)
        output = capsys.readouterr().out
        assert "/quit" in output
        assert "/memories" in output

    def test_unknown_command_returns_none(self, mock_agent):
        assert handle_command("/unknown", mock_agent) is None

    def test_normal_text_returns_none(self, mock_agent):
        assert handle_command("你好", mock_agent) is None


class TestSlashCommandCompleter:
    def test_completer_returns_matching_commands(self):
        from prompt_toolkit.document import Document
        completer = SlashCommandCompleter()
        completions = list(completer.get_completions(Document(text="/mem"), None))
        texts = [item.text for item in completions]
        assert "/memories" in texts


def test_create_agent(tmp_path, mocker):
    mocker.patch("core.llm.OpenAI")
    mocker.patch.dict("os.environ", {
        "OPENAI_BASE_URL": "http://test",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_MODEL": "env-model",
    })

    persona_file = tmp_path / "persona.md"
    persona_file.write_text("你是一个温暖的倾听者", encoding="utf-8")

    config = AppConfig(
        llm=LLMSettings(model="test-model"),
        persona=PersonaSettings(path=str(persona_file)),
        memory=MemorySettings(data_dir=str(tmp_path / "data"), enable_gating=False),
        agent=AgentSettings(),
        ui=UISettings(show_input_rules=False, input_prompt=">>> "),
    )

    agent, emotion = create_agent(config)
    assert agent.llm.model == "test-model"
    assert emotion is not None


def test_placeholder_persona_detected():
    assert is_placeholder_persona("***You can define the characteristics of the agent here.***")
    assert not is_placeholder_persona("你是一个温柔的树洞")


def test_load_persona_uses_private_data_persona(tmp_path):
    tracked_persona = tmp_path / "persona.md"
    tracked_persona.write_text("***You can define the characteristics of the agent here.***", encoding="utf-8")
    config = AppConfig(
        llm=LLMSettings(model="glm-5.1"),
        persona=PersonaSettings(path=str(tracked_persona)),
        memory=MemorySettings(data_dir=str(tmp_path / "data")),
        agent=AgentSettings(),
        ui=UISettings(),
    )

    save_local_persona(config, "你像一个安静的老朋友")

    assert load_persona_text(config) == "你像一个安静的老朋友"
    assert persona_setup_needed(config) is False


def test_load_persona_falls_back_to_default_for_placeholder(tmp_path):
    tracked_persona = tmp_path / "persona.md"
    tracked_persona.write_text("***You can define the characteristics of the agent here.***", encoding="utf-8")
    config = AppConfig(
        llm=LLMSettings(model="glm-5.1"),
        persona=PersonaSettings(path=str(tracked_persona)),
        memory=MemorySettings(data_dir=str(tmp_path / "data")),
        agent=AgentSettings(),
        ui=UISettings(),
    )

    assert load_persona_text(config) == DEFAULT_PERSONA
    assert persona_setup_needed(config) is True


def test_render_startup_banner(mock_agent, capsys):
    config = AppConfig(
        llm=LLMSettings(model="glm-5.1"),
        persona=PersonaSettings(path="persona.md"),
        memory=MemorySettings(data_dir="./data"),
        agent=AgentSettings(),
        ui=UISettings(show_input_rules=True, input_prompt="❯ "),
    )
    render_startup_banner(mock_agent, config)
    output = capsys.readouterr().out
    assert "Treehole" in output
