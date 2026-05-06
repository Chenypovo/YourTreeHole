# tests/test_cli.py
import pytest
from unittest.mock import MagicMock, patch
from cli.main import COMMANDS, SlashCommandCompleter, create_agent, handle_command, render_startup_banner
from core.config import AppConfig, AgentSettings, LLMSettings, MemorySettings, PersonaSettings, UISettings


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.llm.model = "glm-5.1"
    agent.enable_memory_gating = True
    agent.max_iterations = 10
    agent.tools.list_tools.return_value = [
        {"name": "read_file", "description": "读取文件内容"},
        {"name": "shell_exec", "description": "执行shell命令"},
    ]
    agent.memory = MagicMock()
    agent.memory.get_context.return_value = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    agent.memory.long_term_count = 3
    agent.memory.list_long_term.return_value = [
        {"content": "用户喜欢暗色主题"},
        {"content": "用户在写agent项目"},
    ]
    agent.memory.update_long_term.return_value = {"content": "新的记忆内容"}
    agent.memory.delete_long_term.return_value = {"content": "旧的记忆内容"}
    return agent


class TestHandleCommand:
    def test_single_slash_shows_commands(self, mock_agent, capsys):
        handle_command("/", mock_agent)
        output = capsys.readouterr().out
        assert "/help" in output
        assert "/showmemory" in output

    def test_single_backslash_shows_commands(self, mock_agent, capsys):
        handle_command("\\", mock_agent)
        output = capsys.readouterr().out
        assert "/help" in output
        assert "/setmemory" in output

    def test_quit_returns_false(self, mock_agent):
        result = handle_command("/quit", mock_agent)
        assert result is False

    def test_status_shows_runtime_config(self, mock_agent, capsys, mocker):
        mock_agent.llm.model = "glm-5.1"
        mock_agent.enable_memory_gating = True
        mock_agent.max_iterations = 10
        mocker.patch("cli.main.AppConfig.from_file", return_value=AppConfig(
            llm=LLMSettings(model="glm-5.1"),
            persona=PersonaSettings(path="persona.md"),
            memory=MemorySettings(chroma_path="./data/memory", enable_gating=True),
            agent=AgentSettings(max_iterations=10),
            ui=UISettings(show_input_rules=True, input_prompt="❯ "),
        ))

        handle_command("/status", mock_agent)
        output = capsys.readouterr().out
        assert "glm-5.1" in output
        assert "persona.md" in output
        assert "./data/memory" in output

    def test_clear_calls_memory_clear(self, mock_agent):
        handle_command("/clear", mock_agent)
        mock_agent.memory.clear.assert_called_once()

    def test_history_prints_context(self, mock_agent, capsys):
        handle_command("/history", mock_agent)
        output = capsys.readouterr().out
        assert "hi" in output
        assert "hello" in output

    def test_memory_shows_count(self, mock_agent, capsys):
        handle_command("/memory", mock_agent)
        output = capsys.readouterr().out
        assert "3" in output

    def test_help_shows_commands(self, mock_agent, capsys):
        handle_command("/help", mock_agent)
        output = capsys.readouterr().out
        assert "/quit" in output
        assert "/clear" in output

    def test_showmemory_prints_entries(self, mock_agent, capsys):
        handle_command("/showmemory", mock_agent)
        output = capsys.readouterr().out
        assert "用户喜欢暗色主题" in output
        assert "用户在写agent项目" in output

    def test_backslash_alias_works_for_showmemory(self, mock_agent, capsys):
        handle_command("\\showmemory", mock_agent)
        output = capsys.readouterr().out
        assert "用户喜欢暗色主题" in output

    def test_setmemory_updates_entry(self, mock_agent, capsys):
        handle_command("/setmemory 2 新的记忆内容", mock_agent)
        output = capsys.readouterr().out
        mock_agent.memory.update_long_term.assert_called_once_with(2, "新的记忆内容")
        assert "已更新长期记忆 2" in output

    def test_delmemory_deletes_entry(self, mock_agent, capsys):
        handle_command("/delmemory 1", mock_agent)
        output = capsys.readouterr().out
        mock_agent.memory.delete_long_term.assert_called_once_with(1)
        assert "已删除长期记忆 1" in output

    def test_unknown_command_returns_none(self, mock_agent):
        result = handle_command("/unknown", mock_agent)
        assert result is None

    def test_normal_text_returns_none(self, mock_agent):
        result = handle_command("你好", mock_agent)
        assert result is None


class TestSlashCommandCompleter:
    def test_completer_returns_matching_commands(self):
        from prompt_toolkit.document import Document

        completer = SlashCommandCompleter()
        completions = list(completer.get_completions(Document(text="/sh"), None))
        texts = [item.text for item in completions]

        assert "/showmemory" in texts
        assert "/help" not in texts

    def test_completer_ignores_non_command_input(self):
        from prompt_toolkit.document import Document

        completer = SlashCommandCompleter()
        completions = list(completer.get_completions(Document(text="hello"), None))

        assert completions == []


def test_create_agent_uses_app_config(tmp_path, mocker):
    mocker.patch("core.llm.OpenAI")
    mocker.patch.dict("os.environ", {
        "OPENAI_BASE_URL": "http://test",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_MODEL": "env-model",
    })

    persona_file = tmp_path / "persona.md"
    persona_file.write_text("你是一只测试猫", encoding="utf-8")

    config = AppConfig(
        llm=LLMSettings(model="config-model"),
        persona=PersonaSettings(path=str(persona_file)),
        memory=MemorySettings(chroma_path=str(tmp_path / "memory"), enable_gating=False),
        agent=AgentSettings(max_iterations=3),
        ui=UISettings(show_input_rules=False, input_prompt=">>> "),
    )

    agent = create_agent(config)

    assert agent.llm.model == "config-model"
    assert agent.max_iterations == 3
    assert agent.enable_memory_gating is False


def test_render_startup_banner_shows_runtime_info(mock_agent, capsys):
    config = AppConfig(
        llm=LLMSettings(model="glm-5.1"),
        persona=PersonaSettings(path="persona.md"),
        memory=MemorySettings(chroma_path="./data/memory", enable_gating=True),
        agent=AgentSettings(max_iterations=10),
        ui=UISettings(show_input_rules=True, input_prompt="❯ "),
    )

    render_startup_banner(mock_agent, config)
    output = capsys.readouterr().out

    assert "Murphy Agent" in output
    assert "glm-5.1" in output
    assert "read_file" in output
    assert "Persona" not in output
    assert "Memory" not in output
