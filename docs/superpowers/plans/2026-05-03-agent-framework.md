# MyAgent Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal AI pet/assistant framework from scratch with tool calling, long/short-term memory, RAG, and CLI interaction.

**Architecture:** 6 modules with clear single responsibilities — LLMClient wraps the OpenAI SDK, ToolRegistry manages tool registration/execution via decorators, Memory handles short-term (message list) and long-term (ChromaDB vector) storage, ContextManager assembles the full prompt, Agent runs the ReAct loop, and CLI provides the terminal interface.

**Tech Stack:** Python 3.11+, `openai` SDK (OpenAI Compatible API via ZAI), `chromadb`, `python-dotenv`, `pytest`

---

## File Structure

```
myagent/
├── core/
│   ├── __init__.py          # Exports key classes
│   ├── llm.py               # LLMClient - wraps openai SDK
│   ├── tools.py             # ToolRegistry + @tool decorator
│   ├── memory.py            # Memory - short-term + long-term (ChromaDB)
│   ├── context.py           # ContextManager - assembles messages
│   └── agent.py             # Agent - ReAct loop
├── cli/
│   ├── __init__.py
│   └── main.py              # CLI entry point
├── tools/                   # Built-in tool implementations
│   ├── __init__.py
│   ├── web_search.py        # Web search tool
│   ├── file_ops.py          # File read/write tools
│   └── shell.py             # Shell execution tool
├── data/
│   ├── memory/              # ChromaDB persistence (gitignored)
│   └── persona.md           # Persona definition
├── tests/
│   ├── __init__.py
│   ├── test_llm.py
│   ├── test_tools.py
│   ├── test_memory.py
│   ├── test_context.py
│   ├── test_agent.py
│   └── test_cli.py
├── .env                     # API config (gitignored)
├── .gitignore
├── pyproject.toml
└── README.md
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env`
- Create: `data/persona.md`
- Create: `core/__init__.py`, `cli/__init__.py`, `tools/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Initialize git repo and create project directories**

```bash
cd /Users/starrystark/myagent
git init
mkdir -p core cli tools data/memory tests
touch core/__init__.py cli/__init__.py tools/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "myagent"
version = "0.1.0"
description = "Personal AI pet/assistant framework"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0",
    "chromadb>=0.5",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]

[project.scripts]
myagent = "cli.main:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

- [ ] **Step 3: Create .gitignore**

```
.env
__pycache__/
*.pyc
data/memory/
.pytest_cache/
*.egg-info/
dist/
build/
```

- [ ] **Step 4: Create .env template**

```
OPENAI_BASE_URL=https://your-zai-endpoint/v1
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-model-name
```

- [ ] **Step 5: Create data/persona.md**

```markdown
你是一只友善的电子宠物猫，叫小喵。
你记住用户的偏好，帮他完成任务。
说话简洁，偶尔卖个萌。
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: project scaffold with dependencies and config"
```

---

### Task 2: LLMClient

**Files:**
- Create: `core/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write failing tests for LLMClient**

```python
# tests/test_llm.py
import pytest
from unittest.mock import patch, MagicMock
from core.llm import LLMClient, LLMResponse


class TestLLMResponse:
    def test_text_only_response(self):
        resp = LLMResponse(content="hello", tool_calls=[])
        assert resp.content == "hello"
        assert resp.has_tool_calls is False

    def test_tool_call_response(self):
        call = {"id": "call_1", "name": "search", "arguments": '{"q": "test"}'}
        resp = LLMResponse(content="", tool_calls=[call])
        assert resp.has_tool_calls is True
        assert resp.tool_calls[0]["name"] == "search"


class TestLLMClient:
    def test_chat_text_response(self, mocker):
        mock_choice = MagicMock()
        mock_choice.message.content = "hello world"
        mock_choice.message.tool_calls = None
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mocker.patch("core.llm.OpenAI").return_value.chat.completions.create.return_value = mock_resp

        client = LLMClient(base_url="http://test", api_key="test", model="test-model")
        result = client.chat([{"role": "user", "content": "hi"}])

        assert result.content == "hello world"
        assert result.has_tool_calls is False

    def test_chat_tool_call_response(self, mocker):
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_1"
        mock_tool_call.function.name = "search"
        mock_tool_call.function.arguments = '{"q": "test"}'

        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_choice.message.tool_calls = [mock_tool_call]
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]

        mocker.patch("core.llm.OpenAI").return_value.chat.completions.create.return_value = mock_resp

        client = LLMClient(base_url="http://test", api_key="test", model="test-model")
        result = client.chat([{"role": "user", "content": "search for test"}])

        assert result.has_tool_calls is True
        assert result.tool_calls[0]["name"] == "search"

    def test_chat_passes_tools_param(self, mocker):
        mock_create = mocker.patch("core.llm.OpenAI").return_value.chat.completions.create
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_choice.message.tool_calls = None
        mock_create.return_value.choices = [mock_choice]

        client = LLMClient(base_url="http://test", api_key="test", model="test-model")
        tools = [{"type": "function", "function": {"name": "test"}}]
        client.chat([{"role": "user", "content": "hi"}], tools=tools)

        call_kwargs = mock_create.call_args
        assert call_kwargs.kwargs.get("tools") == tools or any("tools" in str(a) for a in call_kwargs.args)

    def test_from_env_creates_client(self, mocker):
        mocker.patch.dict("os.environ", {
            "OPENAI_BASE_URL": "http://test",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_MODEL": "test-model",
        })
        mocker.patch("core.llm.OpenAI")

        client = LLMClient.from_env()
        assert client.model == "test-model"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_llm.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.llm'`

- [ ] **Step 3: Implement LLMClient**

```python
# core/llm.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_env(cls) -> LLMClient:
        load_dotenv()
        return cls(
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.environ["OPENAI_MODEL"],
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_llm.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/llm.py tests/test_llm.py
git commit -m "feat: LLMClient with OpenAI SDK wrapper and tests"
```

---

### Task 3: ToolRegistry

**Files:**
- Create: `core/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests for ToolRegistry**

```python
# tests/test_tools.py
import pytest
from core.tools import tool, ToolRegistry


@tool(name="greet", description="Say hello to someone")
def greet(name: str) -> str:
    return f"Hello, {name}!"


@tool(name="add", description="Add two numbers")
def add(a: int, b: int) -> str:
    return str(a + b)


class TestToolDecorator:
    def test_decorator_marks_function(self):
        assert hasattr(greet, "_tool_name")
        assert greet._tool_name == "greet"
        assert greet._tool_description == "Say hello to someone"

    def test_decorator_preserves_function(self):
        assert greet("world") == "Hello, world!"


class TestToolRegistry:
    def test_register_and_get_schemas(self):
        registry = ToolRegistry()
        registry.register(greet)
        registry.register(add)

        schemas = registry.get_schemas()
        assert len(schemas) == 2
        names = {s["function"]["name"] for s in schemas}
        assert names == {"greet", "add"}

    def test_schema_has_correct_structure(self):
        registry = ToolRegistry()
        registry.register(greet)

        schema = registry.get_schemas()[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "greet"
        assert schema["function"]["description"] == "Say hello to someone"
        assert "name" in schema["function"]["parameters"]["properties"]
        assert schema["function"]["parameters"]["required"] == ["name"]

    def test_execute_tool(self):
        registry = ToolRegistry()
        registry.register(greet)

        result = registry.execute("greet", {"name": "world"})
        assert result == "Hello, world!"

    def test_execute_tool_with_int_params(self):
        registry = ToolRegistry()
        registry.register(add)

        result = registry.execute("add", {"a": 1, "b": 2})
        assert result == "3"

    def test_execute_unknown_tool_returns_error(self):
        registry = ToolRegistry()
        result = registry.execute("nonexistent", {})
        assert "not found" in result.lower()

    def test_execute_failing_tool_returns_error(self):
        @tool(name="boom", description="Always fails")
        def boom():
            raise ValueError("kaboom")

        registry = ToolRegistry()
        registry.register(boom)

        result = registry.execute("boom", {})
        assert "kaboom" in result

    def test_empty_registry(self):
        registry = ToolRegistry()
        assert registry.get_schemas() == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tools.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.tools'`

- [ ] **Step 3: Implement ToolRegistry**

```python
# core/tools.py
from __future__ import annotations

import inspect
import traceback
from typing import Any, Callable


def tool(name: str, description: str) -> Callable:
    """Decorator that marks a function as a tool with metadata."""
    def decorator(func: Callable) -> Callable:
        func._tool_name = name
        func._tool_description = description
        return func
    return decorator


def _build_schema(func: Callable) -> dict[str, Any]:
    """Generate OpenAI function calling JSON schema from type annotations."""
    sig = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []

    type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}

    for param_name, param in sig.parameters.items():
        if param.annotation is inspect.Parameter.empty:
            prop_type = "string"
        else:
            prop_type = type_map.get(param.annotation, "string")

        properties[param_name] = {"type": prop_type}

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": func._tool_name,
            "description": func._tool_description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict[str, Any]] = []

    def register(self, func: Callable) -> None:
        """Register a @tool-decorated function."""
        self._tools[func._tool_name] = func
        self._schemas.append(_build_schema(func))

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI tool calling format schemas."""
        return list(self._schemas)

    def execute(self, name: str, args: dict[str, Any]) -> str:
        """Execute a tool by name. Returns result string or error message."""
        if name not in self._tools:
            return f"Error: Tool '{name}' not found."

        try:
            result = self._tools[name](**args)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {e}\n{traceback.format_exc()}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tools.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/tools.py tests/test_tools.py
git commit -m "feat: ToolRegistry with @tool decorator and auto schema generation"
```

---

### Task 4: Memory

**Files:**
- Create: `core/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write failing tests for Memory**

```python
# tests/test_memory.py
import pytest
import tempfile
import os
from core.memory import Memory


@pytest.fixture
def memory(tmp_path):
    return Memory(chroma_path=str(tmp_path / "test_memory"))


class TestShortTermMemory:
    def test_add_and_get_messages(self, memory):
        memory.add_message("user", "hello")
        memory.add_message("assistant", "hi there")

        ctx = memory.get_context(max_tokens=4000)
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[1]["content"] == "hi there"

    def test_clear_empties_short_term(self, memory):
        memory.add_message("user", "hello")
        memory.clear()
        assert memory.get_context(max_tokens=4000) == []

    def test_get_context_truncates_by_tokens(self, memory):
        # Add many messages, verify get_context respects max_tokens
        for i in range(50):
            memory.add_message("user", f"message {i} " * 100)

        ctx = memory.get_context(max_tokens=500)
        total_text = " ".join(m["content"] for m in ctx)
        # Each "message N " is ~2 tokens, 50*100 = 5000 tokens worth
        # With max_tokens=500, should have significantly fewer messages
        assert len(ctx) < 50


class TestLongTermMemory:
    def test_save_and_recall(self, memory):
        memory.save_long_term("用户喜欢暗色主题", {"type": "preference"})
        results = memory.recall("用户喜欢什么主题", top_k=1)
        assert len(results) >= 1
        assert any("暗色" in r for r in results)

    def test_recall_returns_empty_when_no_match(self, memory):
        results = memory.recall("完全不相关的内容 xyz", top_k=3)
        assert isinstance(results, list)

    def test_save_multiple_and_recall_top_k(self, memory):
        memory.save_long_term("用户喜欢Python", {"type": "preference"})
        memory.save_long_term("用户在写agent项目", {"type": "fact"})
        memory.save_long_term("用户喜欢暗色主题", {"type": "preference"})

        results = memory.recall("用户偏好", top_k=2)
        assert len(results) <= 2

    def test_long_term_persists_across_instances(self, tmp_path):
        path = str(tmp_path / "persist_test")
        m1 = Memory(chroma_path=path)
        m1.save_long_term("持久化测试数据", {"type": "test"})

        m2 = Memory(chroma_path=path)
        results = m2.recall("持久化测试", top_k=1)
        assert any("持久化" in r for r in results)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_memory.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.memory'`

- [ ] **Step 3: Implement Memory**

```python
# core/memory.py
from __future__ import annotations

import chromadb
from typing import Any


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for mixed CJK/English."""
    return max(1, len(text) // 4)


class Memory:
    def __init__(self, chroma_path: str = "./data/memory"):
        self._short_term: list[dict[str, str]] = []
        self._chroma_client = chromadb.PersistentClient(path=chroma_path)
        self._collection = self._chroma_client.get_or_create_collection(
            name="long_term_memory",
        )

    def add_message(self, role: str, content: str) -> None:
        """Add a message to short-term memory."""
        self._short_term.append({"role": role, "content": content})

    def save_long_term(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Save key information to long-term vector memory."""
        metadata = metadata or {}
        import time
        metadata["timestamp"] = time.time()

        doc_id = f"mem_{len(self._collection.get()['ids'])}_{int(time.time())}"
        self._collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id],
        )

    def recall(self, query: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant long-term memories by query."""
        count = self._collection.count()
        if count == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        return results["documents"][0]

    def get_context(self, max_tokens: int = 4000) -> list[dict[str, str]]:
        """Return truncated conversation history within token budget."""
        budget = max_tokens
        result: list[dict[str, str]] = []

        # Keep most recent messages that fit
        for msg in reversed(self._short_term):
            tokens = _estimate_tokens(msg["content"])
            if budget - tokens < 0:
                break
            result.insert(0, msg)
            budget -= tokens

        return result

    def clear(self) -> None:
        """Clear short-term memory (start new conversation)."""
        self._short_term.clear()

    @property
    def long_term_count(self) -> int:
        """Return number of long-term memory entries."""
        return self._collection.count()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_memory.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/memory.py tests/test_memory.py
git commit -m "feat: Memory with short-term truncation and ChromaDB long-term storage"
```

---

### Task 5: ContextManager

**Files:**
- Create: `core/context.py`
- Create: `tests/test_context.py`

- [ ] **Step 1: Write failing tests for ContextManager**

```python
# tests/test_context.py
import pytest
from unittest.mock import MagicMock
from core.context import ContextManager
from core.memory import Memory


@pytest.fixture
def context(tmp_path):
    memory = Memory(chroma_path=str(tmp_path / "ctx_test"))
    tools = MagicMock()
    tools.get_schemas.return_value = [
        {"type": "function", "function": {"name": "test_tool"}}
    ]
    persona_text = "你是一只猫"
    return ContextManager(persona=persona_text, memory=memory, tool_registry=tools)


class TestContextManager:
    def test_build_includes_system_prompt(self, context):
        messages = context.build("你好")
        assert messages[0]["role"] == "system"
        assert "你是一只猫" in messages[0]["content"]

    def test_build_includes_user_input(self, context):
        messages = context.build("你好")
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "你好"

    def test_build_includes_short_term_history(self, context):
        context.memory.add_message("user", "早上好")
        context.memory.add_message("assistant", "喵～早上好")

        messages = context.build("今天天气怎么样")
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert any("早上好" in m["content"] for m in user_msgs)

    def test_build_includes_long_term_recall(self, context):
        context.memory.save_long_term("用户喜欢暗色主题", {"type": "preference"})

        messages = context.build("帮我选个主题")
        system_content = messages[0]["content"]
        assert "暗色" in system_content

    def test_build_message_ordering(self, context):
        context.memory.add_message("user", "hi")
        context.memory.add_message("assistant", "hello")

        messages = context.build("new question")
        assert messages[0]["role"] == "system"
        # History messages in the middle
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "new question"

    def test_persona_file_load(self, tmp_path):
        persona_file = tmp_path / "persona.md"
        persona_file.write_text("你是一只狗")

        memory = Memory(chroma_path=str(tmp_path / "persona_test"))
        tools = MagicMock()
        tools.get_schemas.return_value = []

        ctx = ContextManager.from_file(
            persona_path=str(persona_file),
            memory=memory,
            tool_registry=tools,
        )
        messages = ctx.build("hi")
        assert "你是一只狗" in messages[0]["content"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_context.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.context'`

- [ ] **Step 3: Implement ContextManager**

```python
# core/context.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.memory import Memory
from core.tools import ToolRegistry


class ContextManager:
    def __init__(self, persona: str, memory: Memory, tool_registry: ToolRegistry):
        self._persona = persona
        self._memory = memory
        self._tool_registry = tool_registry

    @classmethod
    def from_file(cls, persona_path: str, memory: Memory, tool_registry: ToolRegistry) -> ContextManager:
        """Create ContextManager with persona loaded from a markdown file."""
        persona = Path(persona_path).read_text(encoding="utf-8").strip()
        return cls(persona=persona, memory=memory, tool_registry=tool_registry)

    def build(self, user_input: str) -> list[dict[str, str]]:
        """Assemble the full message list for LLM."""
        system_prompt = self._build_system_prompt()

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        # Add short-term conversation history
        history = self._memory.get_context(max_tokens=3000)
        messages.extend(history)

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        return messages

    def _build_system_prompt(self) -> str:
        """Build system prompt: persona + long-term memory."""
        parts = [self._persona]

        # Recall relevant long-term memories (use persona as query for general context)
        memories = self._memory.recall(self._persona, top_k=5)
        if memories:
            parts.append("\n\n## 关于用户的记忆:")
            for mem in memories:
                parts.append(f"- {mem}")

        return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_context.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/context.py tests/test_context.py
git commit -m "feat: ContextManager with persona, memory recall, and history assembly"
```

---

### Task 6: Agent (ReAct Loop)

**Files:**
- Create: `core/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write failing tests for Agent**

```python
# tests/test_agent.py
import json
import pytest
from unittest.mock import MagicMock, patch
from core.agent import Agent
from core.llm import LLMResponse
from core.memory import Memory
from core.tools import ToolRegistry, tool
from core.context import ContextManager


@pytest.fixture
def agent(tmp_path):
    llm = MagicMock(spec=["chat"])
    memory = Memory(chroma_path=str(tmp_path / "agent_test"))
    registry = ToolRegistry()
    context = ContextManager(persona="你是一只猫", memory=memory, tool_registry=registry)
    return Agent(llm=llm, memory=memory, tools=registry, context_manager=context)


class TestAgentBasicLoop:
    def test_simple_text_reply(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="喵～你好！", tool_calls=[])

        result = agent.run("你好")

        assert result == "喵～你好！"
        agent.llm.chat.assert_called_once()

    def test_tool_call_then_reply(self, agent, tmp_path):
        # First call: LLM wants to call a tool
        tool_call = {
            "id": "call_1",
            "name": "greet",
            "arguments": json.dumps({"name": "world"}),
        }

        @tool(name="greet", description="Greet someone")
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        agent.tools.register(greet)

        agent.llm.chat.side_effect = [
            LLMResponse(content="", tool_calls=[tool_call]),   # First: tool call
            LLMResponse(content="喵～已打招呼！", tool_calls=[]),  # Second: final reply
        ]

        result = agent.run("跟world打个招呼")

        assert result == "喵～已打招呼！"
        assert agent.llm.chat.call_count == 2

    def test_conversation_history_stored(self, agent):
        agent.llm.chat.return_value = LLMResponse(content="喵～", tool_calls=[])

        agent.run("你好")

        ctx = agent.memory.get_context()
        assert any(m["content"] == "你好" for m in ctx)
        assert any(m["content"] == "喵～" for m in ctx)


class TestAgentLoopSafety:
    def test_max_iterations_stops_loop(self, agent):
        # LLM always returns a tool call — would loop forever
        tool_call = {
            "id": "call_1",
            "name": "greet",
            "arguments": json.dumps({"name": "loop"}),
        }

        @tool(name="greet", description="Greet")
        def greet(name: str) -> str:
            return f"Hi, {name}"

        agent.tools.register(greet)
        agent.llm.chat.return_value = LLMResponse(content="", tool_calls=[tool_call])

        result = agent.run("test")

        # Should stop after max iterations and return something
        assert isinstance(result, str)
        assert agent.llm.chat.call_count == 10  # default max_iterations

    def test_tool_error_handled_gracefully(self, agent):
        tool_call = {
            "id": "call_1",
            "name": "boom",
            "arguments": "{}",
        }

        @tool(name="boom", description="Always fails")
        def boom():
            raise RuntimeError("kaboom")

        agent.tools.register(boom)

        agent.llm.chat.side_effect = [
            LLMResponse(content="", tool_calls=[tool_call]),
            LLMResponse(content="工具出错了喵", tool_calls=[]),
        ]

        result = agent.run("执行boom")
        assert result == "工具出错了喵"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.agent'`

- [ ] **Step 3: Implement Agent**

```python
# core/agent.py
from __future__ import annotations

import json

from core.context import ContextManager
from core.llm import LLMClient, LLMResponse
from core.memory import Memory
from core.tools import ToolRegistry


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        memory: Memory,
        tools: ToolRegistry,
        context_manager: ContextManager,
        max_iterations: int = 10,
    ):
        self.llm = llm
        self.memory = memory
        self.tools = tools
        self.context_manager = context_manager
        self.max_iterations = max_iterations

    def run(self, user_input: str) -> str:
        """Run one conversation turn using the ReAct loop."""
        # Store user message in short-term memory
        self.memory.add_message("user", user_input)

        # Build initial context
        messages = self.context_manager.build(user_input)

        tool_schemas = self.tools.get_schemas() or None

        for _ in range(self.max_iterations):
            response = self.llm.chat(
                messages=messages,
                tools=tool_schemas,
            )

            if not response.has_tool_calls:
                # Final reply — store and return
                self.memory.add_message("assistant", response.content)
                return response.content

            # Process tool calls
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            })

            for tc in response.tool_calls:
                args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                result = self.tools.execute(tc["name"], args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        # Hit max iterations
        return response.content if response.content else "抱歉，我处理这个请求时遇到了困难喵。"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agent.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add core/agent.py tests/test_agent.py
git commit -m "feat: Agent with ReAct loop, tool calling, and iteration safety"
```

---

### Task 7: Built-in Tools

**Files:**
- Create: `tools/web_search.py`
- Create: `tools/file_ops.py`
- Create: `tools/shell.py`

- [ ] **Step 1: Implement web_search tool**

```python
# tools/web_search.py
from core.tools import tool


@tool(name="web_search", description="搜索网页获取信息")
def web_search(query: str) -> str:
    """Search the web for information. Returns search result snippets."""
    import urllib.request
    import urllib.parse
    import json

    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MyAgent/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])

        return "\n".join(results) if results else "未找到相关结果。"
    except Exception as e:
        return f"搜索失败: {e}"
```

- [ ] **Step 2: Implement file_ops tools**

```python
# tools/file_ops.py
from core.tools import tool


@tool(name="read_file", description="读取文件内容")
def read_file(path: str) -> str:
    """Read the contents of a file."""
    try:
        return open(path, encoding="utf-8").read()[:10000]
    except FileNotFoundError:
        return f"错误: 文件 '{path}' 不存在"
    except Exception as e:
        return f"读取文件失败: {e}"


@tool(name="write_file", description="写入内容到文件")
def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已写入 {path}"
    except Exception as e:
        return f"写入文件失败: {e}"
```

- [ ] **Step 3: Implement shell tool**

```python
# tools/shell.py
from core.tools import tool


@tool(name="shell_exec", description="执行shell命令并返回输出")
def shell_exec(command: str) -> str:
    """Execute a shell command and return its output."""
    import subprocess

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        return output[:5000] if output else "(无输出)"
    except subprocess.TimeoutExpired:
        return "命令执行超时 (30秒)"
    except Exception as e:
        return f"执行失败: {e}"
```

- [ ] **Step 4: Commit**

```bash
git add tools/web_search.py tools/file_ops.py tools/shell.py
git commit -m "feat: built-in tools — web search, file ops, shell exec"
```

---

### Task 8: CLI

**Files:**
- Create: `cli/main.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for CLI commands**

```python
# tests/test_cli.py
import pytest
from unittest.mock import MagicMock, patch
from core.llm import LLMResponse
from cli.main import handle_command


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.memory = MagicMock()
    agent.memory.get_context.return_value = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    agent.memory.long_term_count = 3
    return agent


class TestHandleCommand:
    def test_quit_returns_false(self, mock_agent):
        result = handle_command("/quit", mock_agent)
        assert result is False

    def test_clear_calls_memory_clear(self, mock_agent):
        handle_command("/clear", mock_agent)
        mock_agent.memory.clear.assert_called_once()

    def test_history_prints_context(self, mock_agent, capsys):
        handle_command("/history", mock_agent)
        output = capsys.readouterr().out
        assert "hi" in output
        assert "hello" in output

    def test_memory_shows_count(self, mock_agent, capsys):
        handle_command("/memory", mock_agent)
        output = capsys.readouterr().out
        assert "3" in output

    def test_help_shows_commands(self, mock_agent, capsys):
        handle_command("/help", mock_agent)
        output = capsys.readouterr().out
        assert "/quit" in output
        assert "/clear" in output

    def test_unknown_command_returns_none(self, mock_agent):
        result = handle_command("/unknown", mock_agent)
        assert result is None

    def test_normal_text_returns_none(self, mock_agent):
        result = handle_command("你好", mock_agent)
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'cli.main'`

- [ ] **Step 3: Implement CLI**

```python
# cli/main.py
from __future__ import annotations

from core.agent import Agent
from core.context import ContextManager
from core.llm import LLMClient
from core.memory import Memory
from core.tools import ToolRegistry

# Import built-in tools
from tools.web_search import web_search
from tools.file_ops import read_file, write_file
from tools.shell import shell_exec


COMMANDS = {
    "/help": "显示帮助",
    "/quit": "退出",
    "/clear": "清空当前对话",
    "/history": "查看对话历史",
    "/persona": "查看当前人格设定",
    "/memory": "查看长期记忆条数",
}


def handle_command(user_input: str, agent: Agent) -> bool | None:
    """Handle slash commands. Returns False to quit, None to continue."""
    if not user_input.startswith("/"):
        return None

    cmd = user_input.strip().lower()

    if cmd == "/quit":
        return False

    if cmd == "/clear":
        agent.memory.clear()
        print("对话已清空。")
        return True

    if cmd == "/history":
        ctx = agent.memory.get_context()
        for msg in ctx:
            print(f"[{msg['role']}] {msg['content']}")
        return True

    if cmd == "/memory":
        print(f"长期记忆: {agent.memory.long_term_count} 条")
        return True

    if cmd == "/persona":
        # Persona is in the system prompt, show it
        print(agent.context_manager._persona)
        return True

    if cmd == "/help":
        for cmd_name, desc in COMMANDS.items():
            print(f"  {cmd_name:12s} {desc}")
        return True

    return None


def create_agent() -> Agent:
    """Create and configure the agent with all components."""
    llm = LLMClient.from_env()

    memory = Memory()

    registry = ToolRegistry()
    registry.register(web_search)
    registry.register(read_file)
    registry.register(write_file)
    registry.register(shell_exec)

    context = ContextManager.from_file(
        persona_path="data/persona.md",
        memory=memory,
        tool_registry=registry,
    )

    return Agent(
        llm=llm,
        memory=memory,
        tools=registry,
        context_manager=context,
    )


def main():
    """Entry point for CLI."""
    print("小喵上线了～输入 /help 查看命令\n")

    agent = create_agent()

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见喵～")
            break

        if not user_input:
            continue

        # Handle slash commands
        result = handle_command(user_input, agent)
        if result is False:
            print("再见喵～")
            break
        if result is True:
            continue

        # Normal conversation
        reply = agent.run(user_input)
        print(f"\n小喵: {reply}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add cli/main.py tests/test_cli.py
git commit -m "feat: CLI with slash commands and agent initialization"
```

---

### Task 9: Wire Everything Together + Integration Test

**Files:**
- Modify: `core/__init__.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Update core/__init__.py with public API**

```python
# core/__init__.py
from core.llm import LLMClient, LLMResponse
from core.tools import ToolRegistry, tool
from core.memory import Memory
from core.context import ContextManager
from core.agent import Agent

__all__ = [
    "LLMClient",
    "LLMResponse",
    "ToolRegistry",
    "tool",
    "Memory",
    "ContextManager",
    "Agent",
]
```

- [ ] **Step 2: Write an integration test**

```python
# tests/test_integration.py
"""Integration test: full agent loop with mocked LLM."""
import json
import pytest
from unittest.mock import MagicMock

from core.agent import Agent
from core.llm import LLMResponse
from core.memory import Memory
from core.tools import ToolRegistry, tool
from core.context import ContextManager


def test_full_agent_loop_with_tool_call(tmp_path):
    """Test a complete user→agent→tool→agent→user cycle."""
    # Setup
    llm = MagicMock()
    memory = Memory(chroma_path=str(tmp_path / "integration"))
    registry = ToolRegistry()

    @tool(name="calculator", description="Calculate math")
    def calculator(expression: str) -> str:
        return str(eval(expression))  # safe in test

    registry.register(calculator)

    context = ContextManager(
        persona="你是一只猫",
        memory=memory,
        tool_registry=registry,
    )

    agent = Agent(llm=llm, memory=memory, tools=registry, context_manager=context)

    # LLM first calls tool, then replies
    llm.chat.side_effect = [
        LLMResponse(content="", tool_calls=[{
            "id": "call_1",
            "name": "calculator",
            "arguments": json.dumps({"expression": "2+3"}),
        }]),
        LLMResponse(content="2+3=5喵！", tool_calls=[]),
    ]

    result = agent.run("2+3等于多少")

    assert result == "2+3=5喵！"
    assert llm.chat.call_count == 2

    # Verify history stored
    ctx = memory.get_context()
    assert any("2+3" in m["content"] for m in ctx)
    assert any("5喵" in m["content"] for m in ctx)
```

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```

Expected: All PASS (20+ tests)

- [ ] **Step 4: Commit**

```bash
git add core/__init__.py tests/test_integration.py
git commit -m "feat: wire up public API and add integration test"
```

---

### Task 10: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

```markdown
# MyAgent

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
python -m cli.main
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
```

- [ ] **Step 2: Final commit**

```bash
git add README.md
git commit -m "docs: add README with usage and architecture overview"
```

---

## Self-Review

- **Spec coverage**: All 6 modules covered (LLMClient ✅, ToolRegistry ✅, Memory ✅, ContextManager ✅, Agent ✅, CLI ✅). Built-in tools ✅. Persona file ✅. .env config ✅.
- **Placeholder scan**: No TBDs, TODOs, or vague steps. All code is complete.
- **Type consistency**: Method signatures consistent across tasks — `LLMResponse(content, tool_calls)`, `ToolRegistry.register/execute/get_schemas`, `Memory.add_message/save_long_term/recall/get_context/clear`, `ContextManager.build`, `Agent.run` all match between definition and usage.
