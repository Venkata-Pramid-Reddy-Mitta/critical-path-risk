# ADR-003: Determinism under hash randomization

Status: accepted

## Context

The tool publishes fixed numbers: a critical path, a blast-radius ranking, a
worst chain. Those outputs depend on how ties are broken when several tasks are
equally ready in the topological sort or equally damaging in the ranking. If the
tie-break is not deterministic, the published numbers are not reproducible, which
would undermine the entire receipts mechanism.

## Decision

Make every ordering deterministic and independent of the Python hash seed:

- Kahn's ready queue is seeded as a `deque` in the schedule's insertion order,
  not from a set comprehension.
- Every tie in the critical-path trace and the sensitivity ranking breaks by
  `order.index`, the position in that deterministic topological order.

## The bug this fixes

An early draft seeded the ready queue from `{tid for tid in ... if indegree == 0}`,
a set. Set iteration order for strings depends on the hash seed, which Python
randomizes per process. With several tasks ready at once (after CM1, three tasks
become ready simultaneously), the topological order differed between runs.

The subtle part is what did and did not move. The headline numbers were stable:
the critical path is a chain whose internal order is forced by its edges, so
`order.index` gave the critical tasks the same relative order regardless of the
hash seed. What moved was the ordering of the equally-ranked slack tasks in the
blast-radius table. DM2 and CM3 both have 11 days of float and zero delay from a
five-day slip, so the tie between them breaks on `order.index`, and the
topological order underneath that index was not stable. From one run to the next
the published ranking listed them as `...CM3-DM2...` or `...DM2-CM3...`.

The lesson that shaped the test: a determinism check that compared only the
headline summary would have passed while the bug was live, because the summary
was stable and only the ranking underneath it moved. The test has to compare the
thing that actually drifted.

## Consequences

- `tests/test_determinism.py` pins it three ways: repeated in-process runs are
  identical, the topological order is stable, and a subprocess run under six
  `PYTHONHASHSEED` values produces one identical full ranking order. Run against
  the set-seeded draft, the subprocess test fails with two distinct orderings; run
  against the fix, it passes.
- The lesson generalizes: anywhere a published artifact depends on iteration
  order, the order must be made explicit, not inherited from a set or a dict built
  in an unspecified order, and the test must assert on the artifact that moved,
  not on a summary that happened to survive.
