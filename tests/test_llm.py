import pytest
from unittest.mock import patch, MagicMock
from core.config import LLMSettings
from core.llm import LLMClient, LLMResponse


class TestLLMResponse:
    def test_text_only_response(self):
        resp = LLMResponse(content="hello", tool_calls=[])
        assert resp.content == "hello"
        assert resp.has_tool_calls is False

    def test_tool_call_response(self):
        call = {"id": "call_1", "name": "search", "arguments": '{"q": "test"}'}
        resp = LLMResponse(content="", tool_calls=[call])
        assert resp.has_tool_calls is True
        assert resp.tool_calls[0]["name"] == "search"


class TestLLMClient:
    def test_chat_text_response(self, mocker):
        mock_choice = MagicMock()
        mock_choice.message.content = "hello world"
        mock_choice.message.tool_calls = None
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mocker.patch("core.llm.OpenAI").return_value.chat.completions.create.return_value = mock_resp

        client = LLMClient(base_url="http://test", api_key="test", model="test-model")
        result = client.chat([{"role": "user", "content": "hi"}])

        assert result.content == "hello world"
        assert result.has_tool_calls is False

    def test_chat_tool_call_response(self, mocker):
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_1"
        mock_tool_call.function.name = "search"
        mock_tool_call.function.arguments = '{"q": "test"}'

        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_choice.message.tool_calls = [mock_tool_call]
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mocker.patch("core.llm.OpenAI").return_value.chat.completions.create.return_value = mock_resp

        client = LLMClient(base_url="http://test", api_key="test", model="test-model")
        result = client.chat([{"role": "user", "content": "search for test"}])

        assert result.has_tool_calls is True
        assert result.tool_calls[0]["function"]["name"] == "search"

    def test_chat_passes_tools_param(self, mocker):
        mock_create = mocker.patch("core.llm.OpenAI").return_value.chat.completions.create
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_choice.message.tool_calls = None
        mock_create.return_value.choices = [mock_choice]

        client = LLMClient(base_url="http://test", api_key="test", model="test-model")
        tools = [{"type": "function", "function": {"name": "test"}}]
        client.chat([{"role": "user", "content": "hi"}], tools=tools)

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("tools") == tools or any("tools" in str(a) for a in call_kwargs.args)

    def test_from_env_creates_client(self, mocker):
        mocker.patch.dict("os.environ", {
            "OPENAI_BASE_URL": "http://test",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "test-model",
        })
        mocker.patch("core.llm.OpenAI")

        client = LLMClient.from_env()
        assert client.model == "test-model"

    def test_from_settings_prefers_configured_model(self, mocker):
        mocker.patch.dict("os.environ", {
            "OPENAI_BASE_URL": "http://test",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "env-model",
        })
        mocker.patch("core.llm.OpenAI")

        client = LLMClient.from_settings(LLMSettings(model="config-model"))
        assert client.model == "config-model"
