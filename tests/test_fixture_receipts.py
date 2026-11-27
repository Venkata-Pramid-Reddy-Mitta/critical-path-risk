"""Every number published in the README, pinned in one place against the fixture.

If a published figure changes, both this test and the receipts checker fail, so
a drifted number cannot reach a reader through either path.
"""

from __future__ import annotations

from cpr.analysis import analyze
from cpr.config import Policy
from cpr.report import render_json


def test_the_published_headline_numbers(program):
    data = render_json(analyze(program, Policy()))

    assert data["task_count"] == 16
    assert data["project_finish_days"] == 75
    assert data["critical_path_length"] == 8

    assert data["worst_chain"]["tasks"] == ["DM1", "DM2", "DM3", "DM4"]
    assert data["worst_chain"]["apparent_buffer_days"] == 56
    assert data["worst_chain"]["shared_buffer_days"] == 11
    assert round(data["worst_chain"]["overstatement_ratio"], 1) == 5.1

    assert data["hidden_task"]["id"] == "AM1"
    assert data["hidden_task"]["total_float_days"] == 3
    assert data["hidden_task"]["blast_radius_days"] == 2
    assert data["hidden_task"]["rerouting_threshold_days"] == 4

    assert data["joint_blind_spot"]["slip_each_days"] == 11
    assert data["joint_blind_spot"]["single_delay_a_days"] == 0
    assert data["joint_blind_spot"]["single_delay_b_days"] == 0
    assert data["joint_blind_spot"]["joint_delay_days"] == 11


def test_the_slip_size_is_five_days(program):
    assert analyze(program, Policy()).policy.slip_days == 5
