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
