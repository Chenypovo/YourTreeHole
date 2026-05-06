from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class LLMSettings:
    model: str | None = None


@dataclass(frozen=True)
class PersonaSettings:
    path: str = "data/persona.md"


@dataclass(frozen=True)
class MemorySettings:
    chroma_path: str = "./data/memory"
    enable_gating: bool = True


@dataclass(frozen=True)
class AgentSettings:
    max_iterations: int = 10


@dataclass(frozen=True)
class UISettings:
    show_input_rules: bool = True
    input_prompt: str = "❯ "
    input_rule_color: str = "cyan"


@dataclass(frozen=True)
class AppConfig:
    llm: LLMSettings
    persona: PersonaSettings
    memory: MemorySettings
    agent: AgentSettings
    ui: UISettings

    @classmethod
    def from_file(cls, path: str = "config/settings.toml") -> AppConfig:
        raw = _load_toml(path)

        return cls(
            llm=LLMSettings(**raw.get("llm", {})),
            persona=PersonaSettings(**raw.get("persona", {})),
            memory=MemorySettings(**raw.get("memory", {})),
            agent=AgentSettings(**raw.get("agent", {})),
            ui=UISettings(**raw.get("ui", {})),
        )


def _load_toml(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {}

    with config_path.open("rb") as f:
        return tomllib.load(f)
