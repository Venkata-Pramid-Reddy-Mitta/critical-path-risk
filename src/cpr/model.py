"""Why this file exists.

Everything downstream (the CPM passes, the float chains, the slip sensitivity)
is only as trustworthy as the graph it runs on, so the schedule is parsed and
validated once, here, at the boundary. A malformed program (a dependency on a
task that does not exist, a duplicate id, a negative duration) is refused with a
specific message before any analysis runs, rather than producing a plausible but
wrong finish date. Cycle detection lives in ``cpm`` because it falls out of the
topological sort for free; everything else is checked here.

A Schedule is immutable once built. The sensitivity analysis needs to perturb
one duration and re-run the passes hundreds of times, so it builds a cheap
modified copy with ``with_duration`` rather than mutating shared state, which is
also what keeps the whole analysis deterministic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path


class ScheduleError(ValueError):
    """Raised when a program cannot be parsed into a valid dependency graph."""


@dataclass(frozen=True)
class Task:
    """One WBS task: an id, a human label, its workstream, duration and predecessors.

    Duration is in working days and must be a positive integer. Dependencies are
    finish-to-start only: a task cannot start until every id in ``deps`` has
    finished. That restriction is a deliberate boundary, recorded in ADR-002.
    """

    id: str
    name: str
    workstream: str
    duration: int
    deps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ScheduleError("task id must be a non-empty string")
        if not isinstance(self.duration, int) or isinstance(self.duration, bool):
            raise ScheduleError(f"task {self.id!r}: duration must be an integer day count")
        if self.duration <= 0:
            raise ScheduleError(
                f"task {self.id!r}: duration must be positive, got {self.duration}"
            )
        if self.id in self.deps:
            raise ScheduleError(f"task {self.id!r}: a task cannot depend on itself")


@dataclass(frozen=True)
class Schedule:
    """An immutable set of tasks keyed by id, insertion order preserved.

    Insertion order is kept so that any tie in the analysis (two tasks with equal
    float, equal blast radius) resolves the same way on every run and every
    machine, which is what makes the published rankings reproducible.
    """

    tasks: dict[str, Task]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self.tasks.keys())

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self):
        return iter(self.tasks.values())

    def __getitem__(self, task_id: str) -> Task:
        return self.tasks[task_id]

    def successors(self, task_id: str) -> tuple[str, ...]:
        """Every task that lists ``task_id`` among its predecessors."""
        return tuple(t.id for t in self.tasks.values() if task_id in t.deps)

    def with_duration(self, task_id: str, duration: int) -> Schedule:
        """A copy of this schedule with one task's duration replaced.

        This is the primitive the slip sensitivity is built on: inflate one
        duration, re-run the passes, measure how far the finish moved. The
        original is untouched, so the baseline never drifts under the analysis.
        """
        if task_id not in self.tasks:
            raise ScheduleError(f"unknown task id: {task_id!r}")
        new_tasks = dict(self.tasks)
        new_tasks[task_id] = replace(new_tasks[task_id], duration=duration)
        return Schedule(new_tasks)

    @classmethod
    def from_dict(cls, data: dict) -> Schedule:
        """Build and validate a Schedule from a parsed JSON object.

        The object is ``{"tasks": [ {id, name, workstream, duration, deps}, ... ]}``.
        Validation refuses duplicate ids, references to tasks that do not exist,
        and the structural errors Task checks per row.
        """
        if not isinstance(data, dict) or "tasks" not in data:
            raise ScheduleError("program must be an object with a 'tasks' array")
        rows = data["tasks"]
        if not isinstance(rows, list) or not rows:
            raise ScheduleError("'tasks' must be a non-empty array")

        tasks: dict[str, Task] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ScheduleError("each task must be an object")
            missing = {"id", "name", "workstream", "duration"} - row.keys()
            if missing:
                raise ScheduleError(f"task row missing fields: {sorted(missing)}")
            deps = tuple(row.get("deps", ()) or ())
            task = Task(
                id=str(row["id"]),
                name=str(row["name"]),
                workstream=str(row["workstream"]),
                duration=row["duration"],
                deps=deps,
            )
            if task.id in tasks:
                raise ScheduleError(f"duplicate task id: {task.id!r}")
            tasks[task.id] = task

        _check_references(tasks)
        return cls(tasks)

    @classmethod
    def from_json(cls, path: str | Path) -> Schedule:
        """Load a Schedule from a JSON file on disk."""
        p = Path(path)
        if not p.exists():
            raise ScheduleError(f"program file not found: {p}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ScheduleError(f"could not parse {p}: {exc}") from exc
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        """Round-trip back to the JSON shape, for generators and fixtures."""
        return {
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "workstream": t.workstream,
                    "duration": t.duration,
                    "deps": list(t.deps),
                }
                for t in self.tasks.values()
            ]
        }


def _check_references(tasks: dict[str, Task]) -> None:
    for task in tasks.values():
        for dep in task.deps:
            if dep not in tasks:
                raise ScheduleError(
                    f"task {task.id!r} depends on {dep!r}, which is not in the program"
                )
