# tests/test_tools.py
import pytest
from core.tools import tool, ToolRegistry
from tools.shell import shell_exec


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

    def test_list_tools_returns_names_and_descriptions(self):
        registry = ToolRegistry()
        registry.register(greet)

        tools = registry.list_tools()

        assert tools == [{"name": "greet", "description": "Say hello to someone"}]


class TestShellExec:
    def test_rejects_shell_metacharacters(self):
        result = shell_exec("ls | cat")
        assert "不支持 shell 特殊字符" in result

    def test_rejects_blocked_commands(self):
        result = shell_exec("python3 -V")
        assert "不允许执行命令 'python3'" in result

    def test_allows_simple_read_only_command(self):
        result = shell_exec("echo hello")
        assert result.strip() == "hello"
