"""Blast radius, re-routing thresholds, shared buffer, and the two headline tasks."""

from __future__ import annotations

import pytest

from cpr.cpm import compute_cpm
from cpr.sensitivity import (
    blast_radius,
    measure_shared_buffer,
    nearest_rerouting,
    rerouting_threshold,
    sensitivity_ranking,
    top_hidden_task,
)


def test_a_zero_slip_moves_nothing(program):
    cpm = compute_cpm(program)
    assert blast_radius(program, "CM1", 0, cpm.project_duration, cpm.order) == 0


def test_a_negative_slip_is_refused(program):
    cpm = compute_cpm(program)
    with pytest.raises(ValueError, match="negative"):
        blast_radius(program, "CM1", -1, cpm.project_duration, cpm.order)


def test_a_critical_task_slip_moves_the_finish_one_for_one(program):
    cpm = compute_cpm(program)
    for slip in (1, 3, 5, 9):
        assert blast_radius(program, "CM1", slip, cpm.project_duration, cpm.order) == slip


def test_a_slack_task_absorbs_a_slip_up_to_its_float(program):
    cpm = compute_cpm(program)
    # DM1 has 11 days float; a 5-day slip is fully absorbed.
    assert blast_radius(program, "DM1", 5, cpm.project_duration, cpm.order) == 0


def test_a_slack_task_slip_beyond_its_float_moves_the_finish(program):
    cpm = compute_cpm(program)
    # 12 days is one past DM1's 11-day float, so the finish moves by one.
    assert blast_radius(program, "DM1", 12, cpm.project_duration, cpm.order) == 1


def test_the_hidden_task_slip_of_five_delays_the_finish_two_days(program):
    cpm = compute_cpm(program)
    assert blast_radius(program, "AM1", 5, cpm.project_duration, cpm.order) == 2


def test_measure_shared_buffer_agrees_with_the_float(program):
    cpm = compute_cpm(program)
    measured = measure_shared_buffer(
        program, "DM1", cpm.total_float["DM1"], cpm.project_duration, cpm.order
    )
    assert measured == 11


def test_measure_shared_buffer_rejects_a_negative_float(program):
    cpm = compute_cpm(program)
    with pytest.raises(ValueError, match="negative"):
        measure_shared_buffer(program, "DM1", -1, cpm.project_duration, cpm.order)


def test_rerouting_threshold_of_a_slack_task_is_its_float_plus_one(program):
    cpm = compute_cpm(program)
    assert rerouting_threshold(program, cpm, "AM1") == 4
    assert rerouting_threshold(program, cpm, "DM1") == 12


def test_rerouting_threshold_of_a_critical_task_is_one(program):
    cpm = compute_cpm(program)
    assert rerouting_threshold(program, cpm, "CM1") == 1


def test_the_ranking_scores_every_task(program):
    cpm = compute_cpm(program)
    ranking = sensitivity_ranking(program, cpm, 5)
    assert len(ranking) == len(program)


def test_the_ranking_is_sorted_by_blast_radius_descending(program):
    cpm = compute_cpm(program)
    ranking = sensitivity_ranking(program, cpm, 5)
    delays = [r.blast_radius for r in ranking]
    assert delays == sorted(delays, reverse=True)


def test_the_critical_tasks_lead_the_ranking_at_slip_five(program):
    cpm = compute_cpm(program)
    ranking = sensitivity_ranking(program, cpm, 5)
    top_eight = ranking[:8]
    assert all(r.is_critical for r in top_eight)
    assert all(r.blast_radius == 5 for r in top_eight)


def test_the_hidden_task_is_am1_off_the_critical_path(program):
    cpm = compute_cpm(program)
    ranking = sensitivity_ranking(program, cpm, 5)
    hidden = top_hidden_task(ranking)
    assert hidden is not None
    assert hidden.id == "AM1"
    assert hidden.is_critical is False
    assert hidden.blast_radius == 2


def test_the_hidden_task_outranks_the_wider_slack_tasks(program):
    cpm = compute_cpm(program)
    ranking = sensitivity_ranking(program, cpm, 5)
    order = [r.id for r in ranking]
    assert order.index("AM1") < order.index("DM1")


def test_the_nearest_rerouting_task_is_am1_at_four_days(program):
    cpm = compute_cpm(program)
    ranking = sensitivity_ranking(program, cpm, 5)
    reroute = nearest_rerouting(ranking)
    assert reroute.id == "AM1"
    assert reroute.rerouting_threshold == 4


def test_top_hidden_task_is_none_when_no_slack_task_is_exposed():
    from cpr.model import Schedule

    # A straight critical line plus a slack task with float larger than the slip.
    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 10, "deps": []},
        {"id": "B", "name": "b", "workstream": "w", "duration": 10, "deps": ["A"]},
        {"id": "S", "name": "s", "workstream": "w", "duration": 1, "deps": ["A"]},
        {"id": "C", "name": "c", "workstream": "w", "duration": 10, "deps": ["B", "S"]},
    ]
    s = Schedule.from_dict({"tasks": rows})
    cpm = compute_cpm(s)
    ranking = sensitivity_ranking(s, cpm, 2)
    assert top_hidden_task(ranking) is None


def test_ranking_rows_carry_name_and_workstream(program):
    cpm = compute_cpm(program)
    ranking = sensitivity_ranking(program, cpm, 5)
    am1 = next(r for r in ranking if r.id == "AM1")
    assert am1.name == "Service inventory and assessment"
    assert am1.workstream == "App Modernization"
