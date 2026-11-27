"""Why this file exists.

The CLI, the report, the experiments and the tests all want the same bundle of
results from a schedule: the CPM passes, the slack chains, the blast-radius
ranking, the two headline tasks, the joint blind spot, and the gate verdict
against a policy. Computing that in one place keeps the gate definition single
sourced, so the exit code the CLI returns and the verdict the HTML report prints
can never disagree.

The gate is deliberately simple and entirely policy driven: a program is flagged
when its float column overstates a chain's buffer beyond the allowed ratio, or
when a slack task sits within the re-routing alarm window. Neither condition is
an error; both mean "analyzed successfully, and here is a risk the summary did
not show".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .chains import ChainReport, SlackChain, enumerate_slack_chains
from .config import Policy
from .cpm import CpmResult, compute_cpm
from .joint import JointBlindSpot, find_worst_joint_blind_spot
from .model import Schedule
from .sensitivity import (
    TaskSensitivity,
    nearest_rerouting,
    sensitivity_ranking,
    top_hidden_task,
)


class Gate(StrEnum):
    CLEAN = "clean"
    FLAGGED = "flagged"


@dataclass(frozen=True)
class AnalysisResult:
    schedule: Schedule
    policy: Policy
    cpm: CpmResult
    chains: ChainReport
    worst_chain: SlackChain | None
    ranking: tuple[TaskSensitivity, ...]
    hidden_task: TaskSensitivity | None
    nearest_reroute: TaskSensitivity | None
    joint_blind_spot: JointBlindSpot | None
    gate: Gate
    gate_reasons: tuple[str, ...]


def analyze(schedule: Schedule, policy: Policy) -> AnalysisResult:
    """Run the full analysis and apply the policy gate."""
    cpm = compute_cpm(schedule)
    chains = enumerate_slack_chains(schedule, cpm)
    worst_chain = chains.worst(min_length=2)
    ranking = sensitivity_ranking(schedule, cpm, policy.slip_days)
    hidden = top_hidden_task(ranking)
    reroute = nearest_rerouting(ranking)
    joint = find_worst_joint_blind_spot(schedule, cpm)

    reasons: list[str] = []
    if worst_chain is not None and (
        worst_chain.overstatement_ratio >= policy.max_float_overstatement_ratio
    ):
        reasons.append(
            f"float column overstates chain {list(worst_chain.tasks)} buffer "
            f"{worst_chain.apparent_buffer}d vs {worst_chain.shared_buffer}d shared "
            f"(ratio {worst_chain.overstatement_ratio:.1f})"
        )
    if reroute is not None and reroute.rerouting_threshold <= policy.rerouting_alarm_days:
        reasons.append(
            f"slack task {reroute.id} re-routes the critical path at a "
            f"{reroute.rerouting_threshold}d slip (within the "
            f"{policy.rerouting_alarm_days}d alarm window)"
        )

    gate = Gate.FLAGGED if reasons else Gate.CLEAN
    return AnalysisResult(
        schedule=schedule,
        policy=policy,
        cpm=cpm,
        chains=chains,
        worst_chain=worst_chain,
        ranking=ranking,
        hidden_task=hidden,
        nearest_reroute=reroute,
        joint_blind_spot=joint,
        gate=gate,
        gate_reasons=tuple(reasons),
    )
