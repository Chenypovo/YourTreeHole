# core/context.py
from __future__ import annotations

from pathlib import Path

from core.memory import FileMemory
from core.profile import UserProfile


class ContextManager:
    """Assembles the full message list for treehole LLM calls."""

    def __init__(
        self,
        persona: str,
        memory: FileMemory,
        profile: UserProfile,
        model_name: str | None = None,
        emotion=None,
    ):
        self._persona = persona
        self._memory = memory
        self._profile = profile
        self._model_name = model_name
        self._emotion = emotion

    @property
    def memory(self) -> FileMemory:
        return self._memory

    @property
    def profile(self) -> UserProfile:
        return self._profile

    @property
    def persona(self) -> str:
        return self._persona

    @persona.setter
    def persona(self, value: str) -> None:
        self._persona = value

    @classmethod
    def from_file(
        cls,
        persona_path: str,
        memory: FileMemory,
        profile: UserProfile,
        model_name: str | None = None,
        emotion=None,
    ) -> ContextManager:
        persona = Path(persona_path).read_text(encoding="utf-8").strip()
        return cls(
            persona=persona,
            memory=memory,
            profile=profile,
            model_name=model_name,
            emotion=emotion,
        )

    def build(self, user_input: str) -> list[dict[str, str]]:
        """Build the full message list for an LLM call."""
        system_prompt = self._build_system_prompt()

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        history = self._memory.get_context(max_tokens=3000)
        messages.extend(history)

        messages.append({"role": "user", "content": user_input})
        return messages

    def _build_system_prompt(self) -> str:
        parts = [self._persona]

        # Inject user profile
        profile_text = self._profile.load()
        if profile_text and "暂无记录" not in profile_text[:200]:
            parts.append(f"\n\n## 关于用户:\n{profile_text}")

        # Inject recent memories
        recent = self._memory.get_recent_memories(10)
        if recent:
            parts.append("\n\n## 你记得的关于用户的事:")
            for mem in recent:
                check = "✓" if mem["resolved"] else "?"
                parts.append(f"- [{check}] {mem['content']}")

        if self._emotion:
            parts.append(f"\n\n## 情感状态:\n{self._emotion.get_mood_prompt()}")

        if self._model_name:
            parts.append(f"\n\n## 运行信息:\n- 模型: `{self._model_name}`")

        return "\n".join(parts)
