# ADR-005: Exit-code semantics, and why the gate is opt-in

Status: accepted

## Context

The CLI can be wired into a pipeline. A program office might want the build to
fail when the analysis finds a hidden risk. But the shipped fixture is flagged by
design (it exists to demonstrate a flagged program), so a gate that always fails
on the fixture would turn the repository's own CI red.

## Decision

Three exit codes, and the gate is opt-in:

- `0`: the analysis ran and the program is clean against the policy, or `--gate`
  was not passed.
- `2`: the analysis ran and a hidden risk was flagged. Only returned with
  `--gate`.
- `1`: the analysis could not run (invalid schedule, a cycle, a broken policy
  file).

Without `--gate`, `cpr analyze` always exits 0 after printing, so `make report`
on the deliberately flagged fixture does not fail the build.

## Consequences

- The important distinction is between `2` and `1`: "I looked and the answer is
  no" must never be confused with "I could not look". A pipeline can trust a `2`
  to be a real finding, not a crash, and a `1` to be an input problem.
- The gate being opt-in follows the hard-won CI rule that a check which always
  fails gets deleted or weakened within a week, after which nothing is checked. A
  team that wants the gate adds `--gate` to their own pipeline against their own
  programs; the thresholds live in `policy.toml`, with a comment on each.
- The policy is validated on load and on override, so a `--slip 0` or a sub-1.0
  overstatement ratio is refused with a message and exit `1`, rather than
  producing a nonsensical analysis.
