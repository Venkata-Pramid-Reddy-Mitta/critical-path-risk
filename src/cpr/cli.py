"""Why this file exists.

The command line is where a reviewer meets the tool, so the exit codes are part
of the interface and are chosen to mean something a build can act on:

    0  the analysis ran and the program is clean against the policy
    2  the analysis ran and a hidden risk was flagged (only with --gate)
    1  the analysis could not run (bad input, a cycle, a broken policy file)

The distinction between 2 and 1 is the important one: "I looked and the answer is
no" must never be confused with "I could not look". A program office can wire
``cpr analyze --gate`` into their own pipeline and trust a 2 to mean a real
finding, not a crash. The default (no --gate) always exits 0 after printing, so
``make report`` on the deliberately flagged fixture does not turn the build red,
which is the mistake ADR-005 and CI trap five both warn against.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from .analysis import Gate, analyze
from .config import PolicyError, load_policy
from .model import Schedule, ScheduleError
from .report import render_console, render_html, render_json

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_RISK = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cpr",
        description="Rank WBS tasks by the true blast radius of a slip.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    an = sub.add_parser("analyze", help="analyze a program JSON file")
    an.add_argument("program", type=Path, help="path to the program JSON")
    an.add_argument("--policy", type=Path, default=None, help="policy TOML (default: shipped)")
    an.add_argument("--slip", type=int, default=None, help="override the slip size in days")
    an.add_argument("--html", type=Path, default=None, help="write the HTML report to this path")
    an.add_argument("--json", type=Path, default=None, help="write the JSON summary to this path")
    an.add_argument(
        "--gate",
        action="store_true",
        help="exit 2 when a hidden risk is flagged (default exits 0 after printing)",
    )
    an.add_argument("--quiet", action="store_true", help="suppress the console report")
    return parser


def _run_analyze(args: argparse.Namespace) -> int:
    try:
        schedule = Schedule.from_json(args.program)
        policy = load_policy(args.policy)
    except (ScheduleError, PolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAILED

    if args.slip is not None:
        try:
            policy = replace(policy, slip_days=args.slip)
            policy.__post_init__()  # re-validate the override
        except PolicyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_FAILED

    try:
        result = analyze(schedule, policy)
    except ScheduleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAILED

    if not args.quiet:
        print(render_console(result))

    if args.html is not None:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(result), encoding="utf-8")
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(render_json(result), indent=2), encoding="utf-8")

    if args.gate and result.gate is Gate.FLAGGED:
        return EXIT_RISK
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _run_analyze(args)
    parser.error(f"unknown command: {args.command}")  # pragma: no cover
    return EXIT_FAILED  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
