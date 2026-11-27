#!/usr/bin/env python
"""Re-measure every published figure and write docs/metrics.json.

Nothing in this file is typed by hand: the test count and coverage are read from
the machine-readable pytest and coverage reports, and every headline number is
produced by importing the experiment modules and running them. The companion
``check_numbers.py`` then fails the build if any checked document quotes a figure
this file did not produce.

Run the suite as its own CI step (with --junitxml and --cov-report=json) and call
this with --skip-tests so a red test surfaces as a test failure, not as a
traceback from inside a metrics script. Locally, with no reports present, it runs
pytest itself.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "experiments"))

JUNIT = REPO_ROOT / "reports" / "junit.xml"
COVERAGE_JSON = REPO_ROOT / "coverage.json"
METRICS_OUT = REPO_ROOT / "docs" / "metrics.json"


def _run_pytest() -> None:
    subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q",
            "--cov=cpr", "--cov-branch",
            "--cov-report=json:coverage.json",
            "--junitxml=reports/junit.xml",
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def _test_count() -> int:
    tree = ET.parse(JUNIT)
    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    total = int(suite.get("tests"))
    failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    if failed:
        raise SystemExit(f"collect_metrics: {failed} test(s) failing; fix before measuring")
    return total


def _coverage() -> tuple[float, float]:
    data = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    totals = data["totals"]
    line = round(totals["percent_covered"], 1)
    covered = totals.get("covered_branches", 0)
    missing = totals.get("missing_branches", 0)
    branch = round(100.0 * covered / (covered + missing), 1) if (covered + missing) else 100.0
    return line, branch


def collect(skip_tests: bool) -> dict:
    if not skip_tests:
        _run_pytest()
    if not JUNIT.exists() or not COVERAGE_JSON.exists():
        raise SystemExit("collect_metrics: run the suite first (reports missing)")

    tests_total = _test_count()
    coverage_line, coverage_branch = _coverage()

    import exp01_shared_float
    import exp02_rerouting
    import exp03_blast_radius
    import exp04_joint_boundary
    import exp05_robustness

    from cpr.cpm import compute_cpm
    from cpr.model import Schedule

    program = Schedule.from_json(REPO_ROOT / "fixtures" / "program.json")
    cpm = compute_cpm(program)

    e1 = exp01_shared_float.run()
    e2 = exp02_rerouting.run()
    e3 = exp03_blast_radius.run()
    e4 = exp04_joint_boundary.run()
    e5 = exp05_robustness.run()

    metrics = {
        "tests_total": tests_total,
        "coverage_line_pct": coverage_line,
        "coverage_branch_pct": coverage_branch,
        "task_count": len(program),
        "slip_days": e3["slip_days"],
        "project_finish_days": cpm.project_duration,
        "critical_path_length": len(cpm.critical_path),
        "worst_chain_apparent_days": e1["apparent_buffer_days"],
        "worst_chain_shared_days": e1["shared_buffer_days"],
        "overstatement_ratio": round(e1["overstatement_ratio"], 1),
        "hidden_task_float_days": e3["hidden_task_float_days"],
        "hidden_task_delay_days": e3["hidden_task_delay_days"],
        "hidden_task_rank": e3["hidden_task_rank"],
        "rerouting_days": e2["nearest_rerouting_days"],
        "joint_delay_days": e4["joint_delay_days"],
        "joint_slip_each_days": e4["slip_each_days"],
        "robustness_programs": e5["programs_generated"],
        "robustness_overstated_pct": e5["overstated_pct"],
        "robustness_median_ratio": e5["median_worst_ratio"],
        "robustness_reroute_pct": e5["reroute_in_window_pct"],
    }

    anchors = {
        "tests_total": ["{} tests"],
        "coverage_line_pct": ["{}% line", "{}% coverage"],
        "coverage_branch_pct": ["{}% branch"],
        "task_count": ["{}-task", "{} tasks"],
        "slip_days": ["{}-day slip"],
        "project_finish_days": ["{} working days", "{}-day program"],
        "critical_path_length": ["{}-task critical", "critical path of {}"],
        "worst_chain_apparent_days": ["sums to {}", "{} task-days"],
        "worst_chain_shared_days": ["shared buffer of {}", "shared buffer is {}"],
        "overstatement_ratio": ["{}x"],
        "hidden_task_float_days": ["{} days of float", "{}-day float"],
        "hidden_task_delay_days": ["go-live {} days", "by {} days"],
        "hidden_task_rank": ["rank {}", "ranks {}"],
        "rerouting_days": ["{}-day slip"],
        "joint_delay_days": ["go-live {} days"],
        "joint_slip_each_days": ["slip of {} days", "{} days each"],
        "robustness_programs": ["{} random programs", "{} generated programs"],
        "robustness_overstated_pct": ["in {}% of", "{}% of"],
        "robustness_median_ratio": ["median {}x"],
        "robustness_reroute_pct": ["{}% of"],
    }

    return {
        "metrics": metrics,
        "anchors": anchors,
        "checked_documents": [
            "README.md",
        ],
        "note": "every value is produced by running the suite and the five experiments",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true", help="read existing reports")
    args = parser.parse_args()
    payload = collect(skip_tests=args.skip_tests)
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {METRICS_OUT.relative_to(REPO_ROOT)} with {len(payload['metrics'])} metrics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
