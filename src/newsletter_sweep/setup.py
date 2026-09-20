"""Interactive `newsletter-sweep init` — the 60-second setup that makes the
applies_to_me requirement (see profile.py) cheap instead of a blank-page
problem. Two questions, a drafted profile, and a starter config; the user
edits rather than writes from scratch.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .profile import write_profile

CONFIG_TEMPLATE = """\
# newsletter-sweep config — see references/ for the full option reference.

knowledge_path: ./knowledge
profile_path: ./applies_to_me.md
state_path: ./.newsletter-sweep/state.json

provider:
  name: {provider_name}          # anthropic | openai | ollama
  triage_model: {triage_model}
  synthesis_model: {synthesis_model}
  api_key_env: {api_key_env}     # unused for ollama

topics:
  mode: {topics_mode}            # declared | learned
  declared: []                   # only used when mode: declared

sources:
  - type: rss
    feeds: []                    # add newsletter/feed URLs here
  # - type: imap                 # uncomment to add an inbox — see references/connector-setup.md
  #   host: imap.gmail.com
  #   username_env: NEWSLETTER_IMAP_USER
  #   password_env: NEWSLETTER_IMAP_APP_PASSWORD
  #   mailbox: INBOX

sinks:
  - type: markdown                # local, always on
  # - type: notion                 # opt-in — see references/connector-setup.md
  #   integration_token_env: NOTION_TOKEN
  #   parent_page_id: "..."

dry_run: true                     # flip to false once a dry run looks right
"""

PROVIDER_DEFAULTS = {
    "anthropic": ("claude-haiku-4-5-20251001", "claude-sonnet-5", "ANTHROPIC_API_KEY"),
    "openai": ("gpt-5-mini", "gpt-5", "OPENAI_API_KEY"),
    "ollama": ("llama3.2", "llama3.2", "OLLAMA_API_KEY"),
}


def run_init(target_dir: Path, *, interactive: bool = True) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    config_path = target_dir / "config.yaml"
    profile_path = target_dir / "applies_to_me.md"

    if config_path.exists() and profile_path.exists():
        print(f"Already set up: {config_path} and {profile_path} both exist. "
              "Delete them first if you want to redo setup.")
        return

    print("newsletter-sweep setup\n")

    provider_name = _ask_choice(
        "Which LLM provider?", ["anthropic", "openai", "ollama"], default="anthropic",
        interactive=interactive,
    )
    triage_model, synthesis_model, api_key_env = PROVIDER_DEFAULTS[provider_name]

    topics_mode = _ask_choice(
        "Declare topics now, or learn them from your first sweep?",
        ["learned", "declared"], default="learned", interactive=interactive,
    )

    if not profile_path.exists():
        profile_text = _draft_profile(interactive=interactive)
        write_profile(profile_path, profile_text)
        print(f"\nWrote {profile_path} — open it and edit before your first real run.")

    if not config_path.exists():
        config_path.write_text(
            CONFIG_TEMPLATE.format(
                provider_name=provider_name,
                triage_model=triage_model,
                synthesis_model=synthesis_model,
                api_key_env=api_key_env,
                topics_mode=topics_mode,
            )
        )
        print(f"Wrote {config_path} — add at least one RSS feed URL under `sources:`.")

    needs_key = provider_name != "ollama"
    if needs_key:
        _write_env_file(target_dir / ".env", api_key_env)
    _write_gitignore(target_dir / ".gitignore")

    _print_next_steps(target_dir, api_key_env, needs_key)


def _write_env_file(env_path: Path, api_key_env: str) -> None:
    if env_path.exists():
        return
    env_path.write_text(
        "# Secrets live here, never in config.yaml. This file is gitignored.\n"
        f"# Paste your key after the = (no quotes needed):\n"
        f"{api_key_env}=\n"
        "\n"
        "# If you add an IMAP source or Notion sink later, their secrets go\n"
        "# here too — see references/connector-setup.md.\n"
        "# NEWSLETTER_IMAP_USER=\n"
        "# NEWSLETTER_IMAP_APP_PASSWORD=\n"
        "# NOTION_TOKEN=\n"
    )
    print(f"Wrote {env_path} — paste your API key into it (this file is gitignored).")


def _write_gitignore(gitignore_path: Path) -> None:
    # A user who wires up the GitHub Actions workflow will commit this whole
    # directory. Without this, their .env (with the API key) would go with
    # it. So init always drops a .gitignore that protects secrets and the
    # per-run state, whether or not they ever use git.
    if gitignore_path.exists():
        return
    gitignore_path.write_text(
        ".env\n"
        ".newsletter-sweep/\n"
    )


def _print_next_steps(target_dir: Path, api_key_env: str, needs_key: bool) -> None:
    print("\nNext steps:")
    step = 1
    if needs_key:
        print(f"  {step}. Paste your API key into {target_dir / '.env'} "
              f"(the {api_key_env} line).")
        step += 1
    print(f"  {step}. Edit {target_dir / 'applies_to_me.md'} so triage is about you.")
    step += 1
    print(f"  {step}. Add a feed URL or two under `sources:` in {target_dir / 'config.yaml'}.")
    step += 1
    print(f"  {step}. Run `newsletter-sweep run --dry-run` — shows what it would do, "
          "writes nothing.")


def _ask_choice(question: str, options: list[str], *, default: str, interactive: bool) -> str:
    if not interactive:
        return default
    prompt = f"{question} ({'/'.join(options)}) [{default}]: "
    answer = input(prompt).strip().lower()
    return answer if answer in options else default


def _draft_profile(*, interactive: bool) -> str:
    if not interactive:
        return (
            "TODO: describe what you do and what you're trying to get better at. "
            "This is what makes triage specific to you instead of a generic digest."
        )
    print(
        "Two questions to draft your profile — edit the result afterward, "
        "this doesn't need to be perfect:\n"
    )
    role = input("1. What do you do (role, domain, what you're building)? ").strip()
    goal = input("2. What are you trying to get better at or stay current on? ").strip()

    parts = []
    if role:
        parts.append(role)
    if goal:
        parts.append(f"Right now I'm focused on: {goal}.")
    if not parts:
        return (
            "TODO: describe what you do and what you're trying to get better at. "
            "This is what makes triage specific to you instead of a generic digest."
        )
    parts.append(
        "When triaging content, favor items that are specific and actionable over "
        "ones that are merely motivational or already common knowledge to me."
    )
    return "\n\n".join(parts)
