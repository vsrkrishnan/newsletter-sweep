"""Relevance filtering + applies_to_me synthesis.

This is where the original design's context-management lesson gets ported
into code instead of relying on host-side subagent delegation: each item is
triaged with its own small, isolated call (source text truncated to a
reasonable excerpt) so a large batch never has to sit in one giant prompt.
Nothing here holds more than one item's raw body in memory/context at a time.

Two LLM calls per candidate item, not one — kept separate on purpose:
  1. triage (cheap model): relevant y/n + why, one line.
  2. synthesize (stronger model), only for items that passed (1): the
     applies_to_me restatement — see profile.py's docstring for why this
     field is the whole point of the tool rather than a nice-to-have.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .config import Config
from .providers import ModelRouter, ProviderError
from .sources import RawItem
from .state import State
from .taxonomy import TaxonomyResult, route_topic

logger = logging.getLogger(__name__)

MAX_BODY_CHARS = 6000  # keeps each isolated call small regardless of source size

TRIAGE_PROMPT = """Reader profile (what they care about):
{profile}

Relevance themes for this sweep:
{themes}

Item:
Title: {title}
Source: {source}
Excerpt: {body}

Decide if this item is genuinely relevant to the reader given their profile \
and the themes above. Respond with ONLY a JSON object, no other text:
{{"relevant": true or false, "reason": "one sentence", "topic": "best-guess topic slug or empty string"}}
"""

SYNTHESIZE_PROMPT = """Reader profile:
{profile}

Item:
Title: {title}
Source: {source}
Excerpt: {body}

Write, from the reader's own seat (not a neutral third party), 1-2 sentences \
on how this specifically applies to them given their profile. Be concrete — \
name what changes for them, not a generic "this is relevant to X." \
Respond with ONLY that text, no preamble, no quotes around it.
"""


@dataclass
class TriagedItem:
    raw: RawItem
    relevant_reason: str
    applies_to_me: str
    topic: str


@dataclass
class TriageRun:
    kept: list[TriagedItem]
    skipped: list[tuple[RawItem, str]]  # (item, reason)


def triage_items(
    items: list[RawItem],
    config: Config,
    profile: str,
    state: State,
    router: ModelRouter,
    taxonomy: TaxonomyResult,
) -> TriageRun:
    kept: list[TriagedItem] = []
    skipped: list[tuple[RawItem, str]] = []
    themes = "\n".join(f"- {t}" for t in config.relevance_themes)

    for item in items:
        if state.is_duplicate(item.url, item.title + " " + item.body[:200]):
            skipped.append((item, "duplicate (seen_urls/seen_ideas)"))
            continue

        body_excerpt = item.body[:MAX_BODY_CHARS]

        try:
            raw = router.triage(
                system="You triage content against a reader's stated interests. "
                "Be selective — a sharp shortlist beats broad coverage.",
                prompt=TRIAGE_PROMPT.format(
                    profile=profile, themes=themes, title=item.title,
                    source=item.source_name, body=body_excerpt,
                ),
            )
        except ProviderError:
            # A broken provider (bad key, unreachable endpoint, no daemon)
            # fails identically on every item — re-raise once instead of
            # burning the rest of the batch on calls that will all fail
            # the same way and drowning the run in duplicate warnings.
            raise

        try:
            decision = _parse_json(raw)
        except ValueError as exc:
            # A single malformed response is a model quirk, not a broken
            # setup — skip just this item and keep going.
            logger.warning("Could not parse triage response for %r, skipping: %s",
                            item.title, exc)
            skipped.append((item, f"malformed triage response: {exc}"))
            continue

        if not decision.get("relevant"):
            skipped.append((item, decision.get("reason", "not relevant")))
            continue

        try:
            applies = router.synthesize(
                system="You write a sharp, specific first-person-relevant note. "
                "No generic restatement of the source.",
                prompt=SYNTHESIZE_PROMPT.format(
                    profile=profile, title=item.title, source=item.source_name,
                    body=body_excerpt,
                ),
                max_tokens=200,
            ).strip()
        except ProviderError as exc:
            logger.warning("Synthesis call failed for %r: %s", item.title, exc)
            applies = decision.get("reason", "")

        topic = route_topic(decision.get("topic", ""), taxonomy.topics)
        kept.append(TriagedItem(raw=item, relevant_reason=decision.get("reason", ""),
                                 applies_to_me=applies, topic=topic))
        state.mark_seen(item.url, item.title + " " + item.body[:200])

    return TriageRun(kept=kept, skipped=skipped)


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    # Models sometimes wrap JSON in a code fence despite instructions.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"non-JSON triage response: {raw[:200]!r}") from exc
