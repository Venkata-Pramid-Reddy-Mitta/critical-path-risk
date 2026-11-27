"""The critical path method: passes, floats, critical path, cycle detection."""

from __future__ import annotations

from itertools import pairwise

import pytest

from cpr.cpm import (
    CpmResult,
    CycleError,
    compute_cpm,
    project_finish,
    topological_order,
)
from cpr.model import Schedule


def test_topological_order_places_every_dependency_before_its_task(program):
    order = topological_order(program)
    position = {tid: i for i, tid in enumerate(order)}
    for task in program:
        for dep in task.deps:
            assert position[dep] < position[task.id]


def test_topological_order_includes_every_task_once(program):
    order = topological_order(program)
    assert sorted(order) == sorted(program.ids)


def test_a_cycle_is_detected_and_named():
    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 1, "deps": ["C"]},
        {"id": "B", "name": "b", "workstream": "w", "duration": 1, "deps": ["A"]},
        {"id": "C", "name": "c", "workstream": "w", "duration": 1, "deps": ["B"]},
    ]
    s = Schedule.from_dict({"tasks": rows})
    with pytest.raises(CycleError) as exc:
        topological_order(s)
    assert set(exc.value.remaining) == {"A", "B", "C"}


def test_a_self_free_two_node_cycle_is_detected():
    # Build around the self-dependency guard by making two tasks point at
    # each other, which is still a cycle but not a self-loop.
    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 1, "deps": ["B"]},
        {"id": "B", "name": "b", "workstream": "w", "duration": 1, "deps": ["A"]},
    ]
    s = Schedule.from_dict({"tasks": rows})
    with pytest.raises(CycleError):
        compute_cpm(s)


def test_project_finish_is_the_longest_path_on_the_diamond(tiny):
    # A,B,D = 2+5+4 = 11 beats A,C,D = 2+3+4 = 9.
    assert project_finish(tiny) == 11


def test_project_finish_on_the_program_is_75(program):
    assert project_finish(program) == 75


def test_earliest_start_of_a_root_task_is_zero(tiny_result):
    assert tiny_result.es["A"] == 0


def test_earliest_finish_is_start_plus_duration(tiny_result):
    assert tiny_result.ef["B"] == tiny_result.es["B"] + 5


def test_a_merge_task_starts_after_its_latest_predecessor(tiny_result):
    # D waits for B (finishes at 7), not C (finishes at 5).
    assert tiny_result.es["D"] == 7


def test_total_float_is_zero_on_the_critical_path(tiny_result):
    for tid in ("A", "B", "D"):
        assert tiny_result.total_float[tid] == 0


def test_total_float_of_the_slack_task_is_two(tiny_result):
    assert tiny_result.total_float["C"] == 2


def test_free_float_of_the_slack_task_is_two(tiny_result):
    # C can slip 2 days before D's earliest start would move.
    assert tiny_result.free_float["C"] == 2


def test_the_critical_path_of_the_diamond_is_a_b_d(tiny_result):
    assert tiny_result.critical_path == ("A", "B", "D")


def test_project_duration_matches_the_last_finish(program_result_cpm):
    assert program_result_cpm.project_duration == max(program_result_cpm.ef.values())


@pytest.fixture
def program_result_cpm(program) -> CpmResult:
    return compute_cpm(program)


def test_the_program_critical_path_is_eight_tasks(program_result_cpm):
    assert program_result_cpm.critical_path == (
        "CM1", "CM2", "AM2", "AM3", "AM4", "TD2", "TD3", "TD4",
    )


def test_every_critical_task_has_zero_total_float(program_result_cpm):
    for tid in program_result_cpm.critical:
        assert program_result_cpm.total_float[tid] == 0


def test_the_data_chain_tasks_each_show_eleven_days_float(program_result_cpm):
    for tid in ("DM1", "DM2", "DM3"):
        assert program_result_cpm.total_float[tid] == 11


def test_the_near_critical_task_shows_three_days_float(program_result_cpm):
    assert program_result_cpm.total_float["AM1"] == 3


def test_is_critical_agrees_with_zero_float(program_result_cpm):
    for tid in program_result_cpm.order:
        assert program_result_cpm.is_critical(tid) == (program_result_cpm.total_float[tid] == 0)


def test_free_float_never_exceeds_total_float(program_result_cpm):
    for tid in program_result_cpm.order:
        assert program_result_cpm.free_float[tid] <= program_result_cpm.total_float[tid]


def test_a_single_task_program_finishes_at_its_duration():
    s = Schedule.from_dict({"tasks": [{"id": "A", "name": "a", "workstream": "w", "duration": 9}]})
    r = compute_cpm(s)
    assert r.project_duration == 9
    assert r.critical_path == ("A",)


def test_critical_path_trace_follows_real_dependency_edges(program, program_result_cpm):
    path = program_result_cpm.critical_path
    for earlier, later in pairwise(path):
        assert earlier in program[later].deps


def test_critical_path_starts_at_a_root_and_ends_at_a_leaf(program, program_result_cpm):
    path = program_result_cpm.critical_path
    assert program[path[0]].deps == ()
    assert program.successors(path[-1]) == ()
