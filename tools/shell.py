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
