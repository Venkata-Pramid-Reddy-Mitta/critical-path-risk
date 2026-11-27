# ADR-002: Finish-to-start dependencies only

Status: accepted

## Context

Real project tools (MS Project, Primavera) support four dependency types
(finish-to-start, start-to-start, finish-to-finish, start-to-finish) and
leads and lags on each edge. A faithful importer would need all of them.

## Decision

Model finish-to-start dependencies only: a task cannot start until every task in
its `deps` list has finished, with no lead or lag. State this boundary in the
model, the README, and here.

## Consequences

- The vast majority of real schedule dependencies are finish-to-start, so the
  tool is useful on real topologies, and every structural claim it makes (shared
  float, re-routing, the joint boundary) is a property of the dependency graph
  that would hold identically against a real schedule with the same shape.
- The tool deliberately cannot ingest a schedule that leans on start-to-start
  overlaps or negative lags to compress its timeline. Fed one, it would compute a
  longer critical path than the real plan has. That is a wrong answer, so the
  right behavior is to refuse the richer input rather than silently approximate
  it; the importer for real exports (future work) must reject or flag non
  finish-to-start edges rather than dropping them.
- Chain enumeration is bounded: the non-critical subgraph is walked for maximal
  head-to-leaf paths, which is exponential in the worst case on a wide branching
  slack region. The enumeration is capped at 10,000 chains and the cap sets a
  `truncated` flag that the report surfaces, rather than silently dropping
  chains. On realistic program WBS structures the cap is never approached.
