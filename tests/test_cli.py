"""The command line contract: exit codes that a build can act on."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cpr.cli import EXIT_FAILED, EXIT_OK, EXIT_RISK, main

FIXTURE = str(Path(__file__).resolve().parents[1] / "fixtures" / "program.json")


def test_analyze_without_gate_exits_zero_even_when_flagged(capsys):
    assert main(["analyze", FIXTURE]) == EXIT_OK
    out = capsys.readouterr().out
    assert "RISK FLAGGED" in out


def test_analyze_with_gate_exits_two_on_a_flagged_program(capsys):
    assert main(["analyze", FIXTURE, "--gate", "--quiet"]) == EXIT_RISK


def test_analyze_with_gate_exits_zero_under_a_lenient_policy(tmp_path):
    policy = tmp_path / "lenient.toml"
    policy.write_text(
        "[gate]\nmax_float_overstatement_ratio = 9.0\nrerouting_alarm_days = 1\n",
        encoding="utf-8",
    )
    code = main(["analyze", FIXTURE, "--gate", "--quiet", "--policy", str(policy)])
    assert code == EXIT_OK


def test_a_missing_program_file_exits_one(capsys):
    assert main(["analyze", "/no/such.json"]) == EXIT_FAILED
    assert "error" in capsys.readouterr().err


def test_a_zero_slip_override_exits_one(capsys):
    assert main(["analyze", FIXTURE, "--slip", "0", "--quiet"]) == EXIT_FAILED
    assert "slip_days" in capsys.readouterr().err


def test_a_cycle_program_exits_one(tmp_path, capsys):
    prog = tmp_path / "cycle.json"
    prog.write_text(
        json.dumps(
            {
                "tasks": [
                    {"id": "A", "name": "a", "workstream": "w", "duration": 1, "deps": ["B"]},
                    {"id": "B", "name": "b", "workstream": "w", "duration": 1, "deps": ["A"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert main(["analyze", str(prog)]) == EXIT_FAILED
    assert "cycle" in capsys.readouterr().err


def test_html_output_is_written(tmp_path):
    out = tmp_path / "r.html"
    main(["analyze", FIXTURE, "--quiet", "--html", str(out)])
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_json_output_is_written_and_valid(tmp_path):
    out = tmp_path / "r.json"
    main(["analyze", FIXTURE, "--quiet", "--json", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["project_finish_days"] == 75


def test_quiet_suppresses_the_console_report(capsys):
    main(["analyze", FIXTURE, "--quiet"])
    assert capsys.readouterr().out == ""


def test_a_bad_policy_file_exits_one(tmp_path, capsys):
    policy = tmp_path / "bad.toml"
    policy.write_text("[gate]\nmax_float_overstatement_ratio = 0.1\n", encoding="utf-8")
    assert main(["analyze", FIXTURE, "--quiet", "--policy", str(policy)]) == EXIT_FAILED


def test_no_subcommand_is_an_error():
    with pytest.raises(SystemExit):
        main([])
