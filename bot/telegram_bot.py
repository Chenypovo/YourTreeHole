from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from bot.common import BotRuntime, create_shared_runtime, handle_bot_command, is_allowed_user, split_message

try:
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
except ImportError as exc:  # pragma: no cover - exercised by users without optional deps
    raise SystemExit(
        "Telegram support is optional. Install it with: pip install '.[telegram]'"
    ) from exc


class TelegramTreeholeBot:
    """Telegram adapter for the single-user treehole agent."""

    def __init__(self, runtime: BotRuntime):
        self.runtime = runtime
        self.allowed_user_ids = self.runtime.config.telegram.allowed_user_ids
        self._lock = asyncio.Lock()

    async def command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_allowed(update):
            return

        message = update.effective_message
        if not message or not message.text:
            return

        command = message.text.split()[0].split("@")[0]
        args = context.args or []
        async with self._lock:
            await message.chat.send_action(ChatAction.TYPING)
            reply = await asyncio.to_thread(handle_bot_command, command, args, self.runtime)
        await self._reply(message, reply)

    async def text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_allowed(update):
            return

        message = update.effective_message
        if not message or not message.text:
            return

        async with self._lock:
            await message.chat.send_action(ChatAction.TYPING)
            reply = await asyncio.to_thread(self.runtime.agent.run, message.text)
        await self._reply(message, reply)

    async def _ensure_allowed(self, update: Update) -> bool:
        message = update.effective_message
        user = update.effective_user
        if is_allowed_user(user.id if user else None, self.allowed_user_ids):
            return True

        if message:
            await message.reply_text("这个树洞是私人使用的。请先在 config/settings.toml 配置 allowed_user_ids。")
        return False

    async def _reply(self, message, text: str) -> None:
        for chunk in split_message(text):
            await message.reply_text(chunk)


def main() -> None:
    load_dotenv()
    runtime = create_shared_runtime()
    if not runtime.config.telegram.enabled:
        raise SystemExit("Telegram bot is disabled. Set [telegram].enabled = true in config/settings.toml.")
    if not runtime.config.telegram.allowed_user_ids:
        raise SystemExit("Set [telegram].allowed_user_ids before starting the private Telegram bot.")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN in .env.")

    bot = TelegramTreeholeBot(runtime)
    application = Application.builder().token(token).build()
    for command in ["start", "help", "memories", "remember", "forget", "profile", "reset"]:
        application.add_handler(CommandHandler(command, bot.command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.text))
    application.run_polling()


if __name__ == "__main__":
    main()
