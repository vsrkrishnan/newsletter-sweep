# Taxonomy guide

There is no built-in default taxonomy, on purpose — your first genuinely
new-user problem with a tool like this is almost always "the categories it
ships with aren't the categories my content is actually about." So
`newsletter-sweep` doesn't ship any.

## Two modes

Set in `config.yaml` under `topics.mode`:

### `declared`
```yaml
topics:
  mode: declared
  declared: [product-strategy, security, market-signals]
```
You decide up front. Deterministic, and the right choice once you know
roughly what shape your content takes.

### `learned` (default)
```yaml
topics:
  mode: learned
```
On each run, the router first looks for folders that already exist under
`knowledge_path`. If some exist, those *are* your topics — stable once set,
no repeated re-proposals.

If `knowledge_path` is empty (a genuine first run) and there's real content
to look at, the tool proposes 4-8 topics from that actual batch and:
- **in an interactive terminal:** asks you to confirm or edit the list
  before proceeding,
- **in a non-interactive/cron run:** accepts the proposal provisionally,
  seeds the folders, and flags it explicitly at the top of that run's
  digest — so it's never silently locked in without you seeing it.

## The catch-all

Regardless of mode, anything that doesn't cleanly match a known topic goes
to `uncategorized/` rather than being dropped or forced into the nearest
bad fit. If you're seeing a lot land there, that's a signal to either add a
topic or reconsider your `declared` list — not a bug to route around.

## Migrating from declared to learned (or back)

Nothing here is destructive. Switching `topics.mode` doesn't move or
rename any existing files; it only changes how the *next* run decides where
new items go. Folders you've already got stay exactly where they are.
