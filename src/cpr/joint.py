"""Why this file exists.

The sensitivity ranking stresses one task at a time. That is the right default
(it is linear in the number of tasks and it answers the question a program
manager actually asks first), but it has a blind spot of its own, and honesty
about that blind spot is the point of this module.

Two tasks that share a chain's float can each absorb a slip equal to that float
with zero project impact, measured alone. Slip both and the shared buffer is
spent twice: the finish moves by as much as the pair overran it. Single-slip
analysis reports 0 and 0 for exactly the pair that, together, does the damage.

This module measures that gap so the README can publish it as the tool's
boundary rather than hide it. It does not ship a full pairwise search in the
default path: that is O(n squared) slips and is the Pivot, triggered only when a
team adopts the single-slip ranking and starts asking about simultaneous slips.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .cpm import CpmResult, project_finish
from .model import Schedule
from .sensitivity import blast_radius


def joint_slip_delay(
    schedule: Schedule,
    slips: Iterable[tuple[str, int]],
    baseline: int,
    order: tuple[str, ...],
) -> int:
    """Project delay when several tasks slip at once.

    ``slips`` is pairs of (task id, slip days). All are applied, then one forward
    pass measures the combined move. Applying them together is not the sum of
    their separate moves, which is the entire reason this function exists.
    """
    modified = schedule
    for task_id, slip in slips:
        if slip < 0:
            raise ValueError("slip days cannot be negative")
        modified = modified.with_duration(task_id, modified[task_id].duration + slip)
    return project_finish(modified, order) - baseline


@dataclass(frozen=True)
class JointBlindSpot:
    """A pair each rated zero alone but non-zero together, with the numbers."""

    task_a: str
    task_b: str
    slip_each: int
    single_delay_a: int
    single_delay_b: int
    joint_delay: int


def find_worst_joint_blind_spot(
    schedule: Schedule,
    cpm: CpmResult,
) -> JointBlindSpot | None:
    """Search non-critical pairs for the largest single-vs-joint gap.

    For each pair of slack tasks, stress each at the smaller of their two total
    floats (so both are individually safe by construction) and measure the joint
    delay. Returns the pair with the largest joint delay, which is the sharpest
    statement of what the single-slip ranking cannot see. O(n squared), used in
    the boundary experiment and the tests, never on the default report path.
    """
    base = cpm.project_duration
    order = cpm.order
    slack = [tid for tid in cpm.order if cpm.total_float[tid] > 0]

    worst: JointBlindSpot | None = None
    for i, a in enumerate(slack):
        for b in slack[i + 1 :]:
            # Stress each at the smaller of the two floats, so both are safe
            # alone by construction: a slip no larger than a task's float is
            # always absorbed. slack is filtered to positive float, so this is
            # at least 1.
            slip = min(cpm.total_float[a], cpm.total_float[b])
            single_a = blast_radius(schedule, a, slip, base, order)
            single_b = blast_radius(schedule, b, slip, base, order)
            if single_a != 0 or single_b != 0:  # pragma: no cover - invariant guard
                # Unreachable under the min-float slip above, but kept so the
                # "safe alone" guarantee survives a future change to the slip
                # choice. A pair that is already risky alone is not a blind spot.
                continue
            joint = joint_slip_delay(schedule, [(a, slip), (b, slip)], base, order)
            if joint <= 0:
                continue
            candidate = JointBlindSpot(
                task_a=a,
                task_b=b,
                slip_each=slip,
                single_delay_a=single_a,
                single_delay_b=single_b,
                joint_delay=joint,
            )
            key = (joint, slip, order.index(a), order.index(b))
            if worst is None or key > (
                worst.joint_delay,
                worst.slip_each,
                order.index(worst.task_a),
                order.index(worst.task_b),
            ):
                worst = candidate
    return worst
