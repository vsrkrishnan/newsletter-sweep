"""Local markdown sink — the only default. Every other sink is opt-in.

Writes one file per item under knowledge_path/<topic>/, with YAML
frontmatter (created/tags/status/source), and keeps a per-topic index plus
a master index — the same "no orphan pages" discipline the original
knowledge-schema design used, generalized away from one person's tag
vocabulary.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import frontmatter

from ..triage import TriagedItem
from .base import Sink


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80] or "untitled"


class MarkdownSink(Sink):
    """Config:
    ```yaml
    - type: markdown   # knowledge_path from the top-level config is used
    ```
    """

    def __init__(self, options: dict, dry_run: bool = True, knowledge_path: Path | None = None):
        super().__init__(options, dry_run)
        if knowledge_path is None:
            raise ValueError("MarkdownSink requires knowledge_path")
        self.knowledge_path = knowledge_path

    def write_item(self, item: TriagedItem) -> str:
        topic_dir = self.knowledge_path / item.topic
        slug = slugify(item.raw.title)
        target = topic_dir / f"{slug}.md"

        if target.exists():
            # Same title routed twice (e.g. re-run) — don't clobber, dedup
            # already should have caught this via state, but be defensive.
            return f"skipped, already exists: {target}"

        post = frontmatter.Post(_body(item))
        post["created"] = date.today().isoformat()
        post["tags"] = [item.topic]
        post["status"] = "captured"
        post["source"] = item.raw.source_name
        post["source_url"] = item.raw.url

        if self.dry_run:
            return f"[dry-run] would write {target}"

        topic_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(frontmatter.dumps(post) + "\n")
        self._update_index(topic_dir / "index.md", item, slug)
        self._update_index(self.knowledge_path / "index.md", item, f"{item.topic}/{slug}")
        return f"wrote {target}"

    def write_digest(self, digest_markdown: str, digest_title: str) -> str:
        digest_dir = self.knowledge_path.parent / "digests"
        target = digest_dir / f"{date.today().isoformat()}.md"
        if self.dry_run:
            return f"[dry-run] would write digest to {target}"
        digest_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(digest_markdown)
        return f"wrote digest to {target}"

    @staticmethod
    def _update_index(index_path: Path, item: TriagedItem, link: str) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        line = f"- [{item.raw.title}]({link}.md) — {item.raw.source_name}\n"
        if index_path.exists():
            existing = index_path.read_text()
            if line.strip() in existing:
                return
            index_path.write_text(existing + line)
        else:
            index_path.write_text(f"# Index\n\n{line}")


def _body(item: TriagedItem) -> str:
    return f"""# {item.raw.title}

**Source:** {item.raw.source_name} · captured via newsletter-sweep

## What it is
{item.relevant_reason}

## Why this applies to me
{item.applies_to_me}

## Link
{item.raw.url}
"""
