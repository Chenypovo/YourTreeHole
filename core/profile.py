# core/profile.py
from __future__ import annotations

from pathlib import Path


DEFAULT_PROFILE = """## 用户画像

### 基本信息
- （暂无记录）

### 性格与偏好
- （暂无记录）

### 重要的人
- （暂无记录）

### 当前状态
- （暂无记录）

### 未闭环事件
- （暂无）
"""


class UserProfile:
    """Manage user_profile.md — the medium-term memory layer."""

    def __init__(self, data_dir: str = "./data"):
        self._path = Path(data_dir) / "user_profile.md"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(DEFAULT_PROFILE, encoding="utf-8")

    def load(self) -> str:
        """Return full profile text."""
        return self._path.read_text(encoding="utf-8")

    def save(self, content: str) -> None:
        """Overwrite profile with new content."""
        self._path.write_text(content, encoding="utf-8")

    def get_unresolved_events(self) -> list[str]:
        """Parse unresolved events from the 未闭环事件 section."""
        text = self.load()
        events: list[str] = []
        in_unresolved = False

        for line in text.split("\n"):
            if "未闭环" in line:
                in_unresolved = True
                continue
            if in_unresolved:
                stripped = line.strip()
                if stripped.startswith("### "):
                    break
                if stripped.startswith("- [ ] "):
                    events.append(stripped[6:])
                elif stripped.startswith("- （暂无"):
                    continue
                elif not stripped.startswith("-"):
                    if events:
                        break

        return events

    def update(self, llm, recent_conversation: str) -> None:
        """Ask LLM to update the profile based on recent conversation."""
        current = self.load()
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个用户画像管理器。根据最近的对话内容，更新用户画像。\n"
                    "规则：\n"
                    "- 保留已有信息，只更新或新增\n"
                    "- 如果信息有变化（比如工作换了），更新它\n"
                    "- 在「未闭环事件」中标记提到但还没结果的事\n"
                    "- 已有结论的事件改为 [x]\n"
                    "- 返回完整的更新后的画像文本，不要省略任何部分\n"
                    "- 使用 Markdown 格式\n"
                ),
            },
            {
                "role": "user",
                "content": f"当前画像：\n{current}\n\n最近对话：\n{recent_conversation}\n\n请更新画像。",
            },
        ]
        try:
            response = llm.chat(messages=messages, tools=None)
            if response.content.strip():
                self.save(response.content.strip())
        except Exception:
            pass
