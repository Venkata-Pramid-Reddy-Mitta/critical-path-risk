"""Shared fixtures. The committed program is loaded once and reused.

A small hand-checkable schedule (``tiny``) is also provided: a diamond whose
every number can be worked out on paper, so a test failure points at the code
rather than at a disagreement about what the right answer is.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cpr.analysis import analyze
from cpr.config import Policy
from cpr.cpm import compute_cpm
from cpr.model import Schedule

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "fixtures" / "program.json"


@pytest.fixture
def program() -> Schedule:
    return Schedule.from_json(FIXTURE)


@pytest.fixture
def program_result(program: Schedule):
    return analyze(program, Policy())


@pytest.fixture
def tiny() -> Schedule:
    """A diamond: A -> {B, C} -> D, worked by hand in the test docstrings.

    A(2) at 0..2. B(5) at 2..7, C(3) at 2..5. D(4) needs both, starts at 7,
    finishes at 11. Longest path A,B,D = 11. C has total float 2 (B is two days
    longer than C) and free float 2.
    """
    return Schedule.from_dict(
        {
            "tasks": [
                {"id": "A", "name": "a", "workstream": "w", "duration": 2, "deps": []},
                {"id": "B", "name": "b", "workstream": "w", "duration": 5, "deps": ["A"]},
                {"id": "C", "name": "c", "workstream": "w", "duration": 3, "deps": ["A"]},
                {"id": "D", "name": "d", "workstream": "w", "duration": 4, "deps": ["B", "C"]},
            ]
        }
    )


@pytest.fixture
def tiny_result(tiny: Schedule):
    return compute_cpm(tiny)
