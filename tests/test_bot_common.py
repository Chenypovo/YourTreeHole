from types import SimpleNamespace

from bot.common import handle_bot_command, is_allowed_user, split_message


def test_is_allowed_user_requires_explicit_id():
    assert is_allowed_user(123, [123]) is True
    assert is_allowed_user(456, [123]) is False
    assert is_allowed_user(None, [123]) is False
    assert is_allowed_user(123, []) is False


def test_split_message_keeps_short_text():
    assert split_message("hello", limit=10) == ["hello"]


def test_split_message_splits_long_text():
    assert split_message("abc\ndefghijk", limit=6) == ["abc", "defghi", "jk"]


def test_handle_memories_command_formats_entries():
    runtime = SimpleNamespace(
        agent=SimpleNamespace(
            memory=SimpleNamespace(
                list_memories=lambda: [
                    {
                        "date": "2026-05-15",
                        "category": "事件",
                        "content": "用户开始接入 Telegram",
                        "resolved": False,
                    },
                ],
            ),
        ),
    )

    text = handle_bot_command("/memories", [], runtime)

    assert "长期记忆" in text
    assert "用户开始接入 Telegram" in text


def test_handle_remember_command_adds_manual_memory():
    calls = []
    runtime = SimpleNamespace(
        agent=SimpleNamespace(
            memory=SimpleNamespace(save_memory=lambda *args, **kwargs: calls.append((args, kwargs))),
        ),
    )

    text = handle_bot_command("/remember", ["重要", "事情"], runtime)

    assert text == "已记住。"
    assert calls == [(("重要 事情",), {"category": "手动", "resolved": True})]


def test_handle_reset_requires_confirm():
    calls = []
    runtime = SimpleNamespace(
        agent=SimpleNamespace(
            memory=SimpleNamespace(clear=lambda: calls.append("clear")),
        ),
    )

    assert "确认" in handle_bot_command("/reset", [], runtime)
    assert calls == []
    assert "已重置" in handle_bot_command("/reset", ["confirm"], runtime)
    assert calls == ["clear"]
