"""Sink adapter interface. A sink's job is only to persist triaged items —
it never makes judgment calls about relevance or routing.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..triage import TriagedItem


class Sink(ABC):
    def __init__(self, options: dict, dry_run: bool = True):
        self.options = options
        self.dry_run = dry_run

    @abstractmethod
    def write_item(self, item: TriagedItem) -> str:
        """Persist one item. Returns a short human-readable description of
        what was written/would be written, for the run summary."""
        raise NotImplementedError

    def write_digest(self, digest_markdown: str, digest_title: str) -> str:
        """Optional: sinks that support a standalone digest doc override
        this. Default is a no-op — not every sink needs one."""
        return "digest not supported by this sink"
