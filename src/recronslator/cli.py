"""CLI entry point for recronslator.

Commands:
    recronslate "Every Monday at 3am"         → 0 3 * * 1
    recronslate --describe "0 3 * * 1"        → Every Monday at 3:00 AM
    echo "Every 15 minutes" | recronslate     → */15 * * * *
"""

from __future__ import annotations

import argparse
import sys

import recronslator


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="recronslate",
        description=(
            "Translate between natural language schedules and cron expressions.\n\n"
            "Based on the original cronslator project: "
            "https://github.com/pyslop/cronslator"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  recronslate 'Every Monday at 3am'        → 0 3 * * 1\n"
            "  recronslate --describe '0 3 * * 1'       → Every Monday at 3:00 AM\n"
            "  echo 'Every 15 minutes' | recronslate    → */15 * * * *"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {recronslator.__version__}",
    )
    parser.add_argument(
        "--describe", "-d",
        action="store_true",
        help="Translate a cron expression to English (reverse direction)",
    )
    parser.add_argument(
        "schedule",
        nargs="*",
        help="Schedule text (natural language or cron expression). "
             "If omitted, reads from stdin.",
    )

    args = parser.parse_args()

    # Determine input
    if args.schedule:
        text = " ".join(args.schedule)
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not text:
        print("Error: no input provided.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.describe:
            result = recronslator.describe(text)
        else:
            result = recronslator.cronslate(text)
        print(result)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
