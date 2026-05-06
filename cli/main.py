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
