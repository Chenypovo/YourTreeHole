# cli/main.py
from __future__ import annotations

from functools import lru_cache

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.agent import Agent
from core.config import AppConfig
from core.context import ContextManager
from core.llm import LLMClient
from core.memory import Memory
from core.tools import ToolRegistry

# Import built-in tools
from tools.web_search import web_search
from tools.file_ops import read_file, write_file
from tools.shell import shell_exec

console = Console()
APP_VERSION = "0.1.0"

COMMANDS = {
    "/": "显示可用命令",
    "/help": "显示帮助",
    "/status": "查看当前运行配置",
    "/quit": "退出",
    "/clear": "清空当前对话",
    "/history": "查看对话历史",
    "/persona": "查看当前人格设定",
    "/memory": "查看长期记忆条数",
    "/showmemory": "列出长期记忆内容",
    "/setmemory": "按编号修改长期记忆",
    "/delmemory": "按编号删除长期记忆",
}


class SlashCommandCompleter:
    """Lazy prompt_toolkit completer for slash commands."""

    def get_completions(self, document, complete_event):
        text = document.text.lstrip()
        if not text.startswith(("/", "\\")):
            return

        normalized = "/" + text[1:] if text.startswith("\\") else text
        if " " in normalized:
            return

        from prompt_toolkit.completion import Completion

        for cmd_name, desc in COMMANDS.items():
            if cmd_name == "/":
                continue
            if cmd_name.startswith(normalized):
                yield Completion(
                    cmd_name,
                    start_position=-len(text),
                    display=cmd_name,
                    display_meta=desc,
                )

    async def get_completions_async(self, document, complete_event):
        """Compat with prompt_toolkit async completion API."""
        for completion in self.get_completions(document, complete_event):
            yield completion


@lru_cache(maxsize=1)
def _build_prompt_session():
    """Create a prompt_toolkit session when available."""
    try:
        from prompt_toolkit import PromptSession
    except ImportError:
        return None

    return PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        reserve_space_for_menu=8,
    )


def read_user_input() -> str:
    """Read one line from the terminal with slash-command completion when available."""
    return read_user_input_with_config(AppConfig.from_file().ui)


def read_user_input_with_config(ui_config) -> str:
    """Read one line using the configured prompt styling."""
    if ui_config.show_input_rules:
        console.rule(style=ui_config.input_rule_color)
    session = _build_prompt_session()
    if session is None:
        value = console.input("[bold cyan]你:[/bold cyan] ")
        if ui_config.show_input_rules:
            console.rule(style=ui_config.input_rule_color)
        return value

    if not ui_config.show_input_rules:
        return session.prompt(ui_config.input_prompt)

    value = session.prompt(ui_config.input_prompt)
    if ui_config.show_input_rules:
        console.rule(style=ui_config.input_rule_color)
    return value


def handle_command(user_input: str, agent: Agent) -> bool | None:
    """Handle slash commands. Returns False to quit, None to continue."""
    if not user_input.startswith(("/", "\\")):
        return None

    raw = user_input.strip()
    if raw in {"/", "\\"}:
        for cmd_name, desc in COMMANDS.items():
            console.print(f"  [bold green]{cmd_name:12s}[/bold green] {desc}")
        return True

    normalized = "/" + raw[1:] if raw.startswith("\\") else raw
    parts = normalized.split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd == "/quit":
        return False

    if cmd == "/status":
        config = AppConfig.from_file()
        lines = [
            f"模型: {agent.llm.model}",
            f"人格文件: {config.persona.path}",
            f"长期记忆路径: {config.memory.chroma_path}",
            f"长期记忆 gating: {'开启' if agent.enable_memory_gating else '关闭'}",
            f"最大迭代次数: {agent.max_iterations}",
            f"输入分隔线: {'开启' if config.ui.show_input_rules else '关闭'}",
            f"输入提示符: {config.ui.input_prompt}",
        ]
        console.print(Panel("\n".join(lines), title="当前状态", border_style="dim"))
        return True

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
                console.print(f"[bold cyan]Murphy:[/bold cyan] {msg['content']}")
        return True

    if cmd == "/memory":
        count = agent.memory.long_term_count
        console.print(f"[dim]长期记忆: {count} 条[/dim]")
        return True

    if cmd == "/showmemory":
        entries = agent.memory.list_long_term()
        if not entries:
            console.print("[dim]长期记忆为空。[/dim]")
            return True

        for index, entry in enumerate(entries, start=1):
            console.print(f"[bold green]{index}.[/bold green] {entry['content']}")
        return True

    if cmd == "/setmemory":
        if len(parts) < 3:
            console.print("[red]用法: /setmemory <编号> <新内容>[/red]")
            return True

        try:
            index = int(parts[1])
            updated = agent.memory.update_long_term(index, parts[2])
        except ValueError:
            console.print("[red]编号必须是整数。[/red]")
            return True
        except IndexError as e:
            console.print(f"[red]{e}[/red]")
            return True

        console.print(f"[dim]已更新长期记忆 {index}: {updated['content']}[/dim]")
        return True

    if cmd == "/delmemory":
        if len(parts) < 2:
            console.print("[red]用法: /delmemory <编号>[/red]")
            return True

        try:
            index = int(parts[1])
            deleted = agent.memory.delete_long_term(index)
        except ValueError:
            console.print("[red]编号必须是整数。[/red]")
            return True
        except IndexError as e:
            console.print(f"[red]{e}[/red]")
            return True

        console.print(f"[dim]已删除长期记忆 {index}: {deleted['content']}[/dim]")
        return True

    if cmd == "/persona":
        console.print(Panel(agent.context_manager._persona, title="人格设定", border_style="dim"))
        return True

    if cmd == "/help":
        for cmd_name, desc in COMMANDS.items():
            console.print(f"  [bold green]{cmd_name:12s}[/bold green] {desc}")
        return True

    return None


def create_agent(config: AppConfig | None = None) -> Agent:
    """Create and configure the agent with all components."""
    config = config or AppConfig.from_file()
    llm = LLMClient.from_settings(config.llm)

    memory = Memory(chroma_path=config.memory.chroma_path)

    registry = ToolRegistry()
    registry.register(web_search)
    registry.register(read_file)
    registry.register(write_file)
    registry.register(shell_exec)

    context = ContextManager.from_file(
        persona_path=config.persona.path,
        memory=memory,
        tool_registry=registry,
        model_name=llm.model,
    )

    return Agent(
        llm=llm,
        memory=memory,
        tools=registry,
        context_manager=context,
        max_iterations=config.agent.max_iterations,
        enable_memory_gating=config.memory.enable_gating,
    )


def render_startup_banner(agent: Agent, config: AppConfig) -> None:
    """Render the startup banner with runtime details."""
    logo = Text(
        r"""
 __  __                 _
|  \/  |_   _ _ __ _ __ | |__  _   _
| |\/| | | | | '__| '_ \| '_ \| | | |
| |  | | |_| | |  | |_) | | | | |_| |
|_|  |_|\__,_|_|  | .__/|_| |_|\__, |
                  |_|          |___/
""",
        style="bold cyan",
    )

    info = Table.grid(padding=(0, 1))
    info.add_column(style="cyan", no_wrap=True)
    info.add_column(style="white")
    info.add_row("Model", agent.llm.model)
    info.add_row("Commands", "/, /help, /status, /showmemory")

    tools = ", ".join(tool["name"] for tool in agent.tools.list_tools())
    info.add_row("Tools", tools or "(none)")

    body = Columns([logo, info], expand=False, equal=False)
    console.print(Panel(
        body,
        title=f"[bold cyan]Murphy Agent v{APP_VERSION}[/bold cyan]",
        subtitle="[dim]输入 / 查看命令[/dim]",
        border_style="cyan",
    ))


def main():
    """Entry point for CLI."""
    config = AppConfig.from_file()
    agent = create_agent(config)
    render_startup_banner(agent, config)

    while True:
        try:
            user_input = read_user_input_with_config(config.ui).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold cyan]再见喵～[/bold cyan]")
            break

        if not user_input:
            continue

        # Handle slash commands
        result = handle_command(user_input, agent)
        if result is False:
            console.print("[bold cyan]再见喵～[/bold cyan]")
            break
        if result is True:
            continue

        # Streaming conversation
        console.print()
        tool_executing = False
        first_event = True
        thinking_status = console.status("[dim]思考中...[/dim]", spinner="dots")
        thinking_status.start()

        try:
            for token, tool_name in agent.run_stream(user_input):
                if first_event and (token or tool_name is not None):
                    thinking_status.stop()
                    first_event = False

                if tool_name:
                    # Tool is being executed
                    if not tool_executing:
                        console.print(f"[dim yellow]  ⚙ 调用工具: {tool_name}[/dim yellow]")
                        tool_executing = True
                else:
                    tool_executing = False
                    if token:
                        console.print(token, end="")
        finally:
            if first_event:
                thinking_status.stop()

        console.print()


if __name__ == "__main__":
    main()
