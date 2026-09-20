from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import Config, ConfigError
from .profile import MissingProfileError
from .providers import ProviderError
from .setup import run_init


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="newsletter-sweep")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Interactive setup: profile + starter config.")
    init_parser.add_argument("--dir", default=".", help="Directory to set up in (default: cwd)")
    init_parser.add_argument("--non-interactive", action="store_true",
                              help="Write placeholders instead of prompting (for scripted setup).")

    run_parser = sub.add_parser("run", help="Run one sweep.")
    run_parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    run_parser.add_argument("--dry-run", action="store_true", default=None,
                             help="Force dry-run regardless of config.yaml's dry_run setting.")
    run_parser.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                             help="Force a real run (writes files / calls sinks) even if "
                                  "config.yaml has dry_run: true.")
    run_parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "init":
        run_init(Path(args.dir), interactive=not args.non_interactive)
        return 0

    if args.command == "run":
        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            format="%(levelname)s %(name)s: %(message)s",
        )
        return _run(args)

    return 1


def _run(args) -> int:
    from .pipeline import run_sweep  # deferred: keeps `init` fast and dependency-light

    try:
        config = Config.load(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run is not None:
        config.dry_run = args.dry_run

    try:
        result = run_sweep(config, interactive=sys.stdin.isatty())
    except MissingProfileError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ProviderError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1

    mode = "DRY RUN — nothing was written" if result.dry_run else "LIVE RUN"
    print(f"\n=== newsletter-sweep: {mode} ===")
    print(f"Sources scanned: {result.sources_scanned}")
    print(f"Kept: {result.kept}  |  Skipped: {result.skipped}")
    print("\nSink actions:")
    for action in result.sink_actions:
        print(f"  - {action}")
    print(f"\n{result.digest_title}\n{'-' * len(result.digest_title)}")
    print(result.digest_markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
