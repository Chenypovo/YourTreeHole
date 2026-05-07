# Murphy Emotion System & Desktop Pet Design

## Overview

Add an emotional system and terminal desktop pet to Murphy, making it the first agent framework with genuine emotional intelligence and gamified relationship progression.

## Emotion Dimensions

Three dimensions, each affecting different aspects of Murphy's behavior:

| Dimension | Scope | Range | Affects |
|---|---|---|---|
| **mood** | Short-term (per session) | 0-100, default 50 | Reply tone, emoji usage, chattiness |
| **bond** | Long-term (persistent) | 0+ | Relationship level, unlocked abilities, reply intimacy |
| **energy** | Per-session (depleting) | 0-100, default 100 | Reply detail level, proactiveness |

### Mood

- Starts at 50 (calm) each session
- Adjusted per turn by LLM mood analysis (positive/neutral/negative user input)
- Compliments / successful tasks → +5~15
- Criticism / task failures → -5~15
- Natural decay toward 50 over time (not implemented in v1)

### Bond

- Persistent across sessions, stored in `data/bond.json`
- Each effective interaction → +1~3 (LLM judges interaction quality)
- Never decreases (no punishment for inactivity)
- LLM evaluates: did the user share something personal? Did Murphy help meaningfully?

### Energy

- Starts at 100 each session
- Each turn costs 2~5 energy (complex tool calls cost more)
- Below 20: replies become brief, Murphy says it's tired
- `/rest` command restores energy to 80
- New session auto-restores to 100

## Bond Levels

| Level | Name | Bond Required | Behavior |
|---|---|---|---|
| Lv.1 | Stranger | 0-20 | Polite, formal, uses です/ます style |
| Lv.2 | Acquaintance | 21-50 | Relaxed tone, remembers preferences |
| Lv.3 | Friend | 51-80 | Jokes occasionally, proactive caring |
| Lv.4 | Close Friend | 81-120 | Deep understanding, anticipates needs |
| Lv.5 | Soulmate | 121+ | Fully personalized, shares "own thoughts" |

## Hidden Easter Eggs

Not documented in README. Users discover them naturally.

| Trigger | Easter Egg |
|---|---|
| 7 consecutive days of conversation | Murphy celebrates "anniversary", writes a poem |
| Bond reaches Lv.4 | Murphy starts keeping a "diary", occasionally shares thoughts |
| Chatting between 2:00-4:00 AM | Murphy: "这么晚还不睡？我陪你" |
| 50+ turns in single conversation | Murphy: "今天聊得真开心，好久没这么畅快了" |
| 3+ days without interaction | Murphy pouts on return: "你终于来了，我等了好久" |
| Bond reaches Lv.5 | Unlocks hidden `/secret` command, Murphy tells a story unique to your relationship |

## Mood Injection

Emotion state is NOT passed as numbers to the LLM. Instead, natural language descriptions are injected into the system prompt:

```
mood=85, bond=Lv.3, energy=90
→ "你和用户是朋友了，可以适当开玩笑。你现在心情很好，很活跃，想多聊聊。精力充沛。"

mood=20, bond=Lv.1, energy=15
→ "你刚认识这个用户，保持礼貌和距离。你有点低落，不想说太多。你有点累了，回复简短一些。"
```

This makes the LLM naturally embody the emotional state rather than mechanically following rules.

## Terminal Desktop Pet

ASCII art displayed in the CLI after each interaction, reflecting Murphy's current emotional state.

### Status Bar Format

```
  ╭─────╮
  │ ◕ ◡ ◕ │   [Lv.3 Friend | ♥♥♥♥♦ | ⚡87 | mood:happy]
  │  ╰︶╯  │
  ╰──┬──╯
     U U
```

- Left: ASCII pet with mood-based expression
- Right: Bond level, mood bar (5 hearts), energy bar, mood label

### Mood Expressions

Each pet has 4 expression variants:
- **happy**: eyes bright, mouth up
- **calm**: neutral face
- **sad**: droopy eyes
- **tired**: half-closed eyes, small body

### First-Run Pet Creation

On first launch, Murphy asks the user to describe their ideal pet:

```
╭──────────────────────────────────────────╮
│  Welcome to Murphy!                      │
│                                          │
│  描述一下你想要的宠物形象：                │
│  比如"一只戴眼镜的猫"、"一条小火龙"       │
╰──────────────────────────────────────────╯

❯ 一只圆滚滚的橘猫，头上有一根呆毛

  Murphy 正在想象自己的样子...

  [generated ASCII art]

  你喜欢这个形象吗？ (y/n/重新描述)
```

**Three-track pet system:**

1. **LLM Generation (default)**: User describes → LLM generates 4 mood variants → saved
2. **Built-in Templates**: 8-10 presets (cat, dog, dragon, robot, rabbit, fox, owl, penguin) with ready-made expressions
3. **Manual Custom**: User edits `data/pet.json` directly with custom ASCII art

### pet.json Structure

```json
{
  "name": "小橘",
  "species": "橘猫",
  "art": {
    "happy": "  ╭─────╮\n  │ ◕ ◡ ◕ │\n  │  ╰︶╯  │\n  ╰──┬──╯\n     U U",
    "calm":  "  ╭─────╮\n  │ - . - │\n  │  ╰──╯  │\n  ╰──┬──╯\n     U U",
    "sad":   "  ╭─────╮\n  │ . _ . │\n  │  ╰──╯  │\n  ╰──┬──╯\n     U U",
    "tired": "  ╭─────╮\n  │ - - z │\n  │  ╰──╯  │\n  ╰──┬──╯\n     u u"
  }
}
```

## File Structure

```
core/
├── emotion.py          # EmotionEngine - main interface
├── mood.py             # Mood state management
├── bond.py             # Bond persistence + level + easter eggs
data/
├── bond.json           # Persistent bond data (auto-created)
├── pet.json            # Pet appearance (auto-created on first run)
cli/
├── pet_renderer.py     # ASCII pet rendering in terminal
```

## New CLI Commands

| Command | Function |
|---|---|
| `/mood` | Show current mood, bond level, energy |
| `/rest` | Let Murphy rest, restore energy |
| `/pet` | Re-describe pet appearance |
| `/secret` | Hidden command, unlocked at Lv.5 |

## bond.json Structure

```json
{
  "total_bond": 87,
  "level": 3,
  "level_name": "Friend",
  "first_chat_date": "2026-05-07",
  "total_turns": 142,
  "consecutive_days": 5,
  "last_chat_date": "2026-05-07",
  "easter_eggs_triggered": [],
  "achievements": []
}
```

## Integration with Existing System

### EmotionEngine Integration Points

1. **Agent.run() / Agent.run_stream()** — call `emotion.process_turn()` after each assistant reply
2. **ContextManager.build()** — inject mood prompt from `emotion.get_mood_prompt()` into system prompt
3. **CLI main loop** — render pet after each turn via `pet_renderer.render(emotion.get_state())`
4. **Memory gating** — bond level affects memory save behavior (higher bond = more eager to remember)

### Data Flow

```
User Input
    ↓
Agent.run()
    ↓
LLM Response
    ↓
EmotionEngine.process_turn(user_input, response)
    ├── MoodAnalyzer (LLM call) → adjust mood +1~-1
    ├── BondTracker.update() → adjust bond +1~3
    ├── EnergyTracker.consume() → reduce energy
    ├── EasterEggChecker.check() → trigger easter eggs
    ↓
ContextManager.build() injects mood_prompt
    ↓
PetRenderer.render(state) displays ASCII pet
```

## Dependencies

No new external dependencies. All emotion analysis uses the existing LLM client.
