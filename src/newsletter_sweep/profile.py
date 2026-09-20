"""The applies_to_me profile — a hard requirement before the first sweep.

Without it, triage degenerates into a generic summarizer: exactly the
commodity this tool exists to replace. See the original design note this
generalizes from: newsletter-triage.md's `applies_to_shiva` field, which
restates each item from the reader's own seat rather than summarizing it
neutrally.

This module only enforces and reads the profile. Drafting it interactively
lives in setup.py, which is where the "don't hand the user a blank file"
requirement is actually met.
"""
from __future__ import annotations

from pathlib import Path


class MissingProfileError(Exception):
    """Raised when a sweep is attempted with no applies_to_me profile."""

    def __init__(self, profile_path: Path):
        self.profile_path = profile_path
        super().__init__(
            f"No profile at {profile_path}.\n\n"
            "A sweep without one is just a generic newsletter digest — the thing "
            "this tool exists to replace. Run `newsletter-sweep init` to answer a "
            "couple of questions and draft one, or write it yourself: a short "
            "paragraph on what you do and what you're trying to get better at."
        )


MIN_PROFILE_CHARS = 40  # guards against an empty or placeholder file, not prose quality


def load_profile(profile_path: Path) -> str:
    """Read and validate the applies_to_me profile. Raises MissingProfileError
    if it's absent or looks like an untouched placeholder."""
    if not profile_path.exists():
        raise MissingProfileError(profile_path)

    text = profile_path.read_text().strip()
    if len(text) < MIN_PROFILE_CHARS or "TODO" in text[:200]:
        raise MissingProfileError(profile_path)

    return text


def write_profile(profile_path: Path, content: str) -> None:
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(content.strip() + "\n")
