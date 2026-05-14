# core/agent.py
from __future__ import annotations

import json
from collections.abc import Generator
from threading import Thread
from typing import TYPE_CHECKING, Any

from core.context import ContextManager
from core.llm import LLMClient, LLMResponse
from core.memory import FileMemory
from core.profile import UserProfile

if TYPE_CHECKING:
    from core.emotion import EmotionEngine


class Agent:
    """Simple chat agent for the treehole.

    No ReAct loop, no tools. Just: build context -> call LLM -> save memory.
    """

    def __init__(
        self,
        llm: LLMClient,
        memory: FileMemory,
        profile: UserProfile,
        context_manager: ContextManager,
        enable_memory_gating: bool = False,
        profile_update_interval: int = 5,
    ):
        self.llm = llm
        self.memory = memory
        self.profile = profile
        self.context_manager = context_manager
        self.enable_memory_gating = enable_memory_gating
        self._profile_update_interval = profile_update_interval
        self._turn_count = 0
        self.emotion: EmotionEngine | None = None

    def attach_emotion(self, emotion: "EmotionEngine") -> None:
        self.emotion = emotion

    def run(self, user_input: str) -> str:
        """Run one conversation turn. No tools, no loops."""
        messages = self.context_manager.build(user_input)
        self.memory.add_message("user", user_input)

        response = self.llm.chat(messages=messages)

        self.memory.add_message("assistant", response.content)
        self._finalize_turn(user_input, response.content)

        return response.content

    def run_stream(self, user_input: str) -> Generator[str, None, None]:
        """Stream one conversation turn. Yields tokens."""
        messages = self.context_manager.build(user_input)
        self.memory.add_message("user", user_input)

        full_content = ""
        for token, final in self.llm.chat_stream(messages=messages):
            if token:
                full_content += token
                yield token
            if final:
                self.memory.add_message("assistant", final.content)
                full_content = final.content

        self._finalize_turn(user_input, full_content)

    def _finalize_turn(self, user_input: str, assistant_output: str) -> None:
        """Run slow post-turn tasks in background."""
        self._turn_count += 1
        turn_count = self._turn_count
        self.memory.save_turn(user_input, assistant_output)

        def worker() -> None:
            if self.enable_memory_gating:
                self._maybe_save_memory(user_input, assistant_output)
            if turn_count % self._profile_update_interval == 0:
                recent = "\n".join(
                    f"{m['role']}: {m['content']}"
                    for m in self.memory.get_context(max_tokens=2000)
                )
                self.profile.update(self.llm, recent)
            if self.emotion:
                self.emotion.process_turn(user_input, assistant_output)

        Thread(target=worker, daemon=True).start()

    def _maybe_save_memory(self, user_input: str, assistant_output: str) -> None:
        """Ask LLM whether this turn contains memory worth saving."""
        if not user_input.strip() and not assistant_output.strip():
            return

        messages = [
            {
                "role": "system",
                "content": (
                    "你判断一段对话是否包含值得长期记住的用户信息。\n"
                    "值得记住的：用户偏好、身份、习惯、重要事件、情感状态、人际关系。\n"
                    "不值得：临时问题、闲聊、纯工具输出。\n"
                    "返回JSON: {\"should_save\": boolean, \"memory\": \"简短内容\", \"category\": \"偏好|事件|习惯|情感|人物|其他\"}"
                ),
            },
            {
                "role": "user",
                "content": f"用户: {user_input}\n助手: {assistant_output}\n\n是否值得记住？",
            },
        ]

        try:
            decision = self.llm.chat(messages=messages, tools=None)
            payload = _parse_json_object(decision.content)
        except Exception:
            return

        if not payload.get("should_save"):
            return

        memory_text = str(payload.get("memory", "")).strip()
        if not memory_text:
            return

        category = str(payload.get("category", "其他")).strip()
        resolved = category not in ("事件",)
        self.memory.save_memory(memory_text, category=category, resolved=resolved)


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from plain text or fenced code output."""
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 3:
            raw = "\n".join(lines[1:-1]).strip()
    return json.loads(raw)
