from core.tools import tool


_SHELL_METACHARS = {"|", "&", ";", ">", "<", "$", "`", "(", ")", "{", "}", "*", "?"}
_BLOCKED_COMMANDS = {
    "rm",
    "mv",
    "sudo",
    "chmod",
    "chown",
    "git",
    "curl",
    "wget",
    "ssh",
    "scp",
    "python",
    "python3",
    "bash",
    "sh",
    "zsh",
}


@tool(name="shell_exec", description="执行shell命令并返回输出")
def shell_exec(command: str) -> str:
    """Execute a read-only shell command and return its output."""
    import subprocess
    import shlex

    stripped = command.strip()
    if not stripped:
        return "执行失败: 命令不能为空"

    if any(char in stripped for char in _SHELL_METACHARS):
        return "执行失败: 不支持 shell 特殊字符或重定向"

    try:
        args = shlex.split(stripped)
    except ValueError as e:
        return f"执行失败: 无法解析命令: {e}"

    if not args:
        return "执行失败: 命令不能为空"

    if args[0] in _BLOCKED_COMMANDS:
        return f"执行失败: 出于安全考虑，不允许执行命令 '{args[0]}'"

    try:
        result = subprocess.run(
            args,
            shell=False,
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
