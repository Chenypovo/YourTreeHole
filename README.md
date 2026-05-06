![Murphy Agent](assets/murphy.svg)

# Murphy

Personal AI pet/assistant framework built from scratch.

## What it does

An "electronic pet" with personality that remembers you and can use tools.

- **Tool calling**: Web search, file I/O, shell commands — extensible via decorators
- **Long-term memory**: Remembers your preferences and facts across sessions via vector search
- **ReAct loop**: Reason → Act → Observe cycle with safety guards
- **Persona system**: Define personality via a markdown file

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your OpenAI Compatible API settings

# Run
murphy
```

## Architecture

```
CLI → Agent (ReAct Loop) → LLMClient (OpenAI Compat)
                           → ToolRegistry (extensible)
                           → Memory (short-term + ChromaDB long-term)
                           → ContextManager (prompt assembly)
```

## Adding Tools

```python
from core.tools import tool

@tool(name="my_tool", description="What it does")
def my_tool(param: str) -> str:
    return "result"
```

Register in `cli/main.py` and you're done.

## Tech Stack

- Python 3.11+
- openai SDK (OpenAI Compatible API)
- ChromaDB (embedded vector store)

## License

MIT
