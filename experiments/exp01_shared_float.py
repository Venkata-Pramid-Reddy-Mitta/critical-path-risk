"""Experiment 1: does the float column overstate the data chain's buffer?

Question the README asks: if you sum the total-float column across the data
chain, how much buffer does it claim, and how much is really there when a delay
enters at the head? The shared buffer is cross-checked against the propagation
engine so the number is not just the float identity restated.
"""

from __future__ import annotations

from _common import load_program, write_result

from cpr.chains import enumerate_slack_chains
from cpr.cpm import compute_cpm
from cpr.sensitivity import measure_shared_buffer


def run() -> dict:
    program = load_program()
    cpm = compute_cpm(program)
    worst = enumerate_slack_chains(program, cpm).worst(min_length=2)
    assert worst is not None

    verified = measure_shared_buffer(
        program, worst.tasks[0], worst.shared_buffer, cpm.project_duration, cpm.order
    )
    return {
        "chain": list(worst.tasks),
        "apparent_buffer_days": worst.apparent_buffer,
        "shared_buffer_days": worst.shared_buffer,
        "shared_buffer_verified_by_propagation": verified,
        "overstatement_ratio": round(worst.overstatement_ratio, 3),
    }


def main() -> None:
    result = run()
    write_result("exp01_shared_float", result)
    print("Experiment 1: shared-float deception")
    print(f"  chain                {' -> '.join(result['chain'])}")
    print(f"  apparent buffer      {result['apparent_buffer_days']} days (sum of the float column)")
    print(f"  shared buffer        {result['shared_buffer_days']} days (verified by propagation)")
    print(f"  overstatement        {result['overstatement_ratio']}x")


if __name__ == "__main__":
    main()
