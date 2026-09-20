"""Dedup + watermark state — ported from state.txt in the original design.

Two-layer dedup survives the generalization unchanged: seen_urls (fast,
exact) and seen_ideas (fingerprint, catches conceptual duplicates across
differently-worded coverage of the same story). last_processed is the
watermark sources use to only fetch what's new.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path


STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is",
    "are", "with", "this", "that", "it", "as", "by", "at", "from", "be",
    "was", "were", "has", "have", "not", "but", "you", "your",
}


def _significant_words(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    words = re.findall(r"[a-z0-9]+", normalized)
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def fingerprint(text: str) -> str:
    """A coarse idea fingerprint: the sorted set of significant words,
    capped at 15. Deliberately loose — it exists so two differently-worded
    write-ups of the same story (a recap, a follow-up) still fingerprint
    close enough to catch via the Jaccard check in State.is_duplicate,
    not to be a hash of the exact text.
    """
    return " ".join(sorted(_significant_words(text))[:15])


@dataclass
class State:
    last_processed: datetime
    seen_urls: set[str] = field(default_factory=set)
    seen_ideas: set[str] = field(default_factory=set)
    sink_last_trimmed: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load_or_init(cls, path: Path, first_run_lookback_days: int = 7) -> "State":
        if not path.exists():
            return cls(
                last_processed=datetime.now(timezone.utc) - timedelta(days=first_run_lookback_days),
            )
        raw = json.loads(path.read_text())
        return cls(
            last_processed=datetime.fromisoformat(raw["last_processed"]),
            seen_urls=set(raw.get("seen_urls", [])),
            seen_ideas=set(raw.get("seen_ideas", [])),
            sink_last_trimmed=raw.get("sink_last_trimmed", {}),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "last_processed": self.last_processed.isoformat(),
                    "seen_urls": sorted(self.seen_urls),
                    "seen_ideas": sorted(self.seen_ideas),
                    "sink_last_trimmed": self.sink_last_trimmed,
                },
                indent=2,
            )
        )

    def is_duplicate(self, url: str, idea_text: str, jaccard_threshold: float = 0.6) -> bool:
        if url and url in self.seen_urls:
            return True
        candidate = _significant_words(idea_text)
        if not candidate:
            return False
        for seen in self.seen_ideas:
            seen_words = set(seen.split())
            if not seen_words:
                continue
            overlap = len(candidate & seen_words) / len(candidate | seen_words)
            if overlap >= jaccard_threshold:
                return True
        return False

    def mark_seen(self, url: str, idea_text: str) -> None:
        if url:
            self.seen_urls.add(url)
        if idea_text:
            self.seen_ideas.add(fingerprint(idea_text))
