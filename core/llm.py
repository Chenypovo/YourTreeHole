from __future__ import annotations

import os
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from core.config import LLMSettings


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.model = model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    @classmethod
    def from_env(cls) -> LLMClient:
        load_dotenv()
        return cls(
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.environ["OPENAI_MODEL"],
        )

    @classmethod
    def from_settings(cls, settings: LLMSettings) -> LLMClient:
        load_dotenv()
        return cls(
            base_url=settings.base_url or os.environ["OPENAI_BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
            model=settings.model or os.environ["OPENAI_MODEL"],
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
        )

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Generator[tuple[str, LLMResponse], None, None]:
        """Stream chat. Yields (token, final_response) tuples.
        final_response is None until the last yield, which contains the full response.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        stream = self._client.chat.completions.create(**kwargs)

        content_parts: list[str] = []
        tool_calls_map: dict[int, dict[str, Any]] = {}

        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                content_parts.append(delta.content)
                yield (delta.content, None)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        tool_calls_map[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_map[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls_map[idx]["function"]["arguments"] += tc.function.arguments

        final = LLMResponse(
            content="".join(content_parts),
            tool_calls=list(tool_calls_map.values()),
        )
        yield ("", final)
