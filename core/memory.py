# core/memory.py
from __future__ import annotations

import chromadb
import time
from typing import Any


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for mixed CJK/English."""
    return max(1, len(text) // 4)


class Memory:
    def __init__(self, chroma_path: str = "./data/memory"):
        self._short_term: list[dict[str, str]] = []
        self._chroma_client = chromadb.PersistentClient(path=chroma_path)
        self._collection = self._chroma_client.get_or_create_collection(
            name="long_term_memory",
        )

    def add_message(self, role: str, content: str) -> None:
        """Add a message to short-term memory."""
        self._short_term.append({"role": role, "content": content})

    def save_long_term(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Save key information to long-term vector memory."""
        metadata = metadata or {}
        metadata["timestamp"] = time.time()

        doc_id = f"mem_{len(self._collection.get()['ids'])}_{int(time.time())}"
        self._collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id],
        )

    def recall(self, query: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant long-term memories by query."""
        count = self._collection.count()
        if count == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        return results["documents"][0]

    def get_context(self, max_tokens: int = 4000) -> list[dict[str, str]]:
        """Return truncated conversation history within token budget."""
        budget = max_tokens
        result: list[dict[str, str]] = []

        # Keep most recent messages that fit
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

    @property
    def long_term_count(self) -> int:
        """Return number of long-term memory entries."""
        return self._collection.count()
