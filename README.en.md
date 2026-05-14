![Murphy Agent](assets/murphy.svg)

# MURPHY

[![中文](https://img.shields.io/badge/中文-README-315B46?style=for-the-badge)](README.md)

Murphy is a learning project for building a personal AI treehole.

It is not designed as a task-execution agent. The project focuses on a smaller but important question: when people use AI as a private place to talk, how can the AI keep remembering their thoughts, preferences, emotional context, and important life events over a long period of time?

## Goal

Most chat models eventually forget earlier context once the conversation grows too long. Murphy tries to be a simpler, memory-focused treehole:

- Listen to the user carefully.
- Store raw conversations locally.
- Extract durable long-term memories from conversations.
- Naturally bring up important previous events when a new session starts.
- Let the user inspect, add, and delete memories.

This is still a personal learning project, not a production-ready product.

## Examples

When a new session starts, Murphy can remember what the user shared before and naturally ask about recent progress.

![Proactive greeting example](assets/examples/proactive-greeting.png)

In normal conversations, Murphy behaves more like a quiet treehole than a task agent.

![Chat example](assets/examples/chat-example.png)

## Features

- **Raw journal**: every conversation turn is saved locally to `data/journal.md`.
- **Long-term memory**: important information is summarized into `data/memories.md`.
- **User profile**: stable user information is maintained in `data/user_profile.md`.
- **Relevant recall**: recent and relevant memories are injected into the model context.
- **Proactive greeting**: Murphy can mention unresolved events when a new session starts.
- **Custom persona**: users can define the treehole's personality on first startup.
- **Memory management**: users can view, add, and delete long-term memories.

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` with your OpenAI-compatible API settings:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1-mini
```

Start the CLI:

```bash
murphy
```

If you use the web UI:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:7860/
```

## Configuration

Non-secret settings live in `config/settings.toml`:

```toml
[llm]
# base_url = "https://api.z.ai/api/coding/paas/v4"
# model = "glm-5.1"

[persona]
path = "persona.md"

[memory]
data_dir = "./data"
enable_gating = true
profile_update_interval = 5
```

Do not put API keys in `config/settings.toml`. API keys should stay in your local `.env`.

## Local Data

Conversation data is stored locally under `data/` by default:

```text
data/
├── journal.md        # raw conversation journal
├── memories.md       # long-term memories
├── user_profile.md   # user profile
└── persona.md        # custom treehole personality
```

These files contain the user's private data and should not be committed to the repository.

## Architecture

```text
CLI / Web
  -> Agent
  -> ContextManager
     -> persona
     -> user_profile.md
     -> relevant memories
     -> recent conversation
  -> LLMClient
  -> FileMemory
     -> journal.md
     -> memories.md
```

The core idea is: `journal.md` stores the raw source of truth, `memories.md` stores durable long-term memories, and `user_profile.md` stores a structured summary of the user.

## CLI Commands

| Command | Description |
| --- | --- |
| `/help` or `/` | Show commands |
| `/profile` | View the user profile |
| `/memories` | View long-term memories |
| `/remember <text>` | Manually add a memory |
| `/forget <id>` | Delete a memory |
| `/persona` | View the treehole persona |
| `/reset` | Clear the current session only |
| `/quit` | Exit |

## Status

This is a personal learning project. The current focus is making long-term memory, user profiling, context recall, and local data management clear and reliable before polishing the web experience further.
