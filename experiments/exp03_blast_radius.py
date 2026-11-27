"""Experiment 3: where does the non-obvious task sit in the blast-radius ranking?

Question the README asks: rank every task by the delay a one-week (five-day)
slip there would cause. The critical tasks lead, each at the full five days. What
is the highest-ranked task that a Gantt review calls non-critical, and how far
down is it?
"""

from __future__ import annotations

from _common import load_program, write_result

from cpr.config import Policy
from cpr.cpm import compute_cpm
from cpr.sensitivity import sensitivity_ranking, top_hidden_task


def run() -> dict:
    program = load_program()
    cpm = compute_cpm(program)
    policy = Policy()
    ranking = sensitivity_ranking(program, cpm, policy.slip_days)
    hidden = top_hidden_task(ranking)
    assert hidden is not None

    order = [r.id for r in ranking]
    return {
        "slip_days": policy.slip_days,
        "hidden_task": hidden.id,
        "hidden_task_float_days": hidden.total_float,
        "hidden_task_delay_days": hidden.blast_radius,
        "hidden_task_rank": order.index(hidden.id) + 1,
        "critical_task_count": sum(1 for r in ranking if r.is_critical),
        "table": [
            {
                "task": r.id,
                "delay_days": r.blast_radius,
                "float_days": r.total_float,
                "critical": r.is_critical,
            }
            for r in ranking
        ],
    }


def main() -> None:
    result = run()
    write_result("exp03_blast_radius", result)
    print("Experiment 3: the blast-radius ranking")
    print(f"  slip                 {result['slip_days']} days")
    print(f"  non-obvious task     {result['hidden_task']} (rank {result['hidden_task_rank']})")
    print(f"  its float            {result['hidden_task_float_days']} days (a review calls it safe)")
    print(f"  its delay            {result['hidden_task_delay_days']} days")


if __name__ == "__main__":
    main()
