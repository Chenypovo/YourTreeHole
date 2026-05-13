from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from core.bond import Bond


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bond_path(tmp_path: Path) -> str:
    return str(tmp_path / "bond.json")


# ---------------------------------------------------------------------------
# 1. Default bond is zero
# ---------------------------------------------------------------------------
def test_default_bond_is_zero(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    assert bond.total == 0
    assert bond.level == 1
    assert bond.level_name == "Stranger"


# ---------------------------------------------------------------------------
# 2. Add points persists to disk
# ---------------------------------------------------------------------------
def test_add_points_persists(tmp_path):
    p = _bond_path(tmp_path)
    bond = Bond(path=p)
    bond.add(5)

    # Load a fresh Bond from the same path
    bond2 = Bond(path=p)
    assert bond2.total == 5


# ---------------------------------------------------------------------------
# 3. Level up when crossing threshold (21 → Lv.2 Acquaintance)
# ---------------------------------------------------------------------------
def test_level_up(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    bond.add(25)
    assert bond.level == 2
    assert bond.level_name == "Acquaintance"


# ---------------------------------------------------------------------------
# 4. add() returns True when level changes
# ---------------------------------------------------------------------------
def test_add_returns_true_on_level_up(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    # First add from 0 → 25 crosses Lv.2 threshold
    result = bond.add(25)
    assert result is True

    # Another add that does NOT cross a threshold
    result2 = bond.add(1)
    assert result2 is False


# ---------------------------------------------------------------------------
# 5. Consecutive days increments when last_chat_date is yesterday
# ---------------------------------------------------------------------------
def test_consecutive_days_increments(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    bond.data["last_chat_date"] = yesterday
    bond.data["consecutive_days"] = 3
    bond._save()

    bond.add(1)
    assert bond.data["consecutive_days"] == 4


# ---------------------------------------------------------------------------
# 6. Consecutive days resets when gap >= 2 days
# ---------------------------------------------------------------------------
def test_consecutive_days_resets(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    three_days_ago = (date.today() - timedelta(days=3)).isoformat()
    bond.data["last_chat_date"] = three_days_ago
    bond.data["consecutive_days"] = 10
    bond._save()

    bond.add(1)
    assert bond.data["consecutive_days"] == 1


# ---------------------------------------------------------------------------
# 7. Easter egg: anniversary_7d triggers at consecutive_days >= 7
# ---------------------------------------------------------------------------
def test_easter_egg_7_days(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    bond.data["consecutive_days"] = 7
    bond._save()

    result = bond.check_easter_eggs()
    assert result == ["anniversary_7d"]


# ---------------------------------------------------------------------------
# 8. Easter egg: diary_unlock triggers at level >= 4
# ---------------------------------------------------------------------------
def test_easter_egg_lv4_diary(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    # Set total_bond high enough for Lv.4 (threshold 81)
    bond.data["total_bond"] = 90
    bond.data["level"] = 4
    bond.data["level_name"] = "Close Friend"
    bond._save()

    result = bond.check_easter_eggs()
    assert "diary_unlock" in result


# ---------------------------------------------------------------------------
# 9. Easter eggs do not repeat
# ---------------------------------------------------------------------------
def test_easter_egg_no_repeat(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    bond.data["consecutive_days"] = 7
    bond._save()

    first = bond.check_easter_eggs()
    assert "anniversary_7d" in first

    second = bond.check_easter_eggs()
    assert second == []


# ---------------------------------------------------------------------------
# 10. Return after absence (3+ days since last chat)
# ---------------------------------------------------------------------------
def test_return_after_absence(tmp_path):
    bond = Bond(path=_bond_path(tmp_path))
    four_days_ago = (date.today() - timedelta(days=4)).isoformat()
    bond.data["last_chat_date"] = four_days_ago
    bond._save()

    assert bond.check_return_after_absence() is True
