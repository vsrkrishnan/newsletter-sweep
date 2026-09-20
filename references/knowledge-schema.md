# Knowledge file schema

What the markdown sink actually writes, so nothing about the output format
is a surprise once a sweep runs live.

## Layout

```
knowledge_path/
├── index.md                 ← master index, one line per item, all topics
├── <topic>/
│   ├── index.md              ← per-topic index
│   └── <slugified-title>.md  ← one file per kept item
└── uncategorized/
    └── ...                   ← same shape, for anything that didn't match a topic
```

## Item file format

```markdown
---
created: 2026-09-20
tags: [topic-slug]
status: captured
source: Newsletter or feed name
source_url: https://...
---

# Item title

**Source:** Newsletter or feed name · captured via newsletter-sweep

## What it is
[The triage model's reason this qualified — usually 1-2 sentences.]

## Why this applies to me
[The synthesis model's applies_to_me restatement — see
references/why-the-profile-gate.md for why this field exists at all.]

## Link
https://...
```

`status: captured` marks a freshly swept item, distinct from anything you
promote or expand by hand later. Nothing in this tool overwrites a file
that already exists at the same slug — a second sweep that would produce
the same title is treated as a re-run collision and skipped, not clobbered
(dedup via `state.py` should normally prevent this from being reached at
all; the file-exists check is a second line of defense).

## Digest file

One file per run at `<knowledge_path's parent>/digests/YYYY-MM-DD.md` —
see `digest.py` for the exact format. It lists what was kept, what was
skipped and why, and run counts; a thin week is reported as thin, not
padded to look busier than it was.
