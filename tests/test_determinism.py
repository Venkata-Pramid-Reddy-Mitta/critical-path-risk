"""Determinism, and the bug this test was written to pin.

The war story (docs/adr/ADR-003 and the README) in one line: an early version
seeded Kahn's ready queue from a set comprehension. On a Python with hash
randomization the order of equally-ready tasks changed between runs, so the
topological order was not stable. The headline numbers survived (the critical
chain's internal order is forced by its edges), but the blast-radius ranking
orders equally-ranked slack tasks by their position in that topological order, so
the published ranking put DM2 and CM3 (both 11 days float, both 0 delay) in a
different order from one run to the next. A committed artifact that is not byte
identical between runs is enough to make a reviewer stop trusting the numbers,
even when the numbers are right.

The important lesson for the test: comparing only the headline summary would not
have caught this, because the summary was stable while the ranking underneath it
was not. So the subprocess check below compares the full ranking order, which is
what actually moved. The fix seeds the queue in the schedule's insertion order
and breaks every tie by that order; if the set ever creeps back in, at least one
hash seed produces a different ranking order and this fails.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from cpr.analysis import analyze
from cpr.config import Policy
from cpr.cpm import compute_cpm
from cpr.report import render_json
from cpr.sensitivity import sensitivity_ranking

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "fixtures" / "program.json"
SRC = REPO_ROOT / "src"


def test_repeated_in_process_runs_are_identical(program):
    first = render_json(analyze(program, Policy()))
    for _ in range(20):
        assert render_json(analyze(program, Policy())) == first


def test_the_topological_order_is_stable_across_runs(program):
    orders = {compute_cpm(program).order for _ in range(20)}
    assert len(orders) == 1


def test_the_full_ranking_order_is_stable_across_runs(program):
    def order():
        cpm = compute_cpm(program)
        return tuple(r.id for r in sensitivity_ranking(program, cpm, 5))

    assert len({order() for _ in range(20)}) == 1


def _ranking_under_hashseed(seed: int) -> str:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(seed)
    env["PYTHONPATH"] = str(SRC)
    code = (
        "from cpr.model import Schedule;"
        "from cpr.cpm import compute_cpm;"
        "from cpr.sensitivity import sensitivity_ranking;"
        f"s=Schedule.from_json(r'{FIXTURE}');"
        "cpm=compute_cpm(s);"
        "print('-'.join(r.id for r in sensitivity_ranking(s, cpm, 5)))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def test_ranking_order_is_identical_across_hash_seeds():
    # The exact value that drifted under the bug: the ordering of the equally
    # ranked slack tasks. Several seeds must produce one identical ordering.
    orders = {_ranking_under_hashseed(seed) for seed in (0, 1, 2, 7, 42, 99)}
    assert len(orders) == 1
    order = orders.pop()
    # And it is the right answer, not just a stable wrong one.
    assert order.startswith("CM1-CM2-AM2")
    assert "CM3-DM2" in order  # the pair that drifted, now fixed in this order
