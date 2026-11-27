# ADR-004: Total float versus free float, the gap the tool lives in

Status: accepted

## Context

A task has two kinds of slack. Total float is how long it can slip before the
project finish moves. Free float is how long it can slip before any successor's
earliest start moves. They are equal for a task whose successor starts the moment
it ends, and they diverge wherever a task has slack of its own. The entire
shared-float deception lives in the difference.

## Decision

Compute and keep both. The chain metric contrasts the sum of total floats (the
apparent buffer, what the column invites a reader to add up) against the head
task's total float (the shared buffer, what the chain really has when a delay
enters at the top). Free float is reported per task and is what makes the
"independent slack" of a tail task like DM4 legible.

## The bug this records

A first cut of the chain metric read free float where total float was intended
when summing the apparent buffer. Because free float is zero for every task in a
tightly-coupled series chain, the apparent buffer came out equal to the shared
buffer and the overstatement ratio was 1.0 for every chain. A ratio of exactly
1.0 everywhere is impossible for a real merge, which is how the bug announced
itself: the tool reported no deception on a fixture built to contain one.

The fix is a one-line correction (sum total floats, not free floats) plus a test,
`test_apparent_buffer_is_the_sum_of_member_total_floats`, that pins the apparent
buffer to the total-float sum so the two can never be confused again.

## Consequences

- The published 56-vs-11 contrast is a contrast of two correctly distinguished
  quantities, and `measure_shared_buffer` cross-checks the shared side against
  the propagation engine so the number is not merely the float identity restated.
- A reviewer who objects "but DM4 genuinely has independent float" is right, and
  the answer strengthens the tool: that independent float belongs to DM4 alone
  and shrinks as soon as a delay arrives down the chain. The column cannot tell
  shared float from independent float; keeping both numbers is what lets this
  tool do so.
