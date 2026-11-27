"""Experiment 5: is the deception a property of the fixture or of schedules?

Question the README asks: the fixture was built to overstate one chain's buffer,
so on its own it proves nothing general. Generate a thousand random multi-
workstream programs nobody tuned and report how often the float column overstates
some chain's buffer by at least the default 2x, and how often a slack task sits
within the default seven-day re-routing alarm. If those fractions are high, the
trap is structural.
"""

from __future__ import annotations

from statistics import median

from _common import write_result

from cpr.chains import enumerate_slack_chains
from cpr.config import Policy
from cpr.cpm import compute_cpm
from cpr.generator import generate_program
from cpr.sensitivity import nearest_rerouting, sensitivity_ranking

N_PROGRAMS = 1000


def run() -> dict:
    policy = Policy()
    overstated = 0
    reroute_in_window = 0
    worst_ratios: list[float] = []
    analyzed = 0

    for seed in range(N_PROGRAMS):
        program = generate_program(seed=seed)
        cpm = compute_cpm(program)
        report = enumerate_slack_chains(program, cpm)
        worst = report.worst(min_length=2)
        if worst is None:
            # No multi-task slack chain in this program; it cannot overstate.
            continue
        analyzed += 1
        worst_ratios.append(worst.overstatement_ratio)
        if worst.overstatement_ratio >= policy.max_float_overstatement_ratio:
            overstated += 1

        ranking = sensitivity_ranking(program, cpm, policy.slip_days)
        nearest = nearest_rerouting(ranking)
        if nearest is not None and nearest.rerouting_threshold <= policy.rerouting_alarm_days:
            reroute_in_window += 1

    return {
        "programs_generated": N_PROGRAMS,
        "programs_with_a_slack_chain": analyzed,
        "overstatement_threshold": policy.max_float_overstatement_ratio,
        "programs_overstated": overstated,
        "overstated_pct": round(100 * overstated / analyzed, 1),
        "median_worst_ratio": round(median(worst_ratios), 2),
        "max_worst_ratio": round(max(worst_ratios), 2),
        "rerouting_alarm_days": policy.rerouting_alarm_days,
        "programs_with_reroute_in_window": reroute_in_window,
        "reroute_in_window_pct": round(100 * reroute_in_window / analyzed, 1),
    }


def main() -> None:
    result = run()
    write_result("exp05_robustness", result)
    print("Experiment 5: robustness across random programs")
    print(f"  programs             {result['programs_generated']} ({result['programs_with_a_slack_chain']} had a slack chain)")
    print(f"  overstated >= {result['overstatement_threshold']}x    {result['programs_overstated']} ({result['overstated_pct']}%)")
    print(f"  median worst ratio   {result['median_worst_ratio']}x")
    print(f"  re-route in {result['rerouting_alarm_days']}d window {result['programs_with_reroute_in_window']} ({result['reroute_in_window_pct']}%)")


if __name__ == "__main__":
    main()
