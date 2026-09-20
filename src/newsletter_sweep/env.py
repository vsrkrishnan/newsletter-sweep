"""Minimal .env loader — stdlib only, no python-dotenv dependency.

A .env file sitting next to config.yaml is the natural place for the one or
two secrets this tool needs (the LLM API key, and optionally IMAP/Notion
credentials). Loading it automatically is what removes the single biggest
deploy papercut: otherwise a fresh user has to know to `export
ANTHROPIC_API_KEY=...` in the same shell, and hits a "no API key" error
with no idea why.

Real environment variables always win over the file — so a CI/cron run that
injects secrets as real env vars (e.g. the GitHub Actions workflow) is never
overridden by a stray committed .env.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path) -> int:
    """Load KEY=VALUE lines from `path` into os.environ, without clobbering
    variables already set in the real environment. Returns the number of
    variables loaded. A missing file is not an error — returns 0.

    Deliberately small: supports `KEY=value`, `export KEY=value`, `#`
    comments, blank lines, and single/double-quoted values. It is not a
    full shell parser and doesn't try to be.
    """
    if not path.exists():
        return 0

    loaded = 0
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if not key or key in os.environ:  # real env wins; never clobber
            continue
        os.environ[key] = value
        loaded += 1
    return loaded
