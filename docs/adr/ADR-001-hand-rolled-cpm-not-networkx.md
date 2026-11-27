# ADR-001: Hand-roll the critical path method instead of using a graph library

Status: accepted

## Context

The core of this tool is a longest-path computation over a DAG: the forward and
backward passes of the critical path method, total and free float, and the
per-node slip sensitivity built on top. A library such as NetworkX offers
`dag_longest_path` and would remove perhaps forty lines of code.

## Decision

Implement the CPM in plain Python, in `cpr.cpm`, using only the standard library.

Two reasons, one of them the whole point of the project:

1. The longest-path computation is the exact skill this repository exists to
   demonstrate. Calling `networkx.dag_longest_path` would move the one piece of
   author-built algorithm behind a library call, which is precisely the "stolen
   valor" a reviewer looks for. A portfolio piece has to show the thing it
   claims, not import it.
2. Zero runtime dependencies makes install trivial and offline reproduction
   exact. `make verify` runs from a fresh clone with no network and no wheels to
   resolve, which is worth more here than the convenience of a library.

## Consequences

- The topological sort (Kahn), both passes, and the float derivations are
  visible and tested directly, with property-named tests on a hand-worked
  diamond whose every number is checked on paper in the test docstrings.
- The repository carries the cost of maintaining its own graph code. That cost
  is small (the algorithm is standard and stable) and is the intended cost.
- Cycle detection falls out of the Kahn sort for free: a graph that never
  reaches in-degree zero everywhere is not a DAG, and `CycleError` names the
  tasks caught in the cycle.
- If this tool ever needed resource-constrained scheduling or minimum-cost flow,
  the calculus would change and a library would earn its place. That is future
  work, recorded here so the boundary is explicit.
