"""The orchestration and the policy gate."""

from __future__ import annotations

from dataclasses import replace

from cpr.analysis import Gate, analyze
from cpr.config import Policy


def test_the_program_is_flagged_under_the_default_policy(program):
    result = analyze(program, Policy())
    assert result.gate is Gate.FLAGGED


def test_both_gate_reasons_fire_on_the_program(program):
    result = analyze(program, Policy())
    assert len(result.gate_reasons) == 2
    joined = " ".join(result.gate_reasons)
    assert "overstates" in joined
    assert "re-routes" in joined


def test_a_lenient_policy_clears_the_program(program):
    # Raise the overstatement ceiling above 5.1 and shrink the alarm window
    # below AM1's 4-day re-route, so nothing trips.
    lenient = Policy(max_float_overstatement_ratio=9.0, rerouting_alarm_days=1)
    result = analyze(program, lenient)
    assert result.gate is Gate.CLEAN
    assert result.gate_reasons == ()


def test_only_the_overstatement_reason_fires_when_the_alarm_is_tight(program):
    policy = Policy(rerouting_alarm_days=1)
    result = analyze(program, policy)
    assert result.gate is Gate.FLAGGED
    assert any("overstates" in r for r in result.gate_reasons)
    assert not any("re-routes" in r for r in result.gate_reasons)


def test_only_the_rerouting_reason_fires_when_the_ratio_is_lenient(program):
    policy = Policy(max_float_overstatement_ratio=9.0)
    result = analyze(program, policy)
    assert result.gate is Gate.FLAGGED
    assert any("re-routes" in r for r in result.gate_reasons)
    assert not any("overstates" in r for r in result.gate_reasons)


def test_the_slip_size_flows_into_the_ranking(program):
    five = analyze(program, Policy(slip_days=5))
    twelve = analyze(program, replace(Policy(), slip_days=12))
    am1_five = next(r for r in five.ranking if r.id == "AM1").blast_radius
    am1_twelve = next(r for r in twelve.ranking if r.id == "AM1").blast_radius
    assert am1_five == 2
    assert am1_twelve == 9  # 12 - 3 days float


def test_the_result_bundle_carries_every_section(program):
    result = analyze(program, Policy())
    assert result.worst_chain is not None
    assert result.hidden_task is not None
    assert result.nearest_reroute is not None
    assert result.joint_blind_spot is not None
    assert len(result.ranking) == len(program)
