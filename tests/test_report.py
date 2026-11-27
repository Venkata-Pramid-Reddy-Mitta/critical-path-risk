"""The report renderers, including the CSS-class-coverage guard."""

from __future__ import annotations

import re

from cpr.analysis import analyze
from cpr.config import Policy
from cpr.report import render_console, render_html, render_json


def test_the_console_report_states_the_finish_and_critical_path(program):
    text = render_console(analyze(program, Policy()))
    assert "project finish: 75 working days" in text
    assert "CM1 -> CM2 -> AM2" in text


def test_the_console_report_shows_the_flagged_verdict(program):
    text = render_console(analyze(program, Policy()))
    assert "RISK FLAGGED" in text


def test_the_console_report_names_the_hidden_task(program):
    text = render_console(analyze(program, Policy()))
    assert "AM1" in text
    assert "off the critical path" in text


def test_the_console_report_states_the_joint_boundary(program):
    text = render_console(analyze(program, Policy()))
    assert "slipped together" in text
    assert "11 days" in text


def test_the_html_report_is_a_full_document(program):
    html = render_html(analyze(program, Policy()))
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_the_html_verdict_badge_carries_the_flagged_class(program):
    html = render_html(analyze(program, Policy()))
    assert "verdict flagged" in html


def test_a_clean_program_renders_the_clean_badge(program):
    lenient = Policy(max_float_overstatement_ratio=9.0, rerouting_alarm_days=1)
    html = render_html(analyze(program, lenient))
    assert "verdict clean" in html


def test_every_css_class_used_in_the_html_has_a_rule(program):
    # This mirrors the guard the screenshot tool runs against pixels: a class in
    # the markup with no rule is the collision that once hid a verdict badge.
    html = render_html(analyze(program, Policy()))
    used: set[str] = set()
    for group in re.findall(r"class='([^']+)'", html):
        used.update(group.split())
    css = html.split("<style>")[1].split("</style>")[0]
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
    assert used <= defined, f"classes without a rule: {used - defined}"


def test_the_json_summary_carries_the_headline_numbers(program):
    data = render_json(analyze(program, Policy()))
    assert data["project_finish_days"] == 75
    assert data["worst_chain"]["apparent_buffer_days"] == 56
    assert data["worst_chain"]["shared_buffer_days"] == 11
    assert data["hidden_task"]["id"] == "AM1"
    assert data["joint_blind_spot"]["joint_delay_days"] == 11


def test_the_json_summary_reports_the_gate(program):
    data = render_json(analyze(program, Policy()))
    assert data["gate"] == "flagged"
    assert len(data["gate_reasons"]) == 2
