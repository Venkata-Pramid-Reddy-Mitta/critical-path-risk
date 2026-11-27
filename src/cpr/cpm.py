"""Why this file exists.

This is the author-built core: the Critical Path Method, implemented in plain
Python rather than pulled from a graph library, because the longest-path
computation is the exact thing this repository claims to demonstrate. ADR-001
records the decision not to use NetworkX and the line it draws between "I called
a function" and "I wrote the algorithm".

The passes are the standard CPM:

- a Kahn topological sort, which detects a cycle as a by-product (if any node
  never reaches in-degree zero, the graph is not a DAG and no schedule exists);
- a forward pass for earliest start and finish (the longest path from a start);
- a backward pass for latest start and finish (the longest path to the end);
- total float (slack before the project slips) and free float (slack before any
  successor's earliest start slips), which are different numbers and are the
  source of the deception this whole tool exists to expose.

``project_finish`` is split out and kept allocation-light because the slip
sensitivity calls it once per task per slip, so it runs on the order of
thousands of times on a real program.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .model import Schedule, ScheduleError


class CycleError(ScheduleError):
    """Raised when the dependency graph contains a cycle, so it is not a DAG."""

    def __init__(self, remaining: tuple[str, ...]) -> None:
        self.remaining = remaining
        super().__init__(
            "dependency graph has a cycle; no valid schedule exists. "
            f"tasks caught in the cycle: {list(remaining)}"
        )


def topological_order(schedule: Schedule) -> tuple[str, ...]:
    """Kahn's algorithm. Returns ids in an order where every dep precedes its task.

    Ties (several tasks ready at once) break by the schedule's insertion order,
    not by a set's iteration order, so the sort is identical on every run. That
    determinism is what later lets the rankings be published as fixed numbers.
    """
    indegree: dict[str, int] = dict.fromkeys(schedule.ids, 0)
    for task in schedule:
        for _dep in task.deps:
            indegree[task.id] += 1

    # Seed the queue in insertion order to keep ties deterministic.
    ready: deque[str] = deque(tid for tid in schedule.ids if indegree[tid] == 0)
    successors = {tid: schedule.successors(tid) for tid in schedule.ids}

    order: list[str] = []
    while ready:
        tid = ready.popleft()
        order.append(tid)
        for succ in successors[tid]:
            indegree[succ] -= 1
            if indegree[succ] == 0:
                ready.append(succ)

    if len(order) != len(schedule):
        remaining = tuple(tid for tid in schedule.ids if tid not in set(order))
        raise CycleError(remaining)
    return tuple(order)


def _forward_pass(schedule: Schedule, order: tuple[str, ...]) -> tuple[dict, dict]:
    es: dict[str, int] = {}
    ef: dict[str, int] = {}
    for tid in order:
        task = schedule[tid]
        es[tid] = max((ef[d] for d in task.deps), default=0)
        ef[tid] = es[tid] + task.duration
    return es, ef


def project_finish(schedule: Schedule, order: tuple[str, ...] | None = None) -> int:
    """The program's earliest finish in working days: a single forward pass.

    Kept separate and cheap because the slip sensitivity perturbs one duration
    and calls this again, once per task per slip size.
    """
    if order is None:
        order = topological_order(schedule)
    _es, ef = _forward_pass(schedule, order)
    return max(ef.values(), default=0)


@dataclass(frozen=True)
class CpmResult:
    """The full schedule analysis: times, floats, and the critical path."""

    order: tuple[str, ...]
    es: dict[str, int]
    ef: dict[str, int]
    ls: dict[str, int]
    lf: dict[str, int]
    total_float: dict[str, int]
    free_float: dict[str, int]
    project_duration: int
    critical: tuple[str, ...]
    critical_path: tuple[str, ...]

    def is_critical(self, task_id: str) -> bool:
        return self.total_float[task_id] == 0


def compute_cpm(schedule: Schedule) -> CpmResult:
    """Run both passes and derive floats and the critical path."""
    order = topological_order(schedule)
    es, ef = _forward_pass(schedule, order)
    project_duration = max(ef.values(), default=0)

    successors = {tid: schedule.successors(tid) for tid in schedule.ids}
    ls: dict[str, int] = {}
    lf: dict[str, int] = {}
    for tid in reversed(order):
        task = schedule[tid]
        succ = successors[tid]
        lf[tid] = min((ls[s] for s in succ), default=project_duration)
        ls[tid] = lf[tid] - task.duration

    total_float = {tid: ls[tid] - es[tid] for tid in order}

    free_float: dict[str, int] = {}
    for tid in order:
        succ = successors[tid]
        earliest_succ_start = min((es[s] for s in succ), default=project_duration)
        free_float[tid] = earliest_succ_start - ef[tid]

    critical = tuple(tid for tid in order if total_float[tid] == 0)
    critical_path = _trace_critical_path(schedule, order, es, total_float)

    return CpmResult(
        order=order,
        es=es,
        ef=ef,
        ls=ls,
        lf=lf,
        total_float=total_float,
        free_float=free_float,
        project_duration=project_duration,
        critical=critical,
        critical_path=critical_path,
    )


def _trace_critical_path(
    schedule: Schedule,
    order: tuple[str, ...],
    es: dict[str, int],
    total_float: dict[str, int],
) -> tuple[str, ...]:
    """One representative critical path: the chain of zero-float tasks from a
    start node to the finish, following the latest-finishing critical successor.

    A program can have several critical paths; this returns one of them
    deterministically so the report has a concrete chain to name. Membership of
    the critical set is the complete answer; the traced path is for display.
    """
    critical = {tid for tid in order if total_float[tid] == 0}
    if not critical:  # pragma: no cover - any non-empty DAG has a longest path
        return ()

    # Start node: a critical task whose predecessors are all non-critical (or it
    # has none). Earliest ES, then insertion order, for determinism.
    starts = [
        tid
        for tid in order
        if tid in critical and not any(d in critical for d in schedule[tid].deps)
    ]
    start = min(starts, key=lambda t: (es[t], order.index(t)))

    path = [start]
    current = start
    while True:
        succ = [s for s in schedule.successors(current) if s in critical]
        if not succ:
            break
        # Follow the critical successor that finishes the program, resolving ties
        # by insertion order.
        current = min(succ, key=lambda t: (-es[t], order.index(t)))
        path.append(current)
    return tuple(path)
