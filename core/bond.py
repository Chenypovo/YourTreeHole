# core/bond.py
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

BOND_LEVELS = [
    (0,   "Lv.1", "Stranger",      "你刚认识这个用户，保持礼貌和距离。"),
    (21,  "Lv.2", "Acquaintance",  "你和用户是普通朋友了，可以放松一些。"),
    (51,  "Lv.3", "Friend",        "你和用户是好朋友了，可以适当开玩笑。"),
    (81,  "Lv.4", "Close Friend",  "你和用户很亲密，能深度理解对方。"),
    (121, "Lv.5", "Soulmate",      "你和用户是最亲密的伙伴，完全了解彼此。"),
]

DEFAULT_BOND_DATA = {
    "total_bond": 0,
    "level": 1,
    "level_name": "Stranger",
    "first_chat_date": None,
    "total_turns": 0,
    "consecutive_days": 0,
    "last_chat_date": None,
    "easter_eggs_triggered": [],
    "achievements": [],
}


@dataclass
class Bond:
    path: str = "./data/bond.json"
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        self._load()

    def _load(self):
        p = Path(self.path)
        if p.exists():
            self.data = json.loads(p.read_text(encoding="utf-8"))
        else:
            self.data = deepcopy(DEFAULT_BOND_DATA)
            self._save()

    def _save(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.path).write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @property
    def total(self) -> int:
        return self.data["total_bond"]

    @property
    def level(self) -> int:
        return self.data["level"]

    @property
    def level_name(self) -> str:
        return self.data["level_name"]

    @property
    def level_description(self) -> str:
        for threshold, _, _, desc in reversed(BOND_LEVELS):
            if self.data["total_bond"] >= threshold:
                return desc
        return BOND_LEVELS[0][3]

    def add(self, points: int) -> bool:
        """Add bond points. Returns True if level changed."""
        old_level = self.data["level"]
        self.data["total_bond"] += points
        self.data["total_turns"] += 1

        today = date.today().isoformat()
        if self.data["first_chat_date"] is None:
            self.data["first_chat_date"] = today

        # Update consecutive days
        last = self.data.get("last_chat_date")
        if last == today:
            pass  # same day
        elif last:
            last_date = date.fromisoformat(last)
            if (date.today() - last_date).days == 1:
                self.data["consecutive_days"] += 1
            else:
                self.data["consecutive_days"] = 1
        else:
            self.data["consecutive_days"] = 1

        self.data["last_chat_date"] = today

        # Recalculate level
        new_level = 1
        new_name = "Stranger"
        for threshold, lv_tag, name, _ in BOND_LEVELS:
            if self.data["total_bond"] >= threshold:
                new_level = int(lv_tag.split(".")[1])
                new_name = name

        self.data["level"] = new_level
        self.data["level_name"] = new_name
        self._save()
        return new_level != old_level

    def check_easter_eggs(self) -> list[str]:
        """Check and return newly triggered easter egg IDs."""
        triggered = []
        eggs = self.data.get("easter_eggs_triggered", [])

        if "anniversary_7d" not in eggs and self.data["consecutive_days"] >= 7:
            eggs.append("anniversary_7d")
            triggered.append("anniversary_7d")

        if "diary_unlock" not in eggs and self.data["level"] >= 4:
            eggs.append("diary_unlock")
            triggered.append("diary_unlock")

        if "secret_unlock" not in eggs and self.data["level"] >= 5:
            eggs.append("secret_unlock")
            triggered.append("secret_unlock")

        self.data["easter_eggs_triggered"] = eggs
        self._save()
        return triggered

    def check_return_after_absence(self) -> bool:
        """Check if user was absent 3+ days."""
        last = self.data.get("last_chat_date")
        if not last:
            return False
        last_date = date.fromisoformat(last)
        return (date.today() - last_date).days >= 3

    @property
    def has_secret(self) -> bool:
        return "secret_unlock" in self.data.get("easter_eggs_triggered", [])
