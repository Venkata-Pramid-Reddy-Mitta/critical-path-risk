"""Why this file exists.

The committed fixture proves the tool catches a deception that was built for it
to catch, which is necessary but not sufficient: a reviewer is right to ask
whether the shared-float trap is a property of one hand-made graph or of
schedules in general. This generator answers that by producing many random but
realistic multi-workstream programs from a seed, so the robustness experiment
can report how often the float column overstates a chain's buffer across a
thousand programs nobody tuned.

A program here is a set of workstreams, each a chain of tasks, wired to a shared
backbone workstream that the others depend on at random points, plus a final
integration task that merges them. That shape (parallel chains feeding a merge)
is what creates both critical paths and shared-float chains, which is the whole
subject. Everything is driven by a single ``random.Random(seed)`` so a given
seed always yields the identical program, on any machine.
"""

from __future__ import annotations

import random

from .model import Schedule, Task


def generate_program(
    seed: int,
    workstreams: int = 4,
    tasks_per_stream: int = 4,
    min_duration: int = 5,
    max_duration: int = 15,
    cross_link_probability: float = 0.5,
) -> Schedule:
    """A deterministic random program for a given seed.

    ``workstreams`` parallel chains (the first is the shared backbone), each
    ``tasks_per_stream`` tasks long, with cross-links from later streams back to
    an earlier backbone task, and a final integration task merging every stream.
    """
    if workstreams < 2:
        raise ValueError("need at least two workstreams to form a merge")
    if tasks_per_stream < 2:
        raise ValueError("need at least two tasks per stream to form a chain")
    if min_duration <= 0 or max_duration < min_duration:
        raise ValueError("invalid duration bounds")

    rng = random.Random(seed)
    tasks: list[Task] = []
    stream_task_ids: list[list[str]] = []

    for s in range(workstreams):
        ids_here: list[str] = []
        for t in range(tasks_per_stream):
            tid = f"W{s}T{t}"
            deps: list[str] = []
            if t > 0:
                deps.append(ids_here[-1])
            # Non-backbone streams may hang their first task off a backbone task,
            # which is what creates the merges and the slack chains.
            if s > 0 and t == 0 and rng.random() < cross_link_probability:
                backbone = stream_task_ids[0]
                anchor = backbone[rng.randrange(len(backbone))]
                deps.append(anchor)
            tasks.append(
                Task(
                    id=tid,
                    name=f"Stream {s} task {t}",
                    workstream=f"WS{s}",
                    duration=rng.randint(min_duration, max_duration),
                    deps=tuple(deps),
                )
            )
            ids_here.append(tid)
        stream_task_ids.append(ids_here)

    # Final integration merges the tail of every stream.
    tasks.append(
        Task(
            id="INT",
            name="Integration and go-live",
            workstream="Integration",
            duration=rng.randint(min_duration, max_duration),
            deps=tuple(ids[-1] for ids in stream_task_ids),
        )
    )
    return Schedule({t.id: t for t in tasks})
