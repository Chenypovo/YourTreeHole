# cli/main.py
from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from core.agent import Agent
from core.context import ContextManager
from core.llm import LLMClient
from core.memory import Memory
from core.tools import ToolRegistry

# Import built-in tools
from tools.web_search import web_search
from tools.file_ops import read_file, write_file
from tools.shell import shell_exec

console = Console()

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
        console.print("[dim]对话已清空。[/dim]")
        return True

    if cmd == "/history":
        ctx = agent.memory.get_context()
        for msg in ctx:
            role = msg["role"]
            if role == "user":
                console.print(f"[bold cyan]你:[/bold cyan] {msg['content']}")
            elif role == "assistant":
                console.print(f"[bold magenta]小喵:[/bold magenta] {msg['content']}")
        return True

    if cmd == "/memory":
        count = agent.memory.long_term_count
        console.print(f"[dim]长期记忆: {count} 条[/dim]")
        return True

    if cmd == "/persona":
        console.print(Panel(agent.context_manager._persona, title="人格设定", border_style="dim"))
        return True

    if cmd == "/help":
        for cmd_name, desc in COMMANDS.items():
            console.print(f"  [bold green]{cmd_name:12s}[/bold green] {desc}")
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
    console.print(Panel(
        "[bold magenta]小喵上线了～[/bold magenta]\n[dim]输入 /help 查看命令[/dim]",
        border_style="magenta",
    ))

    agent = create_agent()

    while True:
        try:
            user_input = console.input("[bold cyan]你:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold magenta]再见喵～[/bold magenta]")
            break

        if not user_input:
            continue

        # Handle slash commands
        result = handle_command(user_input, agent)
        if result is False:
            console.print("[bold magenta]再见喵～[/bold magenta]")
            break
        if result is True:
            continue

        # Streaming conversation
        console.print()
        collected = ""
        tool_executing = False

        for token, tool_name in agent.run_stream(user_input):
            if tool_name:
                # Tool is being executed
                if not tool_executing:
                    console.print(f"[dim yellow]  ⚙ 调用工具: {tool_name}[/dim yellow]")
                    tool_executing = True
            else:
                tool_executing = False
                if token:
                    collected += token
                    console.print(token, end="")

        # Render final markdown in a panel
        console.print()
        console.print(Markdown(collected))
        console.print()


if __name__ == "__main__":
    main()
