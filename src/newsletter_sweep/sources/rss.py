"""RSS/Atom source — the zero-auth default. Most newsletter platforms
(Substack, Beehiiv, Ghost, ConvertKit) publish a feed even when the primary
distribution is email; this is what makes a five-minute first run possible
with no account, no OAuth, nothing to configure but a list of URLs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser

from .base import RawItem, Source

logger = logging.getLogger(__name__)


class RSSSource(Source):
    """Config:
    ```yaml
    - type: rss
      feeds:
        - "https://example.substack.com/feed"
        - "https://another-newsletter.com/rss.xml"
    ```
    """

    def fetch_since(self, watermark: datetime) -> list[RawItem]:
        feeds = self.options.get("feeds", [])
        items: list[RawItem] = []
        for feed_url in feeds:
            try:
                items.extend(self._fetch_feed(feed_url, watermark))
            except Exception as exc:  # a single bad feed must not kill the run
                logger.warning("RSS feed failed, skipping: %s (%s)", feed_url, exc)
        return items

    def _fetch_feed(self, feed_url: str, watermark: datetime) -> list[RawItem]:
        parsed = feedparser.parse(feed_url)
        source_name = parsed.feed.get("title", feed_url)
        out: list[RawItem] = []
        for entry in parsed.entries:
            published = self._entry_date(entry)
            if published is not None and published <= watermark:
                continue
            body = self._entry_body(entry)
            out.append(
                RawItem(
                    source_name=source_name,
                    title=entry.get("title", "(untitled)"),
                    url=entry.get("link", ""),
                    published=published or datetime.now(timezone.utc),
                    body=body,
                    sender=source_name,
                )
            )
        return out

    @staticmethod
    def _entry_date(entry) -> datetime | None:
        parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed_time:
            return None
        return datetime(*parsed_time[:6], tzinfo=timezone.utc)

    @staticmethod
    def _entry_body(entry) -> str:
        # Prefer full content over the (often truncated) summary.
        if "content" in entry and entry["content"]:
            return "\n\n".join(c.get("value", "") for c in entry["content"])
        return entry.get("summary", "")
