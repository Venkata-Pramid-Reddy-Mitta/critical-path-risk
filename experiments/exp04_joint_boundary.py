"""Experiment 4: the pair the single-slip ranking cannot see.

Question the README asks: the ranking stresses one task at a time. What is the
largest project delay produced by a pair that single-slip analysis rates as zero
for each task alone? This measures the tool's own boundary.
"""

from __future__ import annotations

from _common import load_program, write_result

from cpr.cpm import compute_cpm
from cpr.joint import find_worst_joint_blind_spot


def run() -> dict:
    program = load_program()
    cpm = compute_cpm(program)
    spot = find_worst_joint_blind_spot(program, cpm)
    assert spot is not None
    return {
        "pair": [spot.task_a, spot.task_b],
        "slip_each_days": spot.slip_each,
        "single_delay_a_days": spot.single_delay_a,
        "single_delay_b_days": spot.single_delay_b,
        "joint_delay_days": spot.joint_delay,
    }


def main() -> None:
    result = run()
    write_result("exp04_joint_boundary", result)
    a, b = result["pair"]
    print("Experiment 4: the single-slip blind spot")
    print(f"  pair                 {a} and {b}")
    print(f"  slip each            {result['slip_each_days']} days")
    print(f"  delay alone          {result['single_delay_a_days']} and {result['single_delay_b_days']} days")
    print(f"  delay together       {result['joint_delay_days']} days")


if __name__ == "__main__":
    main()
