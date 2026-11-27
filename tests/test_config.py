"""Policy loading and validation, and the check that code and TOML agree."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from cpr.config import DEFAULT_POLICY_PATH, Policy, PolicyError, load_policy

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_defaults_are_usable_with_no_file():
    p = Policy()
    assert p.slip_days == 5
    assert p.max_float_overstatement_ratio == 2.0


def test_slip_days_must_be_positive():
    with pytest.raises(PolicyError, match="slip_days"):
        Policy(slip_days=0)


def test_review_blind_spot_may_not_be_negative():
    with pytest.raises(PolicyError, match="review_blind_spot"):
        Policy(review_blind_spot_days=-1)


def test_overstatement_ratio_below_one_is_refused():
    with pytest.raises(PolicyError, match="overstatement"):
        Policy(max_float_overstatement_ratio=0.5)


def test_rerouting_alarm_may_not_be_negative():
    with pytest.raises(PolicyError, match="rerouting_alarm"):
        Policy(rerouting_alarm_days=-2)


def test_top_n_must_be_positive():
    with pytest.raises(PolicyError, match="top_n"):
        Policy(top_n=0)


def test_load_policy_with_no_path_reads_the_shipped_file():
    p = load_policy()
    assert isinstance(p, Policy)
    assert p.slip_days == 5


def test_an_explicit_missing_file_is_an_error():
    with pytest.raises(PolicyError, match="not found"):
        load_policy("/no/such/policy.toml")


def test_a_bad_toml_file_reports_a_parse_error(tmp_path):
    bad = tmp_path / "p.toml"
    bad.write_text("this is = = not toml", encoding="utf-8")
    with pytest.raises(PolicyError, match="could not parse"):
        load_policy(bad)


def test_an_unknown_key_is_refused(tmp_path):
    p = tmp_path / "p.toml"
    p.write_text("[gate]\nmystery = 3\n", encoding="utf-8")
    with pytest.raises(PolicyError, match="unknown policy keys"):
        load_policy(p)


def test_a_partial_override_keeps_other_defaults(tmp_path):
    p = tmp_path / "p.toml"
    p.write_text("[horizon]\nslip_days = 10\n", encoding="utf-8")
    policy = load_policy(p)
    assert policy.slip_days == 10
    assert policy.max_float_overstatement_ratio == 2.0


def test_a_flat_file_without_sections_also_loads(tmp_path):
    p = tmp_path / "p.toml"
    p.write_text("slip_days = 7\n", encoding="utf-8")
    assert load_policy(p).slip_days == 7


def test_the_shipped_policy_file_matches_the_dataclass_defaults():
    # If the TOML and the code drift, this fails rather than the two silently
    # disagreeing about what the default gate is.
    raw = tomllib.loads(DEFAULT_POLICY_PATH.read_text(encoding="utf-8"))
    flat: dict = {}
    for section in raw.values():
        flat.update(section)
    defaults = Policy()
    assert flat["slip_days"] == defaults.slip_days
    assert flat["review_blind_spot_days"] == defaults.review_blind_spot_days
    assert flat["max_float_overstatement_ratio"] == defaults.max_float_overstatement_ratio
    assert flat["rerouting_alarm_days"] == defaults.rerouting_alarm_days
    assert flat["top_n"] == defaults.top_n
