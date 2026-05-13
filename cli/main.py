# cli/main.py
from __future__ import annotations

from functools import lru_cache

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.agent import Agent
from core.config import AppConfig
from core.context import ContextManager
from core.emotion import EmotionEngine
from core.llm import LLMClient
from core.memory import FileMemory
from core.profile import UserProfile

console = Console()
APP_VERSION = "0.2.0"

COMMANDS = {
    "/": "显示可用命令",
    "/help": "显示帮助",
    "/quit": "退出",
    "/reset": "清空当前对话（保留记忆）",
    "/profile": "查看用户画像",
    "/memories": "列出长期记忆",
    "/remember": "手动添加一条记忆",
    "/forget": "删除一条记忆",
    "/mood": "查看情感状态",
    "/persona": "查看或修改人格",
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
        for completion in self.get_completions(document, complete_event):
            yield completion


@lru_cache(maxsize=1)
def _build_prompt_session():
    try:
        from prompt_toolkit import PromptSession
    except ImportError:
        return None
    return PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        reserve_space_for_menu=8,
    )


def read_user_input_with_config(ui_config) -> str:
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

    if cmd == "/reset":
        agent.memory.clear()
        console.print("[dim]对话已清空，但你的记忆我都保留着。[/dim]")
        return True

    if cmd == "/profile":
        profile_text = agent.profile.load()
        console.print(Panel(profile_text, title="用户画像", border_style="magenta"))
        return True

    if cmd == "/memories":
        entries = agent.memory.list_memories()
        if not entries:
            console.print("[dim]还没有任何记忆。和我聊聊吧。[/dim]")
            return True
        for i, entry in enumerate(entries, start=1):
            check = "✓" if entry["resolved"] else " "
            console.print(f"  [bold green]{i}.[/bold green] [{check}] [{entry['category']}] {entry['content']}")
        return True

    if cmd == "/remember":
        if len(parts) < 2:
            console.print("[red]用法: /remember <内容>[/red]")
            return True
        content = parts[1] if len(parts) == 2 else " ".join(parts[1:])
        agent.memory.save_memory(content, category="手动", resolved=True)
        console.print(f"[dim]已记住: {content}[/dim]")
        return True

    if cmd == "/forget":
        if len(parts) < 2:
            console.print("[red]用法: /forget <编号>[/red]")
            return True
        try:
            index = int(parts[1])
            deleted = agent.memory.delete_memory(index)
            console.print(f"[dim]已删除: {deleted['content']}[/dim]")
        except ValueError:
            console.print("[red]编号必须是整数[/red]")
        except IndexError as e:
            console.print(f"[red]{e}[/red]")
        return True

    if cmd == "/mood":
        if agent.emotion:
            state = agent.emotion.get_state()
            lines = [
                f"心情: {state.mood_label} ({state.mood_value}/100) {state.mood_hearts}",
                f"羁绊: Lv.{state.bond_level} {state.bond_name}",
                f"精力: {state.energy}/100",
            ]
            console.print(Panel("\n".join(lines), title="情感状态", border_style="magenta"))
        else:
            console.print("[dim]情感系统未启用[/dim]")
        return True

    if cmd == "/persona":
        console.print(Panel(agent.context_manager.persona, title="人格设定", border_style="dim"))
        return True

    if cmd == "/help":
        for cmd_name, desc in COMMANDS.items():
            console.print(f"  [bold green]{cmd_name:12s}[/bold green] {desc}")
        return True

    return None


def create_agent(config: AppConfig | None = None) -> tuple[Agent, EmotionEngine]:
    """Create and configure the treehole agent. Returns (agent, emotion)."""
    config = config or AppConfig.from_file()
    llm = LLMClient.from_settings(config.llm)

    memory = FileMemory(data_dir=config.memory.data_dir)
    profile = UserProfile(data_dir=config.memory.data_dir)

    emotion = EmotionEngine(
        llm=llm,
        bond_path=config.memory.data_dir.rstrip("/") + "/bond.json",
    )

    # Load persona
    from pathlib import Path
    persona_path = config.persona.path
    if Path(persona_path).exists():
        persona_text = Path(persona_path).read_text(encoding="utf-8").strip()
    else:
        persona_text = "你是一个温暖的倾听者。你不评判，不建议，只是认真地听用户说话，记住他们告诉你的每一件重要的事。偶尔追问一句「后来呢？」"

    context = ContextManager(
        persona=persona_text,
        memory=memory,
        profile=profile,
        model_name=llm.model,
        emotion=emotion,
    )

    agent = Agent(
        llm=llm,
        memory=memory,
        profile=profile,
        context_manager=context,
        enable_memory_gating=config.memory.enable_gating,
        profile_update_interval=config.memory.profile_update_interval,
    )
    agent.attach_emotion(emotion)
    return agent, emotion


def generate_greeting(llm, profile: UserProfile, memory: FileMemory) -> str | None:
    """Generate a proactive greeting based on profile and unresolved events."""
    unresolved = profile.get_unresolved_events()
    recent = memory.get_recent_memories(5)
    if not unresolved and not recent:
        return None

    context_parts = []
    if unresolved:
        context_parts.append("用户之前提到但还没说结果的事：\n" + "\n".join(f"- {e}" for e in unresolved))
    if recent:
        context_parts.append("最近的记忆：\n" + "\n".join(f"- {m['content']}" for m in recent[-3:]))

    messages = [
        {"role": "system", "content": (
            "你是一个温暖的AI树洞。根据用户的记忆和未闭环事件，生成一段简短自然的问候。\n"
            "要求：1-2句话，自然亲切，像朋友一样问起之前的事。不要列清单。"
        )},
        {"role": "user", "content": "\n\n".join(context_parts)},
    ]
    try:
        response = llm.chat(messages=messages, tools=None)
        return response.content.strip()
    except Exception:
        return None


def render_startup_banner(agent: Agent, config: AppConfig) -> None:
    logo = Text(
        r"""
 __  __                 _
|  \/  |_   _ _ __ _ __ | |__  _   _
| |\/| | | | | '__| '_ \| '_ \| | | |
| |  | | |_| | |  | |_) | | | | |_| |
|_|  |_|\__,_|_|  | .__/|_| |_|\__, /
                  |_|          |___/
""",
        style="bold cyan",
    )
    console.print(Panel(
        logo,
        title=f"[bold cyan]Treehole v{APP_VERSION}[/bold cyan]",
        subtitle=f"[dim]{agent.llm.model} | 输入 / 查看命令[/dim]",
        border_style="cyan",
    ))


def main():
    """Entry point for CLI."""
    config = AppConfig.from_file()
    agent, emotion = create_agent(config)
    render_startup_banner(agent, config)

    # Proactive greeting
    greeting = generate_greeting(agent.llm, agent.profile, agent.memory)
    if greeting:
        console.print(f"\n  [cyan]{greeting}[/cyan]\n")

    # Check absence
    if emotion.bond.check_return_after_absence():
        console.print("[bold yellow]好久不见！[/bold yellow]\n")

    while True:
        try:
            user_input = read_user_input_with_config(config.ui).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold cyan]下次见～[/bold cyan]")
            break

        if not user_input:
            continue

        result = handle_command(user_input, agent)
        if result is False:
            console.print("[bold cyan]下次见～[/bold cyan]")
            break
        if result is True:
            continue

        # Streaming conversation
        console.print()
        first_token = True
        status = console.status("[dim]思考中...[/dim]", spinner="dots")
        status.start()

        try:
            for token in agent.run_stream(user_input):
                if first_token and token:
                    status.stop()
                    first_token = False
                if token:
                    console.print(token, end="")
        finally:
            if first_token:
                status.stop()

        console.print()


if __name__ == "__main__":
    main()
