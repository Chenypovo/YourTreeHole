# core/emotion.py
from __future__ import annotations

import datetime
from dataclasses import dataclass

from core.mood import Mood
from core.bond import Bond


@dataclass
class EmotionState:
    """Snapshot for rendering."""
    mood_value: int
    mood_label: str
    mood_hearts: str
    bond_level: int
    bond_name: str
    bond_description: str
    energy: int
    easter_eggs: list[str]


EASTER_EGG_MESSAGES = {
    "anniversary_7d": "🎉 我们已经连续聊天 7 天了！Murphy 为你写了一首诗...",
    "diary_unlock": "📖 Murphy 开始写日记了，偶尔会和你分享自己的想法",
    "secret_unlock": "🔐 你解锁了隐藏命令 /secret",
    "marathon_chat": "💬 今天聊得真开心，好久没这么畅快了",
    "late_night": "🌙 这么晚还不睡？我陪你",
}


class EmotionEngine:
    def __init__(self, llm, bond_path: str = "./data/bond.json"):
        self._llm = llm
        self._mood = Mood()
        self._energy = 100
        self._bond = Bond(path=bond_path)
        self._session_turns = 0

    @property
    def bond(self) -> Bond:
        return self._bond

    @property
    def mood(self) -> Mood:
        return self._mood

    @property
    def energy(self) -> int:
        return self._energy

    def get_state(self) -> EmotionState:
        return EmotionState(
            mood_value=self._mood.value,
            mood_label=self._mood.label,
            mood_hearts=self._mood.hearts,
            bond_level=self._bond.level,
            bond_name=self._bond.level_name,
            bond_description=self._bond.level_description,
            energy=self._energy,
            easter_eggs=self._bond.data.get("easter_eggs_triggered", []),
        )

    def get_mood_prompt(self) -> str:
        """Natural language description of emotional state for system prompt."""
        state = self.get_state()
        parts = [state.bond_description]

        if state.mood_value >= 75:
            parts.append("你现在心情很好，很活跃，想多聊聊。")
        elif state.mood_value >= 40:
            parts.append("你心情平静。")
        elif state.mood_value >= 20:
            parts.append("你有点低落，不想说太多。")
        else:
            parts.append("你很不开心，回复会很少。")

        if state.energy < 20:
            parts.append("你有点累了，回复简短一些。")
        elif state.energy >= 80:
            parts.append("精力充沛。")

        return " ".join(parts)

    def rest(self) -> int:
        """Restore energy. Returns new energy value."""
        self._energy = 80
        return self._energy

    def process_turn(self, user_input: str, assistant_output: str) -> dict:
        """Called after each assistant reply. Returns event info."""
        self._session_turns += 1

        # Consume energy
        cost = 3
        if "工具" in assistant_output or "调用" in assistant_output:
            cost = 5
        self._energy = max(0, self._energy - cost)

        # LLM analyzes mood shift
        mood_delta = self._analyze_mood(user_input)
        self._mood.adjust(mood_delta)

        # LLM evaluates bond increment
        bond_points = self._evaluate_bond(user_input, assistant_output)
        level_up = self._bond.add(bond_points)

        # Check easter eggs
        new_eggs = self._bond.check_easter_eggs()

        # Session-specific: marathon_chat (50+ turns)
        if self._session_turns >= 50 and "marathon_chat" not in self._bond.data.get("easter_eggs_triggered", []):
            self._bond.data.setdefault("easter_eggs_triggered", []).append("marathon_chat")
            new_eggs.append("marathon_chat")
            self._bond._save()

        # Late night check (2-4 AM)
        hour = datetime.datetime.now().hour
        if 2 <= hour < 4 and "late_night" not in self._bond.data.get("easter_eggs_triggered", []):
            self._bond.data.setdefault("easter_eggs_triggered", []).append("late_night")
            new_eggs.append("late_night")
            self._bond._save()

        return {
            "mood_delta": mood_delta,
            "bond_points": bond_points,
            "level_up": level_up,
            "easter_eggs": new_eggs,
        }

    def _analyze_mood(self, user_input: str) -> int:
        """Ask LLM to classify user sentiment. Returns delta -15..+15."""
        messages = [
            {"role": "system", "content": (
                "分析用户消息的情感倾向。返回JSON: {\"sentiment\": \"positive\"|\"neutral\"|\"negative\", \"intensity\": 1-3}"
            )},
            {"role": "user", "content": user_input},
        ]
        try:
            resp = self._llm.chat(messages=messages, tools=None)
            from core.agent import _parse_json_object
            result = _parse_json_object(resp.content)
        except Exception:
            return 0

        sentiment = result.get("sentiment", "neutral")
        intensity = min(3, max(1, result.get("intensity", 1)))
        deltas = {"positive": 5, "neutral": 0, "negative": -5}
        return deltas.get(sentiment, 0) * intensity

    def _evaluate_bond(self, user_input: str, assistant_output: str) -> int:
        """Ask LLM to rate interaction quality. Returns 0-3."""
        messages = [
            {"role": "system", "content": (
                "评估这次互动的质量。用户分享了个人信息或情感？助手提供了有意义的帮助？\n"
                "返回JSON: {\"quality\": \"low\"|\"medium\"|\"high\"}"
            )},
            {"role": "user", "content": f"用户: {user_input}\n助手: {assistant_output}"},
        ]
        try:
            resp = self._llm.chat(messages=messages, tools=None)
            from core.agent import _parse_json_object
            result = _parse_json_object(resp.content)
        except Exception:
            return 1

        quality = result.get("quality", "medium")
        return {"low": 0, "medium": 1, "high": 3}.get(quality, 1)
