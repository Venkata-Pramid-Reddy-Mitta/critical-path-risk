"""Why this file exists.

This is the propagation that the float column cannot do for you. To learn a
task's true blast radius you inflate its duration by the slip, re-run the
forward pass, and measure how far the project finish moved. Doing that for every
task turns a static schedule into a ranking of which single slip hurts most, and
it surfaces two things a Gantt review misses:

- the non-obvious task: one with positive float (so a review deprioritizes it)
  whose slip still moves the finish, because its float is smaller than the slip;
- the re-routing threshold: the slip at which a slack task becomes critical and
  the critical path quietly moves onto a chain nobody was watching.

Changing a duration never changes the graph shape, so the topological order is
computed once and reused across the thousands of re-runs the ranking performs.
Every published number here is produced by propagation and, for the threshold,
cross-checked against the float identity it should satisfy.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cpm import CpmResult, project_finish
from .model import Schedule


def blast_radius(
    schedule: Schedule,
    task_id: str,
    slip_days: int,
    baseline: int,
    order: tuple[str, ...],
) -> int:
    """Working days the project finish moves if ``task_id`` slips by ``slip_days``.

    The topology is unchanged by a duration bump, so ``order`` and ``baseline``
    are passed in and reused rather than recomputed per call.
    """
    if slip_days < 0:
        raise ValueError("slip_days cannot be negative")
    if slip_days == 0:
        return 0
    task = schedule[task_id]
    slipped = schedule.with_duration(task_id, task.duration + slip_days)
    return project_finish(slipped, order) - baseline


def measure_shared_buffer(
    schedule: Schedule,
    task_id: str,
    total_float: int,
    baseline: int,
    order: tuple[str, ...],
) -> int:
    """The chain buffer entered at ``task_id``, confirmed by propagation.

    The float identity says a task can slip by exactly its total float before the
    project moves, so this both returns that number and verifies it: a slip of
    ``total_float`` must leave the finish put, and one more must move it. If the
    engine disagreed with the identity, that would be a real bug and this raises
    rather than publishing a number the propagation does not support.
    """
    if total_float < 0:
        raise ValueError("total_float cannot be negative")
    if blast_radius(schedule, task_id, total_float, baseline, order) != 0:
        raise AssertionError(
            f"{task_id}: a slip equal to its total float ({total_float}) moved the "
            "finish, which contradicts the critical path method"
        )
    if blast_radius(schedule, task_id, total_float + 1, baseline, order) <= 0:
        raise AssertionError(
            f"{task_id}: a slip of total float + 1 ({total_float + 1}) did not move "
            "the finish, which contradicts the critical path method"
        )
    return total_float


def rerouting_threshold(
    schedule: Schedule,
    cpm: CpmResult,
    task_id: str,
) -> int:
    """Smallest slip, in days, that makes ``task_id`` move the project finish.

    For a slack task this is the point where the critical path re-routes through
    it (total float + 1). For a task already on the critical path it is 1, since
    any slip moves the finish.
    """
    f = cpm.total_float[task_id]
    threshold = f + 1
    moved = blast_radius(schedule, task_id, threshold, cpm.project_duration, cpm.order)
    if moved <= 0:  # pragma: no cover - a guard against a future CPM regression
        raise AssertionError(
            f"{task_id}: expected re-routing at slip {threshold}, finish did not move"
        )
    return threshold


@dataclass(frozen=True)
class TaskSensitivity:
    """One task's row in the blast-radius ranking."""

    id: str
    name: str
    workstream: str
    total_float: int
    free_float: int
    is_critical: bool
    blast_radius: int
    rerouting_threshold: int


def sensitivity_ranking(
    schedule: Schedule,
    cpm: CpmResult,
    slip_days: int,
) -> tuple[TaskSensitivity, ...]:
    """Every task scored by the project delay a ``slip_days`` slip would cause.

    Sorted by blast radius descending, then by ascending total float (the tasks a
    review would have called tightest), then by schedule order, so the ranking is
    identical on every run.
    """
    rows: list[TaskSensitivity] = []
    for tid in cpm.order:
        task = schedule[tid]
        rows.append(
            TaskSensitivity(
                id=tid,
                name=task.name,
                workstream=task.workstream,
                total_float=cpm.total_float[tid],
                free_float=cpm.free_float[tid],
                is_critical=cpm.is_critical(tid),
                blast_radius=blast_radius(
                    schedule, tid, slip_days, cpm.project_duration, cpm.order
                ),
                rerouting_threshold=rerouting_threshold(schedule, cpm, tid),
            )
        )
    rows.sort(key=lambda r: (-r.blast_radius, r.total_float, cpm.order.index(r.id)))
    return tuple(rows)


def top_hidden_task(ranking: tuple[TaskSensitivity, ...]) -> TaskSensitivity | None:
    """The highest-blast-radius task that is not on the critical path.

    This is the headline "non-obvious" task: positive float, so a Gantt review
    treats it as safe, yet the propagation says a slip there moves the finish.
    """
    hidden = [r for r in ranking if not r.is_critical and r.blast_radius > 0]
    if not hidden:
        return None
    return hidden[0]


def nearest_rerouting(
    ranking: tuple[TaskSensitivity, ...],
) -> TaskSensitivity | None:
    """The non-critical task closest to becoming critical (smallest threshold).

    Ties break toward the longer-float task, then schedule order, so the result
    is stable; this is the earliest blind spot a review would miss.
    """
    slack = [r for r in ranking if not r.is_critical]
    if not slack:
        return None
    return min(slack, key=lambda r: (r.rerouting_threshold, -r.total_float))
