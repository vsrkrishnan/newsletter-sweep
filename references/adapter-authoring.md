# Adding a source, sink, or provider

Each of the three surfaces is a small interface. Adding one doesn't touch
the pipeline (`pipeline.py`) at all — that's the point of the interfaces.

## A new source

Subclass `newsletter_sweep.sources.base.Source`:

```python
from newsletter_sweep.sources.base import RawItem, Source

class MySource(Source):
    def fetch_since(self, watermark: datetime) -> list[RawItem]:
        ...  # return only items newer than watermark
```

Rules that matter:
- Never let one bad entry kill the whole fetch — log and skip it, return
  the rest. Sources run inside a try/except in `pipeline.py`, but a source
  that dies on its first malformed item returns nothing instead of
  everything-else.
- `RawItem.body` should be the fullest text available. **Never strip
  URL-bearing lines** when extracting a body — many newsletters are
  link-dense digests where each item is a headline plus a link, and
  filtering "noise" that looks like a URL can gut the actual content.
  See `sources/imap_source.py`'s `_strip_html` for the pattern: preserve
  link hrefs as visible `text (url)` pairs, don't just discard tags.

Register it in `sources/__init__.py`'s `SOURCE_REGISTRY`.

## A new sink

Subclass `newsletter_sweep.sinks.base.Sink`:

```python
from newsletter_sweep.sinks.base import Sink

class MySink(Sink):
    def write_item(self, item: TriagedItem) -> str:
        ...  # persist; return a short human-readable description

    def write_digest(self, digest_markdown: str, digest_title: str) -> str:
        ...  # optional — default is a no-op
```

Respect `self.dry_run` — a dry-run sink must not touch disk, an API, or
anything external, and should return a `"[dry-run] would ..."` string
describing what it would have done. Every existing test for a sink checks
this explicitly; a new sink should too.

Register it in `sinks/__init__.py`'s `build_sink()`.

## A new provider

Subclass `newsletter_sweep.providers.base.Provider`:

```python
from newsletter_sweep.providers.base import Provider, ProviderError

class MyProvider(Provider):
    def complete(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        ...  # raise ProviderError (not a vendor-specific exception) on failure
```

Two things the rest of the codebase depends on:

- **Always raise `ProviderError`**, never let a vendor SDK's own exception
  type leak out. `cli.py` and `triage.py` both catch `ProviderError`
  specifically — a vendor-specific exception bypasses that and produces an
  ugly traceback instead of a clean message.
- **A broken provider must fail loudly once, not silently per item.**
  `triage.py` re-raises `ProviderError` immediately rather than treating it
  as "skip this one item" — a bad API key fails identically on every item
  in the batch, and swallowing that 20 times in a row both spams the log
  and (with a real backend) burns 20 API calls on calls that will all fail
  the same way.

Register it in `providers/__init__.py`'s `PROVIDER_REGISTRY`.

## The two-model split

`ModelRouter` (in `providers/base.py`) exposes `.triage()` and
`.synthesize()`, bound to two separately configurable models. This isn't
decorative — `triage()` runs once per *candidate* item (high volume, needs
to be cheap) and `synthesize()` runs once per item that already passed
(low volume, needs to be good, since its output is the
`applies_to_me` line the whole tool exists to produce — see
`why-the-profile-gate.md`). A new call site should go through one of these
two, not call `provider.complete()` directly, so the cost/quality split
stays enforced in one place.
