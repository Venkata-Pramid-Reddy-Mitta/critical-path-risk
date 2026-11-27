"""Shared helpers for the experiments: locate the repo, load the fixture, write JSON.

Each experiment imports from here so the five scripts stay short and write their
output the same way, into docs/experiments, where the metrics collector reads it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

FIXTURE = REPO_ROOT / "fixtures" / "program.json"
OUT_DIR = REPO_ROOT / "docs" / "experiments"


def load_program():
    from cpr.model import Schedule

    return Schedule.from_json(FIXTURE)


def write_result(name: str, payload: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
