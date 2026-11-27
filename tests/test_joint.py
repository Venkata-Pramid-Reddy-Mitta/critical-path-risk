"""The joint-slip boundary: the pair single-slip analysis cannot see."""

from __future__ import annotations

import pytest

from cpr.cpm import compute_cpm
from cpr.joint import find_worst_joint_blind_spot, joint_slip_delay


def test_joint_slip_of_an_empty_set_moves_nothing(program):
    cpm = compute_cpm(program)
    assert joint_slip_delay(program, [], cpm.project_duration, cpm.order) == 0


def test_a_negative_joint_slip_is_refused(program):
    cpm = compute_cpm(program)
    with pytest.raises(ValueError, match="negative"):
        joint_slip_delay(program, [("DM1", -1)], cpm.project_duration, cpm.order)


def test_two_safe_slips_combine_to_move_the_finish(program):
    cpm = compute_cpm(program)
    base = cpm.project_duration
    # Each individually safe (11 <= float 11), together they overrun by 11.
    assert joint_slip_delay(program, [("DM2", 11), ("DM3", 11)], base, cpm.order) == 11


def test_the_worst_blind_spot_is_a_pair_safe_alone_but_costly_together(program):
    cpm = compute_cpm(program)
    spot = find_worst_joint_blind_spot(program, cpm)
    assert spot is not None
    assert spot.single_delay_a == 0
    assert spot.single_delay_b == 0
    assert spot.joint_delay > 0


def test_the_worst_blind_spot_joint_delay_is_eleven(program):
    cpm = compute_cpm(program)
    spot = find_worst_joint_blind_spot(program, cpm)
    assert spot.joint_delay == 11
    assert spot.slip_each == 11


def test_the_worst_blind_spot_pair_is_on_the_data_chain(program):
    cpm = compute_cpm(program)
    spot = find_worst_joint_blind_spot(program, cpm)
    assert {spot.task_a, spot.task_b} <= {"DM1", "DM2", "DM3", "DM4", "CM3"}


def test_no_blind_spot_when_there_is_no_shared_slack():
    from cpr.model import Schedule

    # Two independent slack tasks that do not interact: no pair can combine.
    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 10, "deps": []},
        {"id": "B", "name": "b", "workstream": "w", "duration": 10, "deps": ["A"]},
        {"id": "S1", "name": "s1", "workstream": "w", "duration": 1, "deps": ["A"]},
        {"id": "C", "name": "c", "workstream": "w", "duration": 10, "deps": ["B", "S1"]},
    ]
    s = Schedule.from_dict({"tasks": rows})
    cpm = compute_cpm(s)
    assert find_worst_joint_blind_spot(s, cpm) is None


def test_joint_delay_is_at_least_the_larger_single_delay(program):
    # A sanity property: applying both slips cannot help the schedule, so the
    # joint delay is never smaller than either slip applied alone.
    cpm = compute_cpm(program)
    base = cpm.project_duration
    from cpr.sensitivity import blast_radius

    pairs = [("AM1", "DM1"), ("CM3", "DM2"), ("CM4", "DM4")]
    for a, b in pairs:
        slip = 6
        single_a = blast_radius(program, a, slip, base, cpm.order)
        single_b = blast_radius(program, b, slip, base, cpm.order)
        joint = joint_slip_delay(program, [(a, slip), (b, slip)], base, cpm.order)
        assert joint >= max(single_a, single_b)
