from __future__ import annotations

from dataclasses import dataclass

from cli.main import create_agent, generate_greeting
from core.agent import Agent
from core.config import AppConfig
from core.emotion import EmotionEngine


MAX_TELEGRAM_MESSAGE_LEN = 3900


@dataclass
class BotRuntime:
    agent: Agent
    emotion: EmotionEngine
    config: AppConfig


def create_shared_runtime(config_path: str = "config/settings.toml") -> BotRuntime:
    """Create the same single-user Agent stack used by the Web UI."""
    config = AppConfig.from_file(config_path)
    agent, emotion = create_agent(config)
    return BotRuntime(agent=agent, emotion=emotion, config=config)


def is_allowed_user(user_id: int | None, allowed_user_ids: list[int]) -> bool:
    """Return whether a Telegram user is allowed to use this private bot."""
    return user_id is not None and user_id in set(allowed_user_ids)


def split_message(text: str, limit: int = MAX_TELEGRAM_MESSAGE_LEN) -> list[str]:
    """Split long replies so Telegram accepts them."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def handle_bot_command(command: str, args: list[str], runtime: BotRuntime) -> str:
    """Handle private treehole commands shared by chat-platform adapters."""
    command = command.lower().lstrip("/")

    if command in {"start", "help"}:
        return _help_text(runtime)

    if command == "memories":
        return _format_memories(runtime.agent.memory.list_memories())

    if command == "remember":
        content = " ".join(args).strip()
        if not content:
            return "用法：/remember 你想让树洞记住的内容"
        runtime.agent.memory.save_memory(content, category="手动", resolved=True)
        return "已记住。"

    if command == "forget":
        if not args or not args[0].isdigit():
            return "用法：/forget 记忆编号"
        try:
            deleted = runtime.agent.memory.delete_memory(int(args[0]))
        except (IndexError, ValueError) as exc:
            return str(exc)
        return f"已删除：{deleted['content']}"

    if command == "profile":
        return runtime.agent.profile.load() or "还没有用户画像。"

    if command == "reset":
        if not args or args[0].lower() != "confirm":
            return "这会清空当前短期对话，但保留长期记忆。确认请发送：/reset confirm"
        runtime.agent.memory.clear()
        return "当前对话已重置，长期记忆仍然保留。"

    return "未知命令。发送 /help 查看可用命令。"


def greeting_text(runtime: BotRuntime) -> str:
    """Generate a short proactive greeting for mobile chat entrypoints."""
    text = generate_greeting(runtime.agent.llm, runtime.agent.profile, runtime.agent.memory)
    return text or "你好呀，今天想把什么放进树洞？"


def _help_text(runtime: BotRuntime) -> str:
    greeting = greeting_text(runtime)
    return (
        f"{greeting}\n\n"
        "可用命令：\n"
        "/memories - 查看长期记忆\n"
        "/remember <内容> - 手动添加记忆\n"
        "/forget <编号> - 删除一条记忆\n"
        "/profile - 查看用户画像\n"
        "/reset confirm - 重置当前短期对话"
    )


def _format_memories(entries: list[dict]) -> str:
    if not entries:
        return "还没有长期记忆。"

    lines = ["长期记忆："]
    for idx, entry in enumerate(entries, start=1):
        status = "已闭环" if entry.get("resolved") else "未闭环"
        category = entry.get("category") or "general"
        date = entry.get("date") or "unknown"
        content = entry.get("content") or ""
        lines.append(f"{idx}. [{status}] [{category}] {content} ({date})")
    return "\n".join(lines)
