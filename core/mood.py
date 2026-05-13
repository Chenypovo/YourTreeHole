# core/mood.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Mood:
    value: int = 50  # 0-100, default calm

    def adjust(self, delta: int) -> None:
        """Adjust mood by delta, clamped to 0-100."""
        self.value = max(0, min(100, self.value + delta))

    @property
    def label(self) -> str:
        """Return mood label based on value."""
        if self.value >= 75:
            return "happy"
        if self.value >= 40:
            return "calm"
        return "sad"

    @property
    def hearts(self) -> str:
        """Return a 5-symbol bar: ♥ for filled, ♦ for empty."""
        filled = round(self.value / 20)
        return "♥" * filled + "♦" * (5 - filled)
