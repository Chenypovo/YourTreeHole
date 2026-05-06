# tests/test_cli.py
import pytest
from unittest.mock import MagicMock, patch
from cli.main import handle_command


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.memory = MagicMock()
    agent.memory.get_context.return_value = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    agent.memory.long_term_count = 3
    return agent


class TestHandleCommand:
    def test_quit_returns_false(self, mock_agent):
        result = handle_command("/quit", mock_agent)
        assert result is False

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

    def test_unknown_command_returns_none(self, mock_agent):
        result = handle_command("/unknown", mock_agent)
        assert result is None

    def test_normal_text_returns_none(self, mock_agent):
        result = handle_command("你好", mock_agent)
        assert result is None
