"""Source adapter interface.

A source's only job is: given a watermark, return raw items (with enough
metadata to dedup and triage) that arrived since then. Nothing about
triage, routing, or writing lives here — sources are dumb on purpose.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawItem:
    """One fetched item, before triage. `body` should be the fullest text
    available — never strip URL-bearing lines here (a lesson learned the
    hard way: doing so once gutted a high-value link-dense source down to
    nothing). Extraction adapters trim tracking noise only, never content.
    """
    source_name: str
    title: str
    url: str
    published: datetime
    body: str
    sender: str = ""


class Source(ABC):
    """Base class for a content source. Subclass and register in
    sources/__init__.py's SOURCE_REGISTRY to add a new one.
    """

    def __init__(self, options: dict):
        self.options = options

    @abstractmethod
    def fetch_since(self, watermark: datetime) -> list[RawItem]:
        """Return items published/received after `watermark`. Must not
        raise on a single bad entry — log and skip it, return the rest.
        """
        raise NotImplementedError
