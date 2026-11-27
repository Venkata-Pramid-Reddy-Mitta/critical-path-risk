"""Slack chains and the shared-float overstatement they expose."""

from __future__ import annotations

from itertools import pairwise

from cpr.chains import SlackChain, enumerate_slack_chains
from cpr.cpm import compute_cpm


def _chain(tasks, apparent, shared):
    return SlackChain(tasks=tuple(tasks), apparent_buffer=apparent, shared_buffer=shared)


def test_overstatement_ratio_is_apparent_over_shared():
    c = _chain(["X", "Y"], apparent=56, shared=11)
    assert abs(c.overstatement_ratio - 56 / 11) < 1e-9


def test_a_shared_buffer_of_zero_reads_as_infinite_overstatement():
    c = _chain(["X"], apparent=5, shared=0)
    assert c.overstatement_ratio == float("inf")


def test_chain_length_counts_tasks():
    assert _chain(["X", "Y", "Z"], 3, 1).length == 3


def test_the_worst_program_chain_is_the_data_chain(program):
    cpm = compute_cpm(program)
    report = enumerate_slack_chains(program, cpm)
    worst = report.worst(min_length=2)
    assert worst is not None
    assert worst.tasks == ("DM1", "DM2", "DM3", "DM4")


def test_the_data_chain_apparent_buffer_is_fifty_six(program):
    cpm = compute_cpm(program)
    worst = enumerate_slack_chains(program, cpm).worst(min_length=2)
    assert worst.apparent_buffer == 56


def test_the_data_chain_shared_buffer_is_eleven(program):
    cpm = compute_cpm(program)
    worst = enumerate_slack_chains(program, cpm).worst(min_length=2)
    assert worst.shared_buffer == 11


def test_the_data_chain_overstates_buffer_fivefold(program):
    cpm = compute_cpm(program)
    worst = enumerate_slack_chains(program, cpm).worst(min_length=2)
    assert round(worst.overstatement_ratio, 1) == 5.1


def test_apparent_buffer_is_the_sum_of_member_total_floats(program):
    cpm = compute_cpm(program)
    worst = enumerate_slack_chains(program, cpm).worst(min_length=2)
    assert worst.apparent_buffer == sum(cpm.total_float[t] for t in worst.tasks)


def test_shared_buffer_equals_the_head_task_total_float(program):
    cpm = compute_cpm(program)
    worst = enumerate_slack_chains(program, cpm).worst(min_length=2)
    assert worst.shared_buffer == cpm.total_float[worst.tasks[0]]


def test_every_chain_contains_only_non_critical_tasks(program):
    cpm = compute_cpm(program)
    report = enumerate_slack_chains(program, cpm)
    for chain in report.chains:
        for tid in chain.tasks:
            assert cpm.total_float[tid] > 0


def test_every_chain_is_a_real_dependency_path(program):
    cpm = compute_cpm(program)
    report = enumerate_slack_chains(program, cpm)
    for chain in report.chains:
        for earlier, later in pairwise(chain.tasks):
            assert earlier in program[later].deps


def test_a_program_with_no_slack_has_no_chains():
    # A single straight line: every task is critical, so there are no chains.
    from cpr.model import Schedule

    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 3, "deps": []},
        {"id": "B", "name": "b", "workstream": "w", "duration": 3, "deps": ["A"]},
        {"id": "C", "name": "c", "workstream": "w", "duration": 3, "deps": ["B"]},
    ]
    s = Schedule.from_dict({"tasks": rows})
    cpm = compute_cpm(s)
    report = enumerate_slack_chains(s, cpm)
    assert report.chains == ()
    assert report.worst(min_length=2) is None


def test_a_single_task_chain_cannot_overstate_anything():
    from cpr.model import Schedule

    # A critical spine with one dangling slack task: the chain has length 1 and
    # its apparent and shared buffers are equal, so worst(min_length=2) is None.
    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 10, "deps": []},
        {"id": "B", "name": "b", "workstream": "w", "duration": 10, "deps": ["A"]},
        {"id": "S", "name": "s", "workstream": "w", "duration": 1, "deps": ["A"]},
        {"id": "C", "name": "c", "workstream": "w", "duration": 10, "deps": ["B", "S"]},
    ]
    s = Schedule.from_dict({"tasks": rows})
    cpm = compute_cpm(s)
    report = enumerate_slack_chains(s, cpm)
    assert all(ch.length == 1 for ch in report.chains)
    assert report.worst(min_length=2) is None


def test_chain_enumeration_is_not_truncated_on_the_program(program):
    cpm = compute_cpm(program)
    report = enumerate_slack_chains(program, cpm)
    assert report.truncated is False
