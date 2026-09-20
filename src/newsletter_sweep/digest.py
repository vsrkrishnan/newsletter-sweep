"""Weekly digest assembly — pure string formatting, no LLM calls. Ported
from Step 5 of the original design, generalized off Shiva-specific fields.
"""
from __future__ import annotations

from datetime import date

from .taxonomy import TaxonomyResult
from .triage import TriageRun


def build_digest(run: TriageRun, taxonomy: TaxonomyResult, sources_scanned: int) -> tuple[str, str]:
    """Returns (title, markdown)."""
    today = date.today().isoformat()
    title = f"Newsletter Digest — {today}"

    lines = [f"# {title}", ""]

    if taxonomy.proposed:
        lines += [
            "> **Topics were auto-proposed this run** (no config or existing "
            "folders found) — review `knowledge_path/` and adjust, or set "
            "`topics.mode: declared` in config.yaml to lock them in.",
            "",
        ]

    if run.kept:
        lines.append("## Kept")
        lines.append("")
        for item in run.kept:
            lines += [
                f"### {item.raw.title} — {item.raw.source_name}",
                f"**Topic:** {item.topic}",
                f"**What it is:** {item.relevant_reason}",
                f"**Why this applies to me:** {item.applies_to_me}",
                f"**Link:** {item.raw.url}",
                "",
            ]
    else:
        lines += ["## Kept", "", "Nothing qualified this run. That's a valid outcome — "
                  "a thin week should be reported thin, not padded.", ""]

    lines.append("## Skipped")
    lines.append("")
    for item, reason in run.skipped:
        lines.append(f"- **{item.title}** ({item.source_name}): {reason}")
    if not run.skipped:
        lines.append("(none)")
    lines.append("")

    lines += [
        "## This run in numbers",
        f"- Sources scanned: {sources_scanned}",
        f"- Items evaluated: {len(run.kept) + len(run.skipped)}",
        f"- Kept: {len(run.kept)}",
        f"- Skipped: {len(run.skipped)}",
        "",
    ]

    return title, "\n".join(lines)
