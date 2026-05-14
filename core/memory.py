# core/memory.py
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
from typing import Any


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for mixed CJK/English."""
    return max(1, len(text) // 4)


class FileMemory:
    """File-based memory system for the treehole agent.

    Short-term: in-memory conversation history.
    Long-term: data/memories.md (Markdown, append-only).
    Journal: data/journal.md (raw conversation log, append-only).
    """

    def __init__(self, data_dir: str = "./data"):
        self._short_term: list[dict[str, str]] = []
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._memories_file = self._data_dir / "memories.md"
        self._journal_file = self._data_dir / "journal.md"

        if not self._memories_file.exists():
            self._memories_file.write_text("# 记忆\n", encoding="utf-8")
        if not self._journal_file.exists():
            self._journal_file.write_text("# 原始对话日记\n", encoding="utf-8")

    # ── Short-term (session) ──

    def add_message(self, role: str, content: str) -> None:
        """Add a message to short-term conversation history."""
        self._short_term.append({"role": role, "content": content})

    def get_context(self, max_tokens: int = 4000) -> list[dict[str, str]]:
        """Return truncated conversation history within token budget."""
        budget = max_tokens
        result: list[dict[str, str]] = []
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

    # ── Long-term (memories.md) ──

    def save_turn(self, user_input: str, assistant_output: str = "") -> None:
        """Append a raw conversation turn to journal.md.

        This is the durable source of truth. Gated memories and profile summaries
        are derived from this log, so a failed LLM gating call cannot lose the
        user's original thought.
        """
        if not user_input.strip() and not assistant_output.strip():
            return

        today = date.today().isoformat()
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry_parts = [
            f"### {timestamp}",
            "",
            "**用户**",
            _quote_block(user_input.strip()),
        ]
        if assistant_output.strip():
            entry_parts.extend([
                "",
                "**助手**",
                _quote_block(assistant_output.strip()),
            ])
        entry = "\n".join(entry_parts)

        text = self._journal_file.read_text(encoding="utf-8")
        today_header = f"## {today}"
        if today_header in text:
            self._journal_file.write_text(
                text.rstrip() + f"\n\n{entry}\n",
                encoding="utf-8",
            )
        else:
            self._journal_file.write_text(
                text.rstrip() + f"\n\n{today_header}\n\n{entry}\n",
                encoding="utf-8",
            )

    def save_memory(self, content: str, category: str = "general", resolved: bool = False) -> None:
        """Append a memory entry to memories.md under today's date."""
        check = "x" if resolved else " "
        today = date.today().isoformat()
        entry = f"- [{check}] [{category}] {content}"

        text = self._memories_file.read_text(encoding="utf-8")
        today_header = f"## {today}"

        if today_header in text:
            # Find today's section and append to it
            lines = text.split("\n")
            insert_idx = len(lines)
            found_today = False
            for i, line in enumerate(lines):
                if line.strip() == today_header:
                    found_today = True
                    # Find the end of this date's entries
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("## "):
                            insert_idx = j
                            break
                    else:
                        insert_idx = len(lines)
                    break

            lines.insert(insert_idx, entry)
            self._memories_file.write_text("\n".join(lines), encoding="utf-8")
        else:
            # New date section
            self._memories_file.write_text(
                text.rstrip() + f"\n\n{today_header}\n{entry}\n",
                encoding="utf-8",
            )

    def list_memories(self) -> list[dict[str, Any]]:
        """Parse and return all memories from memories.md."""
        text = self._memories_file.read_text(encoding="utf-8")
        entries: list[dict[str, Any]] = []
        current_date = ""

        for line in text.split("\n"):
            if line.startswith("## "):
                current_date = line[3:].strip()
            elif line.startswith("- ["):
                resolved = line[3] == "x"
                rest = line[6:]  # starts at "[" of [category]
                cat_inner = rest[1:]  # skip "[", e.g. "偏好] 用户喜欢猫"
                cat_end = cat_inner.find("]")
                if cat_end != -1:
                    category = cat_inner[:cat_end]
                    content = cat_inner[cat_end + 1:].strip()
                else:
                    category = "general"
                    content = cat_inner.strip()
                entries.append({
                    "date": current_date,
                    "category": category,
                    "content": content,
                    "resolved": resolved,
                })

        return entries

    def delete_memory(self, index: int) -> dict[str, Any]:
        """Delete a memory by 1-based index. Returns the deleted entry."""
        entries = self.list_memories()
        if index < 1 or index > len(entries):
            raise IndexError(f"记忆编号超出范围: {index}")

        target = entries[index - 1]
        lines = self._memories_file.read_text(encoding="utf-8").split("\n")
        current_date = ""
        entry_count = 0
        new_lines = []
        for line in lines:
            if line.startswith("## "):
                current_date = line[3:].strip()
                new_lines.append(line)
            elif line.startswith("- [") and current_date:
                entry_count += 1
                if entry_count != index:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        self._memories_file.write_text("\n".join(new_lines), encoding="utf-8")
        return target

    def get_recent_memories(self, n: int = 20) -> list[dict[str, Any]]:
        """Return the N most recent memories."""
        entries = self.list_memories()
        return entries[-n:]

    def get_relevant_memories(self, query: str, n: int = 10) -> list[dict[str, Any]]:
        """Return memories with simple lexical relevance to the current query.

        This intentionally stays dependency-free. It is not a replacement for a
        vector index, but it prevents old Markdown memories from becoming
        invisible just because they are no longer recent.
        """
        query = query.strip()
        if not query:
            return []

        words = {
            w.lower()
            for w in re.findall(r"[A-Za-z0-9_\-]+", query)
            if len(w) >= 2
        }
        query_chars = {
            ch
            for ch in query
            if "\u4e00" <= ch <= "\u9fff"
        }
        if not words and not query_chars:
            return []

        scored: list[tuple[int, int, dict[str, Any]]] = []
        for idx, entry in enumerate(self.list_memories()):
            haystack = f"{entry['category']} {entry['content']}".lower()
            score = 0
            for word in words:
                if word in haystack:
                    score += len(word) * 3
            if query_chars:
                memory_chars = {
                    ch
                    for ch in entry["content"]
                    if "\u4e00" <= ch <= "\u9fff"
                }
                score += len(query_chars & memory_chars)
            if score > 0:
                scored.append((score, idx, entry))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [entry for _, _, entry in scored[:n]]

    def get_unresolved_events(self) -> list[dict[str, Any]]:
        """Return all unresolved memories."""
        return [e for e in self.list_memories() if not e["resolved"]]

    def resolve_memory(self, index: int) -> dict[str, Any]:
        """Mark a memory as resolved by 1-based index."""
        entries = self.list_memories()
        if index < 1 or index > len(entries):
            raise IndexError(f"记忆编号超出范围: {index}")

        lines = self._memories_file.read_text(encoding="utf-8").split("\n")
        current_date = ""
        entry_count = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                current_date = line[3:].strip()
            elif line.startswith("- [") and current_date:
                entry_count += 1
                if entry_count == index:
                    lines[i] = line.replace("- [ ]", "- [x]", 1)
                    break

        self._memories_file.write_text("\n".join(lines), encoding="utf-8")
        return entries[index - 1]

    @property
    def memory_count(self) -> int:
        """Return total number of long-term memories."""
        return len(self.list_memories())

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def journal_file(self) -> Path:
        return self._journal_file


def _quote_block(text: str) -> str:
    """Render arbitrary text as a Markdown quote block."""
    if not text:
        return ">"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())
