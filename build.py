"""CLI entry point: drive the multi-agent pipeline from the terminal.

Examples:
    # Build the default TODO API example
    python build.py --example todo_api

    # Build from a free-form description
    python build.py "A FastAPI service that exposes /shorten and /<slug> for URL shortening, persisted to SQLite."

    # Read the request from a file
    python build.py --request-file ./examples/url_shortener.txt
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # python-dotenv is optional; the SDK will still pick up env vars if
    # they are set in the shell.
    pass

from orchestrator import run_pipeline

EXAMPLES_DIR = Path(__file__).parent / "examples"
DEFAULT_OUTPUT_ROOT = Path(os.environ.get("OUTPUT_DIR", Path(__file__).parent / "runs"))


def _load_example(name: str) -> str:
    path = EXAMPLES_DIR / f"{name}.txt"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in EXAMPLES_DIR.glob("*.txt"))) or "(none)"
        raise SystemExit(
            f"No example named '{name}'. Available examples: {available}"
        )
    return path.read_text(encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build.py",
        description="Run the multi-agent software development pipeline.",
    )
    parser.add_argument(
        "request",
        nargs="?",
        help="Free-form description of the application to build.",
    )
    parser.add_argument(
        "--request-file",
        type=Path,
        help="Path to a text file containing the request.",
    )
    parser.add_argument(
        "--example",
        help=f"Use a built-in example from {EXAMPLES_DIR}/<name>.txt",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Where to write the run directory (default: {DEFAULT_OUTPUT_ROOT}).",
    )
    parser.add_argument(
        "--model",
        help="Override the Claude model (default: env CLAUDE_MODEL or claude-sonnet-4-5).",
    )
    return parser.parse_args(argv)


def resolve_request(args: argparse.Namespace) -> str:
    sources = [bool(args.request), bool(args.request_file), bool(args.example)]
    if sum(sources) != 1:
        raise SystemExit(
            "Provide exactly one of: a positional request, --request-file, or --example."
        )
    if args.example:
        return _load_example(args.example)
    if args.request_file:
        return args.request_file.read_text(encoding="utf-8")
    return args.request


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. Copy .env.example to .env"
            " and fill it in, or export the variable in your shell.",
            file=sys.stderr,
        )
        return 2

    request = resolve_request(args)

    print("=" * 60)
    print("Multi-agent software development pipeline")
    print("=" * 60)
    print(f"Request: {request[:200]}{'...' if len(request) > 200 else ''}")
    print(f"Output root: {args.output_dir}")
    print()

    result = run_pipeline(
        project_request=request,
        output_root=args.output_dir,
        model=args.model,
    )

    print()
    print("=" * 60)
    print(result.summary())
    print("=" * 60)
    print(f"Generated project: {result.run_dir}")

    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
