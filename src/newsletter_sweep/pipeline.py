"""Orchestrates one sweep run, end to end. This is the code equivalent of
Steps 0-8 in the original Claude Code command — ported to real code per the
project's stated bar: deterministic work is code, not prompts. The only
LLM calls in the whole run happen inside triage.py and (on a first learned-
taxonomy run) taxonomy.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import Config
from .digest import build_digest
from .profile import load_profile
from .providers import build_router
from .sinks import build_sink
from .sources import build_source
from .state import State
from .taxonomy import resolve_taxonomy

logger = logging.getLogger(__name__)


class RunResult:
    def __init__(self):
        self.sources_scanned = 0
        self.kept = 0
        self.skipped = 0
        self.sink_actions: list[str] = []
        self.digest_markdown = ""
        self.digest_title = ""
        self.dry_run = True


def run_sweep(config: Config, *, interactive: bool = False) -> RunResult:
    """Raises MissingProfileError (from profile.py) if applies_to_me.md is
    absent — this is intentional; the caller (cli.py) turns that into a
    clean error message pointing at `init`, not a stack trace.
    """
    profile = load_profile(config.profile_path)
    router = build_router(config.provider)
    state = State.load_or_init(config.state_path)

    result = RunResult()
    result.dry_run = config.dry_run

    # --- fetch ---
    raw_items = []
    for source_cfg in config.sources:
        source = build_source(source_cfg.type, source_cfg.options)
        try:
            fetched = source.fetch_since(state.last_processed)
        except Exception as exc:
            logger.warning("Source %s failed entirely, skipping it this run: %s",
                            source_cfg.type, exc)
            continue
        raw_items.extend(fetched)
        result.sources_scanned += 1

    # --- taxonomy ---
    taxonomy = resolve_taxonomy(config, raw_items, router, interactive=interactive)

    # --- triage ---
    from .triage import triage_items  # local import: avoids a cycle with taxonomy at module load

    triage_run = triage_items(raw_items, config, profile, state, router, taxonomy)
    result.kept = len(triage_run.kept)
    result.skipped = len(triage_run.skipped)

    # --- sinks ---
    sinks = [
        build_sink(s.type, s.options, dry_run=config.dry_run, knowledge_path=config.knowledge_path)
        for s in config.sinks
    ]
    for item in triage_run.kept:
        for sink in sinks:
            try:
                result.sink_actions.append(sink.write_item(item))
            except Exception as exc:
                logger.error("Sink %s failed on %r: %s", sink.__class__.__name__,
                             item.raw.title, exc)
                result.sink_actions.append(f"FAILED ({sink.__class__.__name__}): {exc}")

    title, digest_md = build_digest(triage_run, taxonomy, result.sources_scanned)
    result.digest_title = title
    result.digest_markdown = digest_md
    for sink in sinks:
        try:
            result.sink_actions.append(sink.write_digest(digest_md, title))
        except Exception as exc:
            logger.error("Digest write failed on %s: %s", sink.__class__.__name__, exc)

    # --- state ---
    if raw_items:
        newest = max((i.published for i in raw_items), default=state.last_processed)
        state.last_processed = max(newest, state.last_processed)
    else:
        state.last_processed = datetime.now(timezone.utc)

    if not config.dry_run:
        state.save(config.state_path)

    return result
