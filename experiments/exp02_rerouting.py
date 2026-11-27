"""Experiment 2: how close is the nearest slack task to becoming critical?

Question the README asks: a review deprioritizes every task with positive float.
What is the smallest slip that would re-route the critical path onto one of them,
and which task is it? That slip is the width of the blind spot.
"""

from __future__ import annotations

from _common import load_program, write_result

from cpr.config import Policy
from cpr.cpm import compute_cpm
from cpr.sensitivity import nearest_rerouting, sensitivity_ranking


def run() -> dict:
    program = load_program()
    cpm = compute_cpm(program)
    policy = Policy()
    ranking = sensitivity_ranking(program, cpm, policy.slip_days)
    nearest = nearest_rerouting(ranking)
    assert nearest is not None

    thresholds = {
        r.id: r.rerouting_threshold for r in ranking if not r.is_critical
    }
    return {
        "nearest_task": nearest.id,
        "nearest_task_float_days": nearest.total_float,
        "nearest_rerouting_days": nearest.rerouting_threshold,
        "review_blind_spot_days": policy.review_blind_spot_days,
        "within_blind_spot": nearest.rerouting_threshold <= policy.review_blind_spot_days,
        "all_slack_thresholds": thresholds,
    }


def main() -> None:
    result = run()
    write_result("exp02_rerouting", result)
    print("Experiment 2: the nearest re-routing")
    print(f"  nearest slack task   {result['nearest_task']} ({result['nearest_task_float_days']} days float)")
    print(f"  re-routes at a slip  {result['nearest_rerouting_days']} days")
    print(f"  review blind spot    {result['review_blind_spot_days']} days")
    print(f"  inside blind spot    {result['within_blind_spot']}")


if __name__ == "__main__":
    main()
