# newsletter-sweep

A tool that reads your newsletters so you don't have to skim all of them.

You tell it what you care about. It checks your feeds (or inbox), figures
out which items are actually worth your time, explains *why* each one
matters to you specifically, and saves the good ones — to a folder on your
computer, or to Notion if you set that up. Everything else gets quietly
skipped.

It's built to work with any of Anthropic (Claude), OpenAI, or a model
running on your own machine — though right now Claude is the only one
verified end to end (see [Which AI models work](#which-ai-models-work)).
It can run once when you ask it to, or on a schedule so it just handles
itself.

## Try it in 5 minutes

```bash
pip install git+https://github.com/vsrkrishnan/newsletter-sweep.git
mkdir my-sweep && cd my-sweep
newsletter-sweep init          # answer two quick questions
```

`init` creates three files in the folder and tells you exactly what to do
with each. In short:

1. **Paste your AI key** into the `.env` file it created — e.g.
   `ANTHROPIC_API_KEY=sk-ant-...`. (You can skip this if you chose to run a
   model on your own machine with Ollama.) The key stays in `.env`, which
   is kept out of git for you.
2. **Edit `applies_to_me.md`** — a couple of lines about what you care
   about, so it can judge what's worth your time.
3. **Add a newsletter URL or two** under `sources:` in `config.yaml`.

Then see it work, without saving anything yet:

```bash
newsletter-sweep run --dry-run # shows what it *would* do — saves nothing
```

No email account needed, no sign-ups, nothing to connect. It starts by
reading public RSS feeds and saving results as plain text files, so you can
see it working in a few minutes.

> **Getting an AI key:** an [Anthropic key](https://console.anthropic.com/)
> or [OpenAI key](https://platform.openai.com/api-keys) takes a minute to
> create and costs a few cents per run. Or run a local model with
> [Ollama](https://ollama.com) and pay nothing — pick that at `init` time.

## Why it asks you two questions first

`newsletter-sweep init` asks: what do you do, and what are you trying to
get better at. That's it — takes under a minute.

Here's why it bothers to ask: a generic newsletter summarizer just tells
you what an article says, which you could get from the article itself.
What's actually useful is being told *why it matters to you* — not "this
is about AI agents" but "this changes how you'd handle the thing you're
working on." The tool can only do that if it knows a little about you
first. So it won't run at all until you've told it — more on why in
[`references/why-the-profile-gate.md`](references/why-the-profile-gate.md).

## What it does, step by step

1. **Checks your sources** — RSS feeds, or your inbox if you set that up.
2. **Decides what's worth keeping**, using your two-line profile as the
   bar. Skips anything you've already seen before, even if it shows up
   with a different link.
3. **Explains why each keeper matters to you**, in a sentence or two.
4. **Saves it** — to a local folder by default, or Notion if you've
   connected that.

Every step that doesn't need judgment (checking for duplicates, saving
files, formatting) is handled by plain code — the AI model is only asked
to make the calls that actually need it: is this worth keeping, and why
does it matter to you. That keeps it cheap to run and easy to trust.

## Which AI models work

The tool talks to each provider over its plain HTTP API, so swapping
providers is just a config change. That said, they're not all equally
proven yet:

| Provider | Status |
|---|---|
| **Anthropic (Claude)** | ✅ Verified end to end. This is the recommended choice today. |
| **OpenAI** | ◐ Should work — the known compatibility gotchas are handled (it adapts to both old and new token limits, and uses OpenAI's JSON mode), but it hasn't been run against the live API yet. Also works with OpenAI-compatible endpoints (Groq, Together, local vLLM). |
| **Ollama** (local models) | ◐ Should work — uses Ollama's JSON mode so even smaller models route reliably. Not yet verified end to end, and triage quality still depends on the model you pick. |

The prompts themselves carry nothing provider-specific, so nothing is
locked to one vendor by design. If you run the OpenAI or Ollama path and
hit (or don't hit) a snag, an issue or PR is welcome — that's what moves
these from ◐ to ✅.

## Setting up where things come from and go

**Where content comes from:**

| Source | What you need |
|---|---|
| RSS feeds | Nothing — just paste the feed URLs in |
| Your inbox (e.g. Gmail) | An app password — a few minutes to set up, [instructions here](references/connector-setup.md) |

**Where the good stuff gets saved:**

| Destination | Setup |
|---|---|
| A local folder | Nothing — it's on by default |
| Notion | A free access token — two clicks, [instructions here](references/connector-setup.md) |

## Organizing what it saves

By default, the tool figures out categories on its own from your first
batch of content and checks with you before locking them in. If you'd
rather decide up front, you can list your own categories in the config
file instead. Either way, nothing gets thrown away — anything that doesn't
fit a category still gets saved, just under "uncategorized." Details in
[`references/taxonomy-guide.md`](references/taxonomy-guide.md).

## Running it on autopilot

Add [`.github/workflows/sweep.yml`](.github/workflows/sweep.yml) to your
own repo and it'll run on a schedule automatically (once a week by
default — easy to change). Or run it from any computer's own cron job the
same way you'd run any command-line tool.

## See a real example

[`examples/security-aware-pm/`](examples/security-aware-pm/) shows a
filled-in setup end to end — a real profile, a real config — so you can
see what "done" looks like before writing your own.

## Want to know how it works under the hood?

The design decisions — why it uses two different AI models, why it never
strips links out of newsletter text, how to add a new source or
destination — are written up in [`references/`](references/) rather than
cluttering this page.

## License

Apache-2.0
