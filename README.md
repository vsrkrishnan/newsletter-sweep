# newsletter-sweep

An always-on agent that triages newsletters and feeds against *your* stated
interests, dedups against what you already have, and files the good ones
into a knowledge base you own — locally, or wherever you configure it.

Any LLM provider (Anthropic, OpenAI, Ollama). Any topic (nothing is
hardcoded — declare topics up front, or let the first sweep propose them
from your actual content). Any sink (local markdown by default, Notion
opt-in). Runs by hand, on cron, or in GitHub Actions.

## The 5-minute path

```bash
pip install newsletter-sweep
mkdir my-sweep && cd my-sweep
newsletter-sweep init          # two questions, drafts your profile + a starter config
# edit applies_to_me.md, add a feed URL or two to config.yaml
newsletter-sweep run --dry-run # see what it would do, writes nothing
```

No email account, no Notion, no OAuth. RSS is the default source and local
markdown the default sink — you can be looking at real output in a few
minutes.

## Why `applies_to_me.md` is required

Without a stated point of view, triage degenerates into a generic
summarizer — which every newsletter-digest tool already does. The one
thing that makes this useful is a line, per item, written **from your own
seat**: not "this is about AI agents" but "this changes how you'd approach
X, given what you're building." `newsletter-sweep init` doesn't hand you a
blank file — it asks two questions and drafts a starting profile for you to
edit. A run with no profile refuses to proceed, on purpose; see
[`references/why-the-profile-gate.md`](references/why-the-profile-gate.md).

## How it works

```
source (rss, imap)  →  triage (LLM, cheap model)  →  router (your topics)  →  sink (markdown, notion)
                                     ↓
                        synthesis (LLM, stronger model)
                        "why this applies to me"
```

Two model slots, not one — a cheap model runs the relevance pass on every
candidate item; a stronger model only runs synthesis on items that already
passed. That split is most of where per-run cost lives. See
[`references/adapter-authoring.md`](references/adapter-authoring.md).

Deterministic work — dedup, HTML extraction, digest assembly, file/API
writes — is plain code, not prompts. The LLM is only asked to make
judgment calls: is this relevant, and what does it mean for you.

Each item is triaged in its own isolated call rather than one giant batch
prompt — a raw newsletter body can run to tens of thousands of characters,
and that never needs to sit in one context alongside everything else.

## Topics

Two modes, set in `config.yaml`:

- **`declared`** — you list topics up front. Deterministic, best once you
  know your shape.
- **`learned`** (default) — routes into whatever folders already exist
  under `knowledge_path`; on a genuinely empty first run, proposes a
  taxonomy from your real content and asks you to confirm (or, on an
  unattended/cron run, accepts provisionally and flags it in the digest for
  you to review).

Either way, nothing is silently dropped — anything that doesn't fit a known
topic lands in `uncategorized/`.

## Sources

| Source | Auth | Setup |
|---|---|---|
| RSS/Atom | none | list feed URLs in `config.yaml` |
| IMAP | app password | see [`references/connector-setup.md`](references/connector-setup.md) |

Gmail via IMAP + an app password is the practical path — far simpler than
OAuth. A self-hosted Gmail MCP server is documented as a power-user
alternative in the same reference, along with why it's meaningfully harder
to set up than it looks.

## Sinks

| Sink | Default | Setup |
|---|---|---|
| Local markdown | yes | none — writes under `knowledge_path` |
| Notion | opt-in | integration token, two clicks — see `references/connector-setup.md` |

## Running unattended

`.github/workflows/sweep.yml` runs a scheduled sweep in GitHub Actions —
copy it into your own repo, add your secrets, done. Cron works the same way
locally: `newsletter-sweep run --config /path/to/config.yaml`.

## Example

[`examples/security-aware-pm/`](examples/security-aware-pm/) is a full
worked profile and config — a reader with a security background triaging
AI/product newsletters — showing what a filled-in setup actually looks
like end to end.

## Design notes worth reading before you extend this

- **Never strip URL-bearing lines when extracting a body.** Many
  newsletters are link-dense digests where each item is a headline plus a
  link; naive "clean up the text" extraction can gut the substance out of
  a genuinely valuable source. Trim tracking/redirect noise only.
- **Keep raw payloads out of any single large context.** A newsletter body
  can run to tens of thousands of characters; triage.py deliberately calls
  the LLM once per item rather than batching many raw bodies into one
  prompt.

## License

Apache-2.0
