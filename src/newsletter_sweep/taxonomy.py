"""Topic routing — deliberately not a fixed taxonomy.

The original design's routing table (mental-models / market-signals /
ai-tools-hacks / quotes / read-later) is specific to one person's interests.
A stranger's newsletters could be about anything, so this module supports
two modes instead of shipping a default:

  - declared: the user lists topics in config.yaml up front.
  - learned:  topics come from whatever folders already exist at
              knowledge_path, or — on a genuinely empty first run — are
              proposed from the real content of that run and confirmed
              by the user (or, in a non-interactive/cron context, accepted
              provisionally and flagged for review, never silently locked in).

Either way, `uncategorized/` exists as a catch-all so nothing is dropped
just because it doesn't fit a known bucket.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config import Config
from .providers import ModelRouter
from .sources import RawItem

UNCATEGORIZED = "uncategorized"
MAX_TOPIC_LEN = 60


def sanitize_topic(raw: str) -> str | None:
    """Every topic name becomes a directory name (knowledge_path/<topic>/),
    so every topic — whether typed by the user in config.yaml or proposed
    by the model from a batch of untrusted newsletter content — passes
    through here before it's trusted as a path component. Without this, a
    ``declared`` topic like ``../../etc`` or a learned-mode proposal
    engineered via prompt injection in a newsletter body could write
    outside knowledge_path entirely.

    Returns None if nothing safe survives (caller should drop the topic
    rather than fall back to something unsafe).
    """
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    slug = slug[:MAX_TOPIC_LEN].strip("-")
    return slug or None

TAXONOMY_PROPOSAL_PROMPT = """You are helping set up a knowledge-routing taxonomy \
for a personal content-triage tool. Below are titles and short excerpts from a \
real batch of newsletter/feed content the user is subscribed to.

Propose 4-8 topic folder names (short, kebab-case, e.g. "product-strategy" or \
"climate-policy") that would sensibly cover this content. Base the topics on \
what's actually here, not on generic categories. Return ONLY the topic names, \
one per line, no numbering or commentary.

CONTENT SAMPLE:
{sample}
"""


class TaxonomyResult:
    def __init__(self, topics: list[str], proposed: bool):
        self.topics = topics
        self.proposed = proposed  # True if this run auto-proposed topics (needs user review)


def resolve_taxonomy(
    config: Config, items: list[RawItem], router: ModelRouter, *, interactive: bool
) -> TaxonomyResult:
    if config.topics.mode == "declared":
        return TaxonomyResult(topics=_sanitize_all(config.topics.declared), proposed=False)

    existing = _existing_topic_folders(config.knowledge_path)
    if existing:
        return TaxonomyResult(topics=existing, proposed=False)

    if not items:
        # Nothing to learn from yet and nothing configured — everything
        # this run goes to uncategorized/, which is correct, not a bug.
        return TaxonomyResult(topics=[], proposed=False)

    proposed_topics = _propose_topics(items, router)
    if interactive:
        proposed_topics = _confirm_with_user(proposed_topics)
        proposed = False
    else:
        proposed = True  # cron/headless run: accept, but the digest must say so

    _seed_topic_folders(config.knowledge_path, proposed_topics)
    return TaxonomyResult(topics=proposed_topics, proposed=proposed)


def _existing_topic_folders(knowledge_path: Path) -> list[str]:
    if not knowledge_path.exists():
        return []
    return sorted(
        p.name
        for p in knowledge_path.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != UNCATEGORIZED
    )


def _propose_topics(items: list[RawItem], router: ModelRouter) -> list[str]:
    # Titles/bodies here come straight from external newsletter content —
    # untrusted input to this prompt. The model's response is sanitized
    # below via _sanitize_all before it's ever treated as a path component.
    sample = "\n\n".join(f"- {i.title}\n  {i.body[:300]}" for i in items[:20])
    raw = router.synthesize(
        system="You design pragmatic, content-derived information taxonomies.",
        prompt=TAXONOMY_PROPOSAL_PROMPT.format(sample=sample),
        max_tokens=200,
    )
    topics = [line.strip().strip("-").strip() for line in raw.splitlines() if line.strip()]
    return _sanitize_all(topics) or [UNCATEGORIZED]


def _confirm_with_user(proposed: list[str]) -> list[str]:
    print("\nNo topics configured yet. Based on your first batch of content, proposing:")
    for t in proposed:
        print(f"  - {t}")
    answer = input("\nUse these? [Y/n/edit as comma-separated list]: ").strip()
    if not answer or answer.lower() == "y":
        return proposed
    if answer.lower() == "n":
        return [UNCATEGORIZED]
    return _sanitize_all(answer.split(","))


def _sanitize_all(raw_topics: list[str]) -> list[str]:
    seen: list[str] = []
    for raw in raw_topics:
        slug = sanitize_topic(raw)
        if slug and slug != UNCATEGORIZED and slug not in seen:
            seen.append(slug)
    return seen


def _seed_topic_folders(knowledge_path: Path, topics: list[str]) -> None:
    knowledge_path.mkdir(parents=True, exist_ok=True)
    (knowledge_path / UNCATEGORIZED).mkdir(exist_ok=True)
    for topic in topics:
        (knowledge_path / topic).mkdir(exist_ok=True)


def route_topic(candidate: str, topics: list[str]) -> str:
    """Simple containment match against known topics; falls back to
    uncategorized. Triage (an LLM call) does the real semantic routing —
    this is only the fallback when that call is skipped or fails.
    """
    if not topics:
        return UNCATEGORIZED
    lowered = candidate.lower().strip()
    for topic in topics:
        if topic.lower() == lowered:
            return topic
    return UNCATEGORIZED
