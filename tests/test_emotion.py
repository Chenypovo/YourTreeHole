from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.emotion import EmotionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bond_path(tmp_path: Path) -> str:
    return str(tmp_path / "bond.json")


def _mock_llm(sentiment: str = "neutral", intensity: int = 1,
              quality: str = "medium") -> MagicMock:
    """Create a mock LLM whose chat() returns parsed-JSON-friendly content.

    _analyze_mood calls llm.chat() first (sentiment), then _evaluate_bond
    calls llm.chat() again (quality).  We use side_effect to return them in
    order.
    """
    llm = MagicMock()
    sentiment_resp = MagicMock()
    sentiment_resp.content = json.dumps(
        {"sentiment": sentiment, "intensity": intensity}
    )
    quality_resp = MagicMock()
    quality_resp.content = json.dumps({"quality": quality})
    llm.chat.side_effect = [sentiment_resp, quality_resp]
    return llm


# ---------------------------------------------------------------------------
# 1. Initial state
# ---------------------------------------------------------------------------

def test_initial_state(tmp_path):
    llm = MagicMock()
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    state = engine.get_state()

    assert state.mood_value == 50
    assert state.energy == 100
    assert state.bond_level == 1


# ---------------------------------------------------------------------------
# 2. Mood prompt for stranger level
# ---------------------------------------------------------------------------

def test_get_mood_prompt_stranger(tmp_path):
    llm = MagicMock()
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    prompt = engine.get_mood_prompt()

    assert "礼貌" in prompt or "距离" in prompt


# ---------------------------------------------------------------------------
# 3. Mood prompt for friend level (Lv.3, total_bond >= 51)
# ---------------------------------------------------------------------------

def test_get_mood_prompt_friend(tmp_path):
    llm = MagicMock()
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    # Manually set bond data to simulate level 3
    engine._bond.data["total_bond"] = 60
    engine._bond.data["level"] = 3
    engine._bond.data["level_name"] = "Friend"
    engine._bond._save()

    prompt = engine.get_mood_prompt()
    assert "朋友" in prompt


# ---------------------------------------------------------------------------
# 4. Rest restores energy
# ---------------------------------------------------------------------------

def test_rest_restores_energy(tmp_path):
    llm = MagicMock()
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    engine._energy = 10

    result = engine.rest()
    assert result == 80
    assert engine.energy == 80


# ---------------------------------------------------------------------------
# 5. process_turn consumes energy
# ---------------------------------------------------------------------------

def test_process_turn_consumes_energy(tmp_path):
    llm = _mock_llm(sentiment="neutral", intensity=1, quality="medium")
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    energy_before = engine.energy

    engine.process_turn("hello", "hi there")

    assert engine.energy < energy_before
    # neutral sentiment → no mood change, medium quality → 1 bond point
    assert engine.energy == energy_before - 3


# ---------------------------------------------------------------------------
# 6. process_turn calls LLM for mood analysis
# ---------------------------------------------------------------------------

def test_process_turn_calls_llm_for_mood(tmp_path):
    llm = _mock_llm(sentiment="neutral", intensity=1, quality="medium")
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))

    engine.process_turn("I'm happy!", "Glad to hear that!")

    assert llm.chat.call_count == 2
    # First call is sentiment analysis
    first_call_args = llm.chat.call_args_list[0]
    messages = first_call_args.kwargs.get("messages") or first_call_args[1].get("messages") or first_call_args[0][0]
    # The messages list should contain the sentiment analysis system prompt
    system_content = messages[0]["content"]
    assert "sentiment" in system_content.lower() or "情感" in system_content


# ---------------------------------------------------------------------------
# 7. process_turn adds bond points
# ---------------------------------------------------------------------------

def test_process_turn_adds_bond(tmp_path):
    llm = _mock_llm(sentiment="neutral", intensity=1, quality="medium")
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    bond_before = engine.bond.total

    engine.process_turn("hello", "hi there")

    assert engine.bond.total == bond_before + 1


# ---------------------------------------------------------------------------
# 8. process_turn level up (bond near Lv.2 threshold)
# ---------------------------------------------------------------------------

def test_process_turn_level_up(tmp_path):
    llm = _mock_llm(sentiment="neutral", intensity=1, quality="high")
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    # Set total_bond to 20; high quality adds 3 → 23, crosses Lv.2 threshold (21)
    engine._bond.data["total_bond"] = 20
    engine._bond._save()

    result = engine.process_turn("hello", "hi there")

    assert result["level_up"] is True
    assert engine.bond.level == 2


# ---------------------------------------------------------------------------
# 9. Mood prompt does not limit conversation length
# ---------------------------------------------------------------------------

def test_mood_prompt_low_energy(tmp_path):
    llm = MagicMock()
    engine = EmotionEngine(llm=llm, bond_path=_bond_path(tmp_path))
    engine._energy = 15

    prompt = engine.get_mood_prompt()
    assert "累" not in prompt
    assert "精力" not in prompt
