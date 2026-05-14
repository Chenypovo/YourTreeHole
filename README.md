![Murphy Agent](assets/murphy.svg)

# MURPHY

Murphy is a small learning project for exploring a personal AI treehole: a local chat companion that keeps long-term notes about the user instead of relying only on the model context window.

It is not a production product. I use it to learn how memory, profiles, streaming chat, and CLI UX fit together.

## What It Does

- **Raw journal**: saves each conversation turn locally in `data/journal.md`.
- **Long-term memory**: stores selected durable memories in `data/memories.md`.
- **User profile**: periodically summarizes stable user information into `data/user_profile.md`.
- **Relevant recall**: injects recent and query-related memories into the model context.
- **CLI commands**: inspect and manage memory from the terminal.

## Examples

Murphy can remember what you shared before and naturally bring it up when you start a new session.

![Proactive greeting example](assets/examples/proactive-greeting.png)

It is designed as a quiet treehole for ongoing conversations, not a task agent.

![Chat example](assets/examples/chat-example.png)

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env
murphy
```

Edit `.env` with your OpenAI-compatible API settings before running.

## Configuration

Main settings live in `config/settings.toml`.

```toml
[llm]
model = "glm-4.7"

[persona]
path = "persona.md"

[memory]
data_dir = "./data"
enable_gating = true
profile_update_interval = 5
```

You can define the agent's personality in `persona.md`.

## Commands

| Command | Description |
| --- | --- |
| `/help` or `/` | Show commands |
| `/profile` | View the user profile |
| `/memories` | List long-term memories |
| `/remember <text>` | Manually add a memory |
| `/forget <id>` | Delete a memory |
| `/mood` | View emotional state |
| `/persona` | View persona text |
| `/reset` | Clear the current session only |
| `/quit` | Exit |

## Data And Privacy

Runtime data is stored under `data/` and should stay local. This folder can contain private journal entries, memories, profile summaries, and relationship state. Do not commit it unless you intentionally want to publish that data.

## Architecture

```text
CLI / Streamlit
  -> Agent
  -> ContextManager
     -> persona.md
     -> data/user_profile.md
     -> relevant + recent memories
     -> short-term session history
  -> LLMClient
  -> FileMemory
     -> data/journal.md
     -> data/memories.md
```

## Status

This is a personal learning repo. The current focus is making the memory layer reliable and understandable before adding more UI or agent features.
