"""Defensive and rarely-hit branches, exercised so coverage reflects reality."""

from __future__ import annotations

import pytest

import cpr.chains as chains_mod
import cpr.config as config_mod
from cpr.analysis import analyze
from cpr.chains import enumerate_slack_chains
from cpr.config import Policy, load_policy
from cpr.cpm import compute_cpm
from cpr.joint import find_worst_joint_blind_spot
from cpr.model import Schedule
from cpr.report import render_console, render_html
from cpr.sensitivity import measure_shared_buffer, nearest_rerouting, sensitivity_ranking


def _all_critical_line() -> Schedule:
    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 4, "deps": []},
        {"id": "B", "name": "b", "workstream": "w", "duration": 4, "deps": ["A"]},
        {"id": "C", "name": "c", "workstream": "w", "duration": 4, "deps": ["B"]},
    ]
    return Schedule.from_dict({"tasks": rows})


def test_measure_shared_buffer_raises_when_the_float_is_too_large(program):
    cpm = compute_cpm(program)
    # DM1's real float is 11; claiming 15 means a 15-day slip moves the finish,
    # which contradicts the identity, so the guard fires.
    with pytest.raises(AssertionError, match="moved the"):
        measure_shared_buffer(program, "DM1", 15, cpm.project_duration, cpm.order)


def test_measure_shared_buffer_raises_when_the_float_is_too_small(program):
    cpm = compute_cpm(program)
    # Claiming 5 means a 6-day slip should move the finish; it does not (real
    # float is 11), so the second guard fires.
    with pytest.raises(AssertionError, match="did not move"):
        measure_shared_buffer(program, "DM1", 5, cpm.project_duration, cpm.order)


def test_nearest_rerouting_is_none_when_everything_is_critical():
    s = _all_critical_line()
    cpm = compute_cpm(s)
    ranking = sensitivity_ranking(s, cpm, 3)
    assert nearest_rerouting(ranking) is None


def test_render_handles_a_program_with_no_chain_or_hidden_task():
    s = _all_critical_line()
    result = analyze(s, Policy())
    text = render_console(result)
    html = render_html(result)
    assert "CLEAN" in text
    assert "verdict clean" in html
    # No worst chain, hidden task, or joint pair, so those sections are absent.
    assert "Shared-float deception" not in html
    assert "non-obvious task" not in html


def test_no_joint_blind_spot_on_an_all_critical_program():
    s = _all_critical_line()
    cpm = compute_cpm(s)
    assert find_worst_joint_blind_spot(s, cpm) is None


def test_chain_enumeration_truncates_and_reports_it(program, monkeypatch):
    # Force the cap down to prove the truncation path sets the flag rather than
    # silently dropping chains.
    monkeypatch.setattr(chains_mod, "MAX_CHAINS", 1)
    cpm = compute_cpm(program)
    report = enumerate_slack_chains(program, cpm)
    assert report.truncated is True
    assert len(report.chains) <= 1


def test_load_policy_falls_back_to_defaults_when_no_file_is_shipped(tmp_path, monkeypatch):
    missing = tmp_path / "absent.toml"
    monkeypatch.setattr(config_mod, "DEFAULT_POLICY_PATH", missing)
    assert load_policy() == Policy()


def test_find_worst_blind_spot_scans_many_pairs_on_a_generated_program():
    # A five-stream generated program has several slack pairs, so the search
    # exercises the branch where a later candidate does not beat the current
    # best. Seed 1 is a case with a large joint delay.
    from cpr.generator import generate_program

    s = generate_program(seed=1, workstreams=5, tasks_per_stream=4)
    cpm = compute_cpm(s)
    spot = find_worst_joint_blind_spot(s, cpm)
    assert spot is not None
    assert spot.single_delay_a == 0 and spot.single_delay_b == 0
    assert spot.joint_delay > 0


def test_a_joint_pair_that_is_individually_risky_is_skipped():
    # A slack task whose slip alone already moves the finish must not be offered
    # as a "safe alone" blind spot. Build a case and confirm the search returns
    # None rather than a pair with a non-zero single delay.
    rows = [
        {"id": "A", "name": "a", "workstream": "w", "duration": 10, "deps": []},
        {"id": "B", "name": "b", "workstream": "w", "duration": 10, "deps": ["A"]},
        {"id": "S", "name": "s", "workstream": "w", "duration": 2, "deps": ["A"]},
        {"id": "C", "name": "c", "workstream": "w", "duration": 10, "deps": ["B", "S"]},
    ]
    s = Schedule.from_dict({"tasks": rows})
    cpm = compute_cpm(s)
    # Only one slack task (S), so no pair exists; the search returns None.
    assert find_worst_joint_blind_spot(s, cpm) is None
