"""Config loading and validation.

Everything that's hardcoded per-user in the original Claude Code command
(paths, addresses, taxonomy, Notion page IDs, model pins) lives here instead,
in one YAML file. See examples/shiva-profile/config.yaml for a worked example.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised for missing/invalid config — always with a fix, not just a complaint."""


@dataclass
class ProviderConfig:
    name: str = "anthropic"  # anthropic | openai | ollama
    triage_model: str = "claude-haiku-4-5-20251001"
    synthesis_model: str = "claude-sonnet-5"
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str | None = None  # for ollama / self-hosted endpoints

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


@dataclass
class SourceConfig:
    type: str  # rss | imap
    options: dict = field(default_factory=dict)


@dataclass
class SinkConfig:
    type: str  # markdown | notion
    options: dict = field(default_factory=dict)


@dataclass
class TopicsConfig:
    mode: str = "learned"  # declared | learned
    declared: list[str] = field(default_factory=list)


@dataclass
class Config:
    knowledge_path: Path
    profile_path: Path
    state_path: Path
    provider: ProviderConfig
    topics: TopicsConfig
    sources: list[SourceConfig]
    sinks: list[SinkConfig]
    relevance_themes: list[str]
    dry_run: bool = True
    root: Path = field(default_factory=Path.cwd)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path)
        if not path.exists():
            raise ConfigError(
                f"No config at {path}. Run `newsletter-sweep init` first — "
                "it writes a starter config.yaml and an applies_to_me.md profile."
            )
        raw = yaml.safe_load(path.read_text()) or {}
        root = path.parent

        provider_raw = raw.get("provider", {})
        provider = ProviderConfig(
            name=provider_raw.get("name", "anthropic"),
            triage_model=provider_raw.get("triage_model", "claude-haiku-4-5-20251001"),
            synthesis_model=provider_raw.get("synthesis_model", "claude-sonnet-5"),
            api_key_env=provider_raw.get("api_key_env", "ANTHROPIC_API_KEY"),
            base_url=provider_raw.get("base_url"),
        )

        topics_raw = raw.get("topics", {})
        topics = TopicsConfig(
            mode=topics_raw.get("mode", "learned"),
            declared=topics_raw.get("declared", []),
        )
        if topics.mode not in ("declared", "learned"):
            raise ConfigError(
                f"topics.mode must be 'declared' or 'learned', got {topics.mode!r}"
            )
        if topics.mode == "declared" and not topics.declared:
            raise ConfigError(
                "topics.mode is 'declared' but topics.declared is empty. "
                "List at least one topic, or switch to mode: learned."
            )

        sources = [
            SourceConfig(type=s["type"], options={k: v for k, v in s.items() if k != "type"})
            for s in raw.get("sources", [])
        ]
        if not sources:
            raise ConfigError(
                "No sources configured. Add at least one under `sources:` "
                "(rss is the zero-auth default)."
            )

        sinks = [
            SinkConfig(type=s["type"], options={k: v for k, v in s.items() if k != "type"})
            for s in raw.get("sinks", [{"type": "markdown"}])
        ]

        knowledge_path = root / raw.get("knowledge_path", "./knowledge")
        profile_path = root / raw.get("profile_path", "./applies_to_me.md")
        state_path = root / raw.get("state_path", "./.newsletter-sweep/state.json")

        return cls(
            knowledge_path=knowledge_path,
            profile_path=profile_path,
            state_path=state_path,
            provider=provider,
            topics=topics,
            sources=sources,
            sinks=sinks,
            relevance_themes=raw.get("relevance_themes", DEFAULT_RELEVANCE_THEMES),
            dry_run=raw.get("dry_run", True),
            root=root,
        )


# Used only when a user's config doesn't declare its own — a starting point,
# not a fixed taxonomy. See references/taxonomy-guide.md.
DEFAULT_RELEVANCE_THEMES = [
    "Ideas directly useful to my stated goals (see applies_to_me.md)",
    "Genuinely new information, not a restatement of common knowledge",
    "Concrete and actionable, not purely motivational",
]
