from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analyzer import analyze_repository
from .git import repository_is_git
from .reporting import to_json, to_markdown, to_terminal
from .scanner.files import scan_repository
from .sources import analyze_source


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repo-pulse", description="Deterministic repository maintenance evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("analyze", "scan"):
        sub = subparsers.add_parser(command)
        sub.add_argument(
            "repository",
            nargs="?",
            default=".",
            help="local repository path (analyze also accepts an HTTPS Git URL)",
        )
        default_format = "terminal" if command == "analyze" else "json"
        formats = ("json", "markdown", "terminal") if command == "analyze" else ("json", "markdown")
        sub.add_argument("--format", choices=formats, default=default_format)
        sub.add_argument("--output", type=Path)
    doctor = subparsers.add_parser("doctor", help="Check whether a target can be analyzed.")
    doctor.add_argument("repository", nargs="?", default=".")
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = Path(args.repository).resolve()
        if args.command == "doctor":
            if not root.is_dir():
                raise FileNotFoundError("Repository directory does not exist: {}".format(root))
            print(json.dumps({"repository": str(root), "readable": True, "git_repository": repository_is_git(root)}))
            return 0
        if args.command == "scan":
            records = scan_repository(root)
            payload = json.dumps([record.__dict__ for record in records], indent=2, sort_keys=True)
            if args.format == "markdown":
                payload = "# RepoPulse scan\n\n" + "\n".join(
                    "- `{}`: {} lines, {} bytes".format(record.path, record.line_count, record.size)
                    for record in records
                ) + "\n"
        else:
            analysis = analyze_source(args.repository)
            if args.format == "json":
                payload = to_json(analysis)
            elif args.format == "markdown":
                payload = to_markdown(analysis)
            else:
                payload = to_terminal(analysis)
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="" if payload.endswith("\n") else "\n")
        return 0
    except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
        print("repo-pulse: error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
