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
        system_prompt = self._build_system_prompt(user_input)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        history = self._memory.get_context(max_tokens=3000)
        messages.extend(history)

        messages.append({"role": "user", "content": user_input})
        return messages

    def _build_system_prompt(self, user_input: str) -> str:
        parts = [self._persona]
        parts.append(
            "\n\n## 回复方式:\n"
            "- 这是树洞，不是访谈。先承接用户的情绪和事实，不要每轮结尾都反问。\n"
            "- 默认用陈述、复述、整理来回应；不要连续提出多个问题。\n"
            "- 只有在确实需要用户继续展开时，最多问一个短问题。\n"
            "- 避免反复使用「今天想聊点什么」「后来呢」「还有呢」这类模板句。"
        )

        # Inject user profile
        profile_text = self._profile.load()
        meaningful_profile = _strip_empty_profile_lines(profile_text)
        if meaningful_profile:
            parts.append(f"\n\n## 关于用户:\n{meaningful_profile}")

        unresolved = self._memory.get_unresolved_events()
        if unresolved:
            parts.append("\n\n## 还没闭环、可以在合适时自然提到的事:")
            for mem in unresolved[:10]:
                parts.append(f"- {mem['content']}")

        # Inject relevant and recent memories. Relevant old memories come first so
        # the agent can remember things beyond the most recent entries.
        seen: set[tuple[str, str, str]] = set()
        selected = []
        for mem in self._memory.get_relevant_memories(user_input, 10):
            key = (mem["date"], mem["category"], mem["content"])
            if key not in seen:
                selected.append(mem)
                seen.add(key)
        recent = self._memory.get_recent_memories(10)
        for mem in recent:
            key = (mem["date"], mem["category"], mem["content"])
            if key not in seen:
                selected.append(mem)
                seen.add(key)

        if selected:
            parts.append("\n\n## 你记得的关于用户的事:")
            for mem in selected[:15]:
                check = "✓" if mem["resolved"] else "?"
                parts.append(f"- [{check}] {mem['content']}")

        if self._emotion:
            parts.append(f"\n\n## 情感状态:\n{self._emotion.get_mood_prompt()}")

        if self._model_name:
            parts.append(f"\n\n## 运行信息:\n- 模型: `{self._model_name}`")

        return "\n".join(parts)


def _strip_empty_profile_lines(profile_text: str) -> str:
    """Remove placeholder rows while preserving real profile content."""
    lines = []
    has_real_content = False
    for line in profile_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- （暂无") or stripped.startswith("- (暂无"):
            continue
        if stripped:
            lines.append(line)
            if not stripped.startswith("#"):
                has_real_content = True
    if not has_real_content:
        return ""
    return "\n".join(lines).strip()
