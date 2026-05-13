# MyAgent - Personal AI Pet/Assistant Framework

## Overview

A personal AI agent framework built from scratch (no LangChain/CrewAI) for learning agent architecture and interview preparation. The agent acts as an "electronic pet" with personality, long-term memory, and tool-use capabilities.

## Tech Stack

- **Language**: Python
- **LLM**: OpenAI Compatible API (ZAI), via `openai` SDK only
- **Vector Store**: ChromaDB (embedded, zero infrastructure)
- **Interface**: CLI first, web UI later
- **Agent Mode**: Single agent, multi-agent extensible

## Architecture

```
┌─────────────────────────────────────────┐
│                  CLI                     │
│            (用户交互入口)                  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│              Agent 核心                   │
│  ┌─────────────────────────────────┐    │
│  │  对话循环 (ReAct Loop)           │    │
│  │  用户输入 → LLM → 工具调用/回复   │    │
│  └──────────────┬──────────────────┘    │
│                 │                        │
│  ┌──────────────▼──────────────────┐    │
│  │        Context Manager          │    │
│  │  组装 system prompt + 记忆       │    │
│  │  + 工具定义 + 对话历史           │    │
│  └──┬──────────┬──────────┬────────┘    │
│     │          │          │              │
│  ┌──▼───┐ ┌───▼──┐ ┌────▼─────┐        │
│  │Memory│ │Tools │ │   LLM    │        │
│  │短期   │ │Registry│ │ Client  │        │
│  │长期   │ │      │ │(OpenAI)  │        │
│  │RAG   │ │      │ │ Compat)  │        │
│  └──────┘ └──────┘ └──────────┘        │
└─────────────────────────────────────────┘
```

## Module Design

### 1. LLMClient (`core/llm.py`) ~100 lines

Wraps the `openai` SDK for API calls.

```python
class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str): ...
    def chat(self, messages: list, tools: list = None, stream: bool = True) -> Response: ...
```

- Minimal wrapper over `openai` SDK, no extra abstraction
- Streaming output yields tokens, CLI layer handles printing
- Returns unified `Response` object (content + tool_calls) regardless of underlying model
- Configuration via `.env` file (base_url, api_key, model)

### 2. ToolRegistry (`core/tools.py`) ~150 lines

Registers and executes tools using decorator + type annotations.

```python
@tool(name="web_search", description="搜索网页")
def web_search(query: str) -> str: ...

class ToolRegistry:
    def register(self, func) -> None: ...
    def get_schemas(self) -> list[dict]: ...
    def execute(self, name: str, args: dict) -> str: ...
```

- `@tool` decorator + Python type annotations auto-generate JSON schema for function calling
- A tool is just a regular Python function with string I/O
- `get_schemas()` outputs directly feed into `LLMClient.chat(tools=...)`
- `execute()` wraps in try-catch; tool errors don't crash the loop, error message returns to LLM
- Built-in tools: `web_search`, `read_file`, `shell_exec`

### 3. Memory (`core/memory.py`) ~200 lines

Manages short-term (conversation history) and long-term (vector retrieval) memory.

```python
class Memory:
    def __init__(self, chroma_path: str = "./data/memory"): ...
    def add_message(self, role: str, content: str) -> None: ...
    def save_long_term(self, content: str, metadata: dict) -> None: ...
    def recall(self, query: str, top_k: int = 5) -> list[str]: ...
    def get_context(self, max_tokens: int = 4000) -> list[dict]: ...
    def clear(self) -> None: ...
```

**Short-term memory:** Message list, truncated by token count via `get_context()`. Keeps recent messages + system prompt, prevents context window overflow.

**Long-term memory:** After each conversation turn, LLM extracts key information (user preferences, important facts, task results) and stores in ChromaDB. At the start of next turn, `recall()` retrieves relevant memories based on user input and injects into system prompt.

**ChromaDB collection structure:**
```
collection "long_term_memory"
├── {content: "用户喜欢暗色主题", metadata: {type: "preference", timestamp: ...}}
├── {content: "用户正在做 agent 项目", metadata: {type: "fact", timestamp: ...}}
```

**Why LLM extraction instead of raw storage:** Raw conversations are long and noisy. Extracted key information has higher retrieval precision and lower storage cost.

### 4. ContextManager (`core/context.py`) ~150 lines

Assembles the complete message list sent to LLM.

```python
class ContextManager:
    def __init__(self, system_prompt: str, memory: Memory, tool_registry: ToolRegistry): ...
    def build(self, user_input: str) -> list[dict]: ...
    def _build_system_prompt(self) -> str: ...
```

- Single source of truth for message assembly; Agent loop never constructs messages directly
- Final message structure sent to LLM:
  ```
  [system]  人格设定 + 长期记忆检索结果
  [user]    之前的对话...
  [assistant] ...
  [user]    当前用户输入
  ```
- Persona defined in `data/persona.md`, editable anytime
- Token budget: system prompt + memory ~1000, conversation history ~3000, reply ~2000. Total within model's context window

### 5. Agent (`core/agent.py`) ~200 lines

The ReAct loop - the core conversation cycle.

```python
class Agent:
    def __init__(self, llm: LLMClient, memory: Memory, tools: ToolRegistry, context_manager: ContextManager): ...
    def run(self, user_input: str) -> str: ...
```

**ReAct pattern:** Reason (LLM thinks) → Act (call tool) → Observe (see result) → Think again. Loop until LLM outputs final reply without tool calls.

**Loop safety:**
- Max iteration limit (default 10) to prevent infinite tool calling
- Single tool execution timeout (default 30 seconds)
- Tool errors don't interrupt; error message returns to LLM to decide next step

**Memory save timing:**
- After each conversation turn, call `save_long_term` once to extract memorable information
- Not every message — too noisy

### 6. CLI (`cli/main.py`) ~100 lines

Terminal interaction interface.

**Slash commands:**

| Command | Function |
|---|---|
| `/help` | Show help |
| `/quit` | Exit |
| `/clear` | Clear current conversation (short-term memory) |
| `/history` | View conversation history |
| `/persona` | View/modify persona |
| `/memory` | View long-term memory count |

- Entry via `python -m myagent`
- Streaming output via `sys.stdout.write` for character-by-character printing

## Project Structure

```
myagent/
├── core/
│   ├── __init__.py
│   ├── llm.py            # LLMClient
│   ├── tools.py          # ToolRegistry + @tool decorator
│   ├── memory.py         # Memory (short-term + long-term)
│   ├── context.py        # ContextManager
│   └── agent.py          # Agent (ReAct loop)
├── cli/
│   ├── __init__.py
│   └── main.py           # CLI entry point
├── tools/                # Tool implementations
│   ├── web_search.py
│   ├── file_ops.py
│   └── shell.py
├── data/
│   ├── memory/           # ChromaDB persistence directory
│   └── persona.md        # Persona definition
├── .env                  # API configuration
├── pyproject.toml
└── README.md
```

## Estimated Code Volume

~900 lines of core code. Each module in a single file with clear responsibilities.

## Interview Value

This project demonstrates understanding of:

- **Tool calling**: Function schema auto-generation, LLM decision loop, result feedback
- **Memory architecture**: Short-term context window management, long-term vector retrieval, LLM-based information extraction
- **ReAct pattern**: Reasoning-acting loop with safety guards
- **Context management**: Token budget allocation, prompt assembly, persona injection
- **RAG**: Vector storage, similarity search, retrieval-augmented generation
