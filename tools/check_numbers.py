#!/usr/bin/env python
"""Fail the build when a document quotes a figure the code no longer produces.

This is the other half of the receipts mechanism. It loads docs/metrics.json,
loads each checked document, and for every metric confirms that at least one of
its anchor phrases (the exact wording with the value substituted in) appears
somewhere in the checked set. If a README number is edited by hand, the anchor
with the correct value vanishes and this fails, which is the whole point: the
numbers cannot drift from the code without the build going red.

Two design choices learned the hard way and recorded in references/receipts.md:
anchors name the number plus two or three words (never a whole clause, which
would straddle a wrapped line and match nothing), and small numbers are only ever
checked through an anchor, never by bare digits, because a lone "2" appears by
coincidence in any document.

The forward check (every metric present) fails the build. The reverse check (any
number in the README that no metric explains) prints for review but does not fail
on its own, because prose legitimately contains years, version strings and task
ids; strict mode turns it into a failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
METRICS = REPO_ROOT / "docs" / "metrics.json"

# Numbers that legitimately appear in prose and are not code-produced metrics.
PROSE_WHITELIST = {
    "0", "1", "2", "3", "4", "5",  # small counts in explanatory sentences
    "2.0", "7",  # the default policy thresholds, themselves documented in policy.toml
    "0.3.0", "2026",  # version string and copyright year
    "001", "002", "003", "004", "005",  # ADR numbers
    "3.11", "3.12", "3.13",  # supported Python versions
    "10", "20", "100",  # round figures used in explanations
    "1.0",  # the buggy overstatement ratio named in the war story
    "12",  # the slip of total float plus one that moves the finish
}


def _value_candidates(value) -> list[str]:
    """Every string a number might legitimately be written as in prose."""
    if isinstance(value, bool):
        return [str(value)]
    if isinstance(value, int):
        return [str(value)]
    if isinstance(value, float):
        cands = {f"{value:g}", f"{value:.1f}", str(value)}
        if value.is_integer():
            cands.add(str(int(value)))
        return sorted(cands)
    return [str(value)]


def _strip_code(markdown: str) -> str:
    """Remove fenced blocks, inline code, HTML tags and URLs before the reverse scan."""
    text = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    return text


def forward_check(payload: dict, docs: dict[str, str]) -> list[str]:
    """Return a list of failure messages, one per metric that is not anchored."""
    metrics = payload["metrics"]
    anchors = payload["anchors"]
    blob = "\n".join(docs.values())
    failures: list[str] = []

    for name, value in metrics.items():
        if value is None:
            failures.append(f"{name}: metric value is null (collector did not fill it)")
            continue
        templates = anchors.get(name)
        if not templates:
            failures.append(f"{name}: no anchor phrases declared (small numbers must be anchored)")
            continue
        candidates = _value_candidates(value)
        found = any(
            tmpl.format(cand) in blob for tmpl in templates for cand in candidates
        )
        if not found:
            shown = [tmpl.format(candidates[0]) for tmpl in templates]
            failures.append(f"{name}={value}: no anchor matched, expected one of {shown}")
    return failures


def reverse_check(payload: dict, readme: str) -> list[str]:
    """Numbers in the README prose that match no metric value. Advisory."""
    allowed: set[str] = set(PROSE_WHITELIST)
    for value in payload["metrics"].values():
        allowed.update(_value_candidates(value))

    prose = _strip_code(readme)
    unexplained: list[str] = []
    for match in re.finditer(r"(?<![\w.$])\d+(?:\.\d+)?(?![\w.])", prose):
        token = match.group(0)
        if token not in allowed:
            unexplained.append(token)
    return sorted(set(unexplained))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail on unexplained README numbers")
    args = parser.parse_args()

    if not METRICS.exists():
        raise SystemExit("check_numbers: docs/metrics.json missing; run collect_metrics.py first")
    payload = json.loads(METRICS.read_text(encoding="utf-8"))

    docs: dict[str, str] = {}
    for rel in payload["checked_documents"]:
        path = REPO_ROOT / rel
        if not path.exists():
            raise SystemExit(f"check_numbers: checked document missing: {rel}")
        docs[rel] = path.read_text(encoding="utf-8")

    failures = forward_check(payload, docs)
    unexplained = reverse_check(payload, docs.get("README.md", ""))

    if unexplained:
        print("advisory: README numbers with no matching metric (review these):")
        print("  " + ", ".join(unexplained))

    if failures:
        print("\ncheck_numbers: FAIL")
        for f in failures:
            print(f"  {f}")
        return 1

    if args.strict and unexplained:
        print("\ncheck_numbers: FAIL (strict): unexplained README numbers above")
        return 1

    print(f"check_numbers: OK, {len(payload['metrics'])} metrics anchored in {len(docs)} documents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
