"""Why this file exists.

The total-float column is the most-read number on a schedule and the most
misread. Two tasks in series, each showing 11 days of float, invite a reader to
believe there are 22 days of buffer between them. There are not. Slip the first
by 11 and the second drops to 0: the float is shared down the chain, not summed
across it. This module makes that concrete by finding the maximal chains of
non-critical tasks and, for each, contrasting the buffer the column invites you
to add up (the apparent buffer) with the buffer the chain actually has when a
delay enters at its head (the shared buffer).

The shared buffer of a chain is the total float of its head task: slip the head
by that much and the whole chain cascades to exactly the project finish, with no
day to spare. ``sensitivity.measure_shared_buffer`` verifies this against the
propagation engine rather than trusting the identity, and a test pins the two
together.

Chain enumeration walks only the non-critical subgraph and emits maximal head to
leaf paths. On a branching slack region that is an exponential number of paths in
the worst case, so enumeration is capped and the cap is reported rather than
silently truncating, which is the boundary recorded in ADR-002.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cpm import CpmResult
from .model import Schedule

MAX_CHAINS = 10_000


@dataclass(frozen=True)
class SlackChain:
    """A maximal series of non-critical tasks and the two buffers for it."""

    tasks: tuple[str, ...]
    apparent_buffer: int
    shared_buffer: int

    @property
    def overstatement_ratio(self) -> float:
        """Apparent buffer divided by the real shared buffer (1.0 if honest)."""
        if self.shared_buffer == 0:
            return float("inf")
        return self.apparent_buffer / self.shared_buffer

    @property
    def length(self) -> int:
        return len(self.tasks)


@dataclass(frozen=True)
class ChainReport:
    chains: tuple[SlackChain, ...]
    truncated: bool

    def worst(self, min_length: int = 2) -> SlackChain | None:
        """The chain whose float column overstates its buffer by the most.

        Restricted to chains of at least ``min_length`` tasks, because a single
        task cannot overstate anything: its apparent and shared buffers are the
        same number.
        """
        candidates = [c for c in self.chains if c.length >= min_length]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda c: (c.overstatement_ratio, c.apparent_buffer, -len(c.tasks)),
        )


def enumerate_slack_chains(schedule: Schedule, cpm: CpmResult) -> ChainReport:
    """Every maximal chain of non-critical tasks, with both buffers computed."""
    tf = cpm.total_float
    noncrit = {tid for tid in cpm.order if tf[tid] > 0}

    succ_nc: dict[str, list[str]] = {
        tid: [s for s in schedule.successors(tid) if s in noncrit] for tid in noncrit
    }
    has_nc_pred = {
        tid: any(d in noncrit for d in schedule[tid].deps) for tid in noncrit
    }
    starts = [tid for tid in cpm.order if tid in noncrit and not has_nc_pred[tid]]

    chains: list[SlackChain] = []
    truncated = False

    def emit(path: list[str]) -> None:
        apparent = sum(tf[t] for t in path)
        shared = tf[path[0]]
        chains.append(
            SlackChain(tasks=tuple(path), apparent_buffer=apparent, shared_buffer=shared)
        )

    # Iterative DFS so a deep chain cannot blow the Python recursion limit.
    for start in starts:
        stack: list[list[str]] = [[start]]
        while stack:
            if len(chains) >= MAX_CHAINS:
                truncated = True
                break
            path = stack.pop()
            tail = path[-1]
            nexts = succ_nc[tail]
            if not nexts:
                emit(path)
                continue
            # Push successors in reverse insertion order so they pop in order,
            # keeping the emitted list deterministic.
            for nxt in reversed(nexts):
                stack.append([*path, nxt])
        if truncated:
            break

    return ChainReport(chains=tuple(chains), truncated=truncated)
