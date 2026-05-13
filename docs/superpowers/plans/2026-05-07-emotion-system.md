# Emotion System & Desktop Pet — Implementation Plan

**Spec**: `docs/superpowers/specs/2026-05-07-emotion-system-design.md`

## Architecture

```
core/emotion.py   ← EmotionEngine (facade: mood + bond + energy + easter eggs)
core/mood.py      ← Mood state (session-scoped, 0-100)
core/bond.py      ← Bond persistence (JSON, levels, easter eggs)
cli/pet_renderer.py ← ASCII pet rendering
data/bond.json    ← auto-created persistent bond data
data/pet.json     ← auto-created pet appearance
```

Integration points:
- `Agent.run()/run_stream()` → call `emotion.process_turn()` after reply
- `ContextManager.build()` → inject `emotion.get_mood_prompt()` into system prompt
- `cli/main.py` → render pet after each turn, new commands, first-run setup

No new dependencies.

---

## Step 1: Mood module (`core/mood.py`)

Write `core/mood.py` with a `Mood` dataclass:

```python
# core/mood.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Mood:
    value: int = 50  # 0-100, default calm

    def adjust(self, delta: int) -> None:
        self.value = max(0, min(100, self.value + delta))

    @property
    def label(self) -> str:
        if self.value >= 75:
            return "happy"
        if self.value >= 40:
            return "calm"
        if self.value >= 20:
            return "sad"
        return "sad"

    @property
    def hearts(self) -> str:
        """Return a 5-symbol bar: ♥ for filled, ♦ for empty."""
        filled = round(self.value / 20)
        return "♥" * filled + "♦" * (5 - filled)
```

**Tests** (`tests/test_mood.py`):
- `test_default_mood_is_50` — new Mood().value == 50
- `test_adjust_positive_clamps_100` — mood.adjust(60) → 100
- `test_adjust_negative_clamps_0` — mood.adjust(-80) → 0
- `test_label_happy` — mood=85 → "happy"
- `test_label_calm` — mood=50 → "calm"
- `test_label_sad` — mood=15 → "sad"
- `test_hearts_full` — mood=100 → "♥♥♥♥♥"
- `test_hearts_partial` — mood=60 → "♥♥♥♦♦"

---

## Step 2: Bond module (`core/bond.py`)

Write `core/bond.py` with bond level definitions, persistence, and easter egg detection.

```python
# core/bond.py
from __future__ import annotations
import json
import time
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
            self.data = dict(DEFAULT_BOND_DATA)
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
            pass  # same day, no change
        elif last:
            from datetime import date as date_cls
            last_date = date_cls.fromisoformat(last)
            if (date_cls.today() - last_date).days == 1:
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

        # 7 consecutive days
        if "anniversary_7d" not in eggs and self.data["consecutive_days"] >= 7:
            eggs.append("anniversary_7d")
            triggered.append("anniversary_7d")

        # Bond Lv.4 — diary unlock
        if "diary_unlock" not in eggs and self.data["level"] >= 4:
            eggs.append("diary_unlock")
            triggered.append("diary_unlock")

        # Bond Lv.5 — /secret command
        if "secret_unlock" not in eggs and self.data["level"] >= 5:
            eggs.append("secret_unlock")
            triggered.append("secret_unlock")

        # 50+ turns in one session (caller tracks session turns)
        # Late night chat (2-4 AM) — caller checks time

        self.data["easter_eggs_triggered"] = eggs
        self._save()
        return triggered

    def check_return_after_absence(self) -> bool:
        """Check if user was absent 3+ days."""
        last = self.data.get("last_chat_date")
        if not last:
            return False
        from datetime import date as date_cls
        last_date = date_cls.fromisoformat(last)
        return (date_cls.today() - last_date).days >= 3

    @property
    def has_secret(self) -> bool:
        return "secret_unlock" in self.data.get("easter_eggs_triggered", [])
```

**Tests** (`tests/test_bond.py`):
- `test_default_bond_is_zero` — new bond, total=0, level=1
- `test_add_points_persists` — bond.add(5), reload from file, total==5
- `test_level_up` — bond starts at 0, add 25 → level becomes 2 (acquaintance at 21)
- `test_add_returns_true_on_level_up` — level changed → returns True
- `test_consecutive_days_increments` — simulate two consecutive days
- `test_consecutive_days_resets` — gap >1 day → resets to 1
- `test_easter_egg_7_days` — set consecutive_days=7, check anniversary triggered
- `test_easter_egg_lv4_diary` — bond reaches lv4, diary_unlock triggered
- `test_easter_egg_no_repeat` — calling check again doesn't re-trigger
- `test_return_after_absence` — last_chat_date 4 days ago → True

---

## Step 3: Pet renderer (`cli/pet_renderer.py`)

Write the ASCII pet renderer with built-in templates and mood-based expression switching.

```python
# cli/pet_renderer.py
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass

# 8 built-in pet templates (happy/calm/sad/tired for each)
BUILTIN_PETS = {
    "cat": {
        "name": "小猫",
        "species": "猫",
        "art": {
            "happy": "  ╭─────╮\n  │ ◕ ◡ ◕ │\n  │  ╰︶╯  │\n  ╰──┬──╯\n     U U",
            "calm":  "  ╭─────╮\n  │ - . - │\n  │  ╰──╯  │\n  ╰──┬──╯\n     U U",
            "sad":   "  ╭─────╮\n  │ . _ . │\n  │  ╰──╯  │\n  ╰──┬──╯\n     U U",
            "tired": "  ╭─────╮\n  │ - - z │\n  │  ╰──╯  │\n  ╰──┬──╯\n     u u",
        },
    },
    "dog": { ... },  # similar structure
    # ... dragon, robot, rabbit, fox, owl, penguin
}

@dataclass
class PetState:
    """Snapshot passed from EmotionEngine for rendering."""
    bond_level: int
    bond_name: str
    mood_hearts: str
    mood_label: str
    energy: int

def load_pet(path: str = "./data/pet.json") -> dict:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None

def save_pet(pet_data: dict, path: str = "./data/pet.json") -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(pet_data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_pet_art(pet_data: dict, mood_label: str) -> str:
    """Return ASCII art matching the current mood."""
    return pet_data["art"].get(mood_label, pet_data["art"]["calm"])

def render_pet(pet_data: dict, state: PetState) -> str:
    """Render the full pet + status bar as a single string."""
    art = get_pet_art(pet_data, state.mood_label)
    # Build status bar: [Lv.3 Friend | ♥♥♥♥♦ | ⚡87 | mood:happy]
    status = f"  [{state.bond_name} | {state.mood_hearts} | ⚡{state.energy} | {state.mood_label}]"
    # Combine art lines with status
    art_lines = art.split("\n")
    # Place status to the right of the pet
    lines = []
    for i, line in enumerate(art_lines):
        if i == 0:
            lines.append(f"{line}   {status}")
        else:
            lines.append(line)
    return "\n".join(lines)
```

**Tests** (`tests/test_pet_renderer.py`):
- `test_load_pet_returns_none_when_missing` — no file → None
- `test_save_and_load_pet` — save → load → matches
- `test_get_pet_art_happy` — returns happy art
- `test_get_pet_art_falls_back_to_calm` — unknown mood → calm art
- `test_render_pet_includes_status` — output contains bond name, hearts, energy
- `test_builtin_pets_have_all_expressions` — every builtin has happy/calm/sad/tired keys

---

## Step 4: EmotionEngine (`core/emotion.py`)

The facade that ties mood, bond, energy together. Provides `process_turn()` and `get_mood_prompt()`.

```python
# core/emotion.py
from __future__ import annotations
import json
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

        # Consume energy (2-5 per turn, tool calls cost more)
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
        # Session-specific easter eggs
        if self._session_turns >= 50 and "marathon_chat" not in self._bond.data.get("easter_eggs_triggered", []):
            self._bond.data.setdefault("easter_eggs_triggered", []).append("marathon_chat")
            new_eggs.append("marathon_chat")
            self._bond._save()

        # Late night check (2-4 AM)
        import datetime
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
```

**Tests** (`tests/test_emotion.py`):
- `test_initial_state` — mood=50, energy=100, bond=0
- `test_get_mood_prompt_stranger` — default → contains "礼貌"
- `test_get_mood_prompt_friend` — set bond to lv3 → contains "朋友"
- `test_rest_restores_energy` — energy → 80
- `test_process_turn_consumes_energy` — after 1 turn, energy < 100
- `test_process_turn_calls_llm_for_mood` — mock LLM, verify chat called with sentiment prompt
- `test_process_turn_adds_bond` — mock LLM returns medium quality → bond increases
- `test_process_turn_level_up` — simulate bond reaching lv2 threshold
- `test_mood_prompt_low_energy` — set energy < 20 → prompt mentions tired

---

## Step 5: Integrate into Agent (`core/agent.py`)

Modify `Agent.__init__` to accept optional `emotion` parameter:

```python
# In Agent.__init__, add:
self.emotion: EmotionEngine | None = None

def attach_emotion(self, emotion: EmotionEngine) -> None:
    self.emotion = emotion
```

In `run()`, after `self._maybe_save_long_term()`:
```python
emotion_events = None
if self.emotion:
    emotion_events = self.emotion.process_turn(user_input, response.content)
```

In `run_stream()`, same place after the final reply.

Add `from core.emotion import EmotionEngine` (lazy import or top-level).

**Tests** (`tests/test_agent.py` — extend existing):
- `test_emotion_process_turn_called_after_reply` — mock emotion, verify process_turn called
- `test_no_emotion_no_error` — no emotion attached, agent still works

---

## Step 6: Integrate into ContextManager (`core/context.py`)

Add `emotion` parameter to `ContextManager`:

```python
def __init__(self, persona, memory, tool_registry, model_name=None, emotion=None):
    ...
    self._emotion = emotion

def _build_system_prompt(self, user_input):
    parts = [self._persona]
    if self._emotion:
        parts.append(f"\n\n## 情感状态:\n{self._emotion.get_mood_prompt()}")
    ...  # rest unchanged
```

**Tests** (`tests/test_context.py` — extend existing):
- `test_build_includes_mood_prompt_when_emotion_attached` — mock emotion, verify mood prompt in system message
- `test_build_without_emotion_unchanged` — no emotion → same as before

---

## Step 7: Integrate into CLI (`cli/main.py`)

This is the biggest integration step. Changes:

1. **`create_agent()`** — create EmotionEngine, attach to agent and context
2. **First-run pet setup** — check if `data/pet.json` exists, if not run interactive setup
3. **Render pet after each turn** — call `render_pet()` after streaming completes
4. **New commands**: `/mood`, `/rest`, `/pet`, `/secret`
5. **Easter egg display** — after process_turn, show easter egg messages
6. **Update `/status`** — show emotion state

Key changes to `main()` loop:
```python
# After streaming completes:
if agent.emotion:
    events = agent.emotion.process_turn(user_input, reply)  # already called in agent
    # Show easter eggs
    for egg in events.get("easter_eggs", []):
        console.print(Panel(easter_egg_message(egg), style="bold yellow"))
    # Render pet
    pet = load_pet()
    state = agent.emotion.get_state()
    console.print(render_pet(pet, state))
```

**Tests** (`tests/test_cli.py` — extend existing):
- `test_mood_command_shows_state` — mock emotion, verify output
- `test_rest_command_restores_energy` — mock emotion.rest, verify called
- `test_pet_command_triggers_setup` — mock LLM, verify pet.json created
- `test_status_includes_emotion` — mock emotion, verify mood/bond in output

---

## Step 8: First-run pet setup flow

Add a `first_run_setup()` function in `cli/main.py` or `cli/pet_renderer.py`:

```python
def first_run_setup(llm, console) -> dict:
    """Interactive first-run pet creation. Returns pet_data dict."""
    console.print(Panel("描述一下你想要的宠物形象：\n比如\"一只戴眼镜的猫\"、\"一条小火龙\"", title="Welcome to Murphy!"))

    description = console.input("[bold cyan]❯ [/bold cyan]")

    # Generate ASCII art via LLM
    console.print("[dim]Murphy 正在想象自己的样子...[/dim]")
    art = _generate_pet_art(llm, description)

    console.print(art)
    choice = console.input("你喜欢这个形象吗？(y/n) ")

    if choice.strip().lower() != "y":
        # Offer built-in templates as fallback
        return _pick_builtin_template(console)

    return {"name": description[:10], "species": description, "art": art}
```

**Tests**:
- `test_first_run_creates_pet_json` — mock input/LLM, verify file created
- `test_first_run_fallback_to_builtin` — user says "n" → picks template

---

## Execution Order

| Step | Files | Dependencies | Tests |
|------|-------|-------------|-------|
| 1 | `core/mood.py`, `tests/test_mood.py` | None | 8 tests |
| 2 | `core/bond.py`, `tests/test_bond.py` | None | 10 tests |
| 3 | `cli/pet_renderer.py`, `tests/test_pet_renderer.py` | None | 6 tests |
| 4 | `core/emotion.py`, `tests/test_emotion.py` | Steps 1, 2 | 9 tests |
| 5 | `core/agent.py` | Step 4 | 2 tests |
| 6 | `core/context.py` | Step 4 | 2 tests |
| 7 | `cli/main.py` | Steps 4, 5, 6 | 4 tests |
| 8 | First-run setup (in `cli/main.py` or `cli/pet_renderer.py`) | Steps 3, 4 | 2 tests |

Steps 1, 2, 3 are fully independent and can run in parallel.

---

## Easter Egg Messages

```python
EASTER_EGG_MESSAGES = {
    "anniversary_7d": "🎉 我们已经连续聊天 7 天了！Murphy 为你写了一首诗...",
    "diary_unlock": "📖 Murphy 开始写日记了，偶尔会和你分享自己的想法",
    "secret_unlock": "🔐 你解锁了隐藏命令 /secret",
    "marathon_chat": "💬 今天聊得真开心，好久没这么畅快了",
    "late_night": "🌙 这么晚还不睡？我陪你",
}
```

For `return_after_absence`: handled in CLI startup, not in process_turn:
```
"你终于来了，我等了好久" (displayed as a special greeting on session start)
```
