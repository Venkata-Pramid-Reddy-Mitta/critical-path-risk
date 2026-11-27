"""Why this file exists.

The analysis is only useful if a program manager can read it in the form they
already use: a status page. This module renders the AnalysisResult two ways, a
plain-text report for the terminal and a standalone HTML report for a status
pack, from the same result object so the two can never disagree. The HTML is
also what the screenshot tool photographs for the README, so the verdict badge
carries an explicit color pair and the screenshot tool reads its computed style
back to prove it is legible (a guard added after a green-on-green badge shipped
in an earlier project, recorded in the war story).

No templating engine: the report is a handful of tables, so it is built with
``html.escape`` and string joins, which keeps the dependency list empty and the
output byte-for-byte deterministic.
"""

from __future__ import annotations

from html import escape
from typing import Any

from .analysis import AnalysisResult, Gate


def render_json(result: AnalysisResult) -> dict[str, Any]:
    """A machine-readable summary of one analysis run.

    This is the per-run report written by ``cpr analyze --json``. It is distinct
    from ``docs/metrics.json``, which the receipts tooling builds by re-running
    the suite and every experiment; this one is a convenience for scripting a
    single program.
    """
    cpm = result.cpm
    wc = result.worst_chain
    h = result.hidden_task
    j = result.joint_blind_spot
    return {
        "task_count": len(result.schedule),
        "project_finish_days": cpm.project_duration,
        "critical_path": list(cpm.critical_path),
        "critical_path_length": len(cpm.critical_path),
        "gate": result.gate.value,
        "gate_reasons": list(result.gate_reasons),
        "slip_days": result.policy.slip_days,
        "worst_chain": None
        if wc is None
        else {
            "tasks": list(wc.tasks),
            "apparent_buffer_days": wc.apparent_buffer,
            "shared_buffer_days": wc.shared_buffer,
            "overstatement_ratio": round(wc.overstatement_ratio, 3),
        },
        "hidden_task": None
        if h is None
        else {
            "id": h.id,
            "total_float_days": h.total_float,
            "blast_radius_days": h.blast_radius,
            "rerouting_threshold_days": h.rerouting_threshold,
        },
        "joint_blind_spot": None
        if j is None
        else {
            "task_a": j.task_a,
            "task_b": j.task_b,
            "slip_each_days": j.slip_each,
            "single_delay_a_days": j.single_delay_a,
            "single_delay_b_days": j.single_delay_b,
            "joint_delay_days": j.joint_delay,
        },
    }


def render_console(result: AnalysisResult) -> str:
    cpm = result.cpm
    lines: list[str] = []
    lines.append("critical-path-risk analysis")
    lines.append("=" * 52)
    lines.append(
        f"tasks: {len(result.schedule)}    "
        f"project finish: {cpm.project_duration} working days"
    )
    lines.append(
        f"critical path ({len(cpm.critical_path)} tasks): "
        f"{' -> '.join(cpm.critical_path)}"
    )
    lines.append("")

    verdict = "RISK FLAGGED" if result.gate is Gate.FLAGGED else "CLEAN"
    lines.append(f"gate: {verdict}")
    for reason in result.gate_reasons:
        lines.append(f"  - {reason}")
    lines.append("")

    if result.worst_chain is not None:
        wc = result.worst_chain
        lines.append("shared-float deception (worst chain)")
        lines.append("-" * 52)
        lines.append(f"  chain: {' -> '.join(wc.tasks)}")
        lines.append(
            f"  float column sums to {wc.apparent_buffer} days; "
            f"real shared buffer {wc.shared_buffer} days "
            f"(overstated {wc.overstatement_ratio:.1f}x)"
        )
        lines.append("")

    if result.hidden_task is not None:
        h = result.hidden_task
        lines.append("the non-obvious task")
        lines.append("-" * 52)
        lines.append(
            f"  {h.id} ({h.name}) is off the critical path with {h.total_float} days "
            f"float, yet a {result.policy.slip_days}-day slip delays go-live "
            f"{h.blast_radius} days; it re-routes the critical path at a "
            f"{h.rerouting_threshold}-day slip"
        )
        lines.append("")

    lines.append(
        f"blast-radius ranking ({result.policy.slip_days}-day slip, "
        f"top {result.policy.top_n})"
    )
    lines.append("-" * 52)
    lines.append(f"  {'task':<6}{'delay':>6}{'float':>7}{'reroute':>9}  on critical path")
    for row in result.ranking[: result.policy.top_n]:
        crit = "yes" if row.is_critical else "no"
        lines.append(
            f"  {row.id:<6}{row.blast_radius:>6}{row.total_float:>7}"
            f"{row.rerouting_threshold:>9}  {crit}"
        )
    lines.append("")

    if result.joint_blind_spot is not None:
        j = result.joint_blind_spot
        lines.append("boundary: the single-slip blind spot")
        lines.append("-" * 52)
        lines.append(
            f"  {j.task_a} and {j.task_b} each absorb a slip of {j.slip_each} days with "
            f"0 delay alone ({j.single_delay_a} and {j.single_delay_b}); slipped "
            f"together they delay go-live {j.joint_delay} days"
        )
    return "\n".join(lines)


_CSS = """
body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       color: #1a1a1a; background: #ffffff; margin: 0; padding: 32px; line-height: 1.45; }
.wrap { max-width: 920px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px 0; }
h2 { font-size: 16px; margin: 28px 0 8px 0; border-bottom: 1px solid #e3e3e3; padding-bottom: 4px; }
.sub { color: #555; font-size: 13px; margin: 0 0 16px 0; }
.verdict { display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: 700;
           font-size: 13px; letter-spacing: 0.04em; }
.verdict.flagged { background: #b3261e; color: #ffffff; }
.verdict.clean { background: #1b5e20; color: #ffffff; }
.reasons { margin: 10px 0 0 0; padding-left: 18px; color: #333; font-size: 13px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; margin: 6px 0 4px 0; }
th, td { text-align: left; padding: 5px 10px; border-bottom: 1px solid #ededed; }
th { background: #f4f4f4; font-weight: 600; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
tr.crit td { color: #777; }
tr.hidden td { background: #fff4e5; font-weight: 600; }
.callout { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px;
           padding: 12px 14px; margin: 8px 0; font-size: 13px; }
.big { font-size: 15px; font-weight: 700; }
.foot { color: #777; font-size: 12px; margin-top: 28px; }
"""


def render_html(result: AnalysisResult) -> str:
    cpm = result.cpm
    flagged = result.gate is Gate.FLAGGED
    verdict_class = "flagged" if flagged else "clean"
    verdict_text = "RISK FLAGGED" if flagged else "CLEAN"

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append("<title>critical-path-risk report</title>")
    parts.append(f"<style>{_CSS}</style></head><body><div class='wrap'>")
    parts.append("<h1>critical-path-risk</h1>")
    parts.append(
        f"<p class='sub'>{len(result.schedule)} tasks, "
        f"project finish {cpm.project_duration} working days, "
        f"critical path {len(cpm.critical_path)} tasks</p>"
    )
    parts.append(f"<span class='verdict {verdict_class}'>{verdict_text}</span>")
    if result.gate_reasons:
        parts.append("<ul class='reasons'>")
        for reason in result.gate_reasons:
            parts.append(f"<li>{escape(reason)}</li>")
        parts.append("</ul>")

    if result.worst_chain is not None:
        wc = result.worst_chain
        chain_html = " &rarr; ".join(escape(t) for t in wc.tasks)
        parts.append("<h2>Shared-float deception</h2>")
        parts.append(
            "<div class='callout'>Chain "
            f"<b>{chain_html}</b>. The total-float column "
            f"invites a reader to sum <span class='big'>{wc.apparent_buffer}</span> days "
            "of buffer. Entered at the head and propagated, the chain has "
            f"<span class='big'>{wc.shared_buffer}</span> days "
            f"(overstated {wc.overstatement_ratio:.1f}x).</div>"
        )

    if result.hidden_task is not None:
        h = result.hidden_task
        parts.append("<h2>The non-obvious task</h2>")
        parts.append(
            "<div class='callout'><b>" + escape(f"{h.id} ({h.name})") + "</b> is off the "
            f"critical path with {h.total_float} days float, so a Gantt review "
            f"deprioritizes it. A {result.policy.slip_days}-day slip there delays go-live "
            f"<span class='big'>{h.blast_radius}</span> days, and it re-routes the critical "
            f"path at a <span class='big'>{h.rerouting_threshold}</span>-day slip.</div>"
        )

    parts.append(f"<h2>Blast-radius ranking ({result.policy.slip_days}-day slip)</h2>")
    parts.append("<table><thead><tr>")
    for head in ("Task", "Workstream", "Delay (days)", "Float", "Re-route at", "On critical path"):
        parts.append(f"<th>{head}</th>")
    parts.append("</tr></thead><tbody>")
    hidden_id = result.hidden_task.id if result.hidden_task else None
    for row in result.ranking[: result.policy.top_n]:
        row_class = "crit" if row.is_critical else ("hidden" if row.id == hidden_id else "")
        cls = f" class='{row_class}'" if row_class else ""
        parts.append(f"<tr{cls}>")
        parts.append(f"<td>{escape(row.id)}</td>")
        parts.append(f"<td>{escape(row.workstream)}</td>")
        parts.append(f"<td class='num'>{row.blast_radius}</td>")
        parts.append(f"<td class='num'>{row.total_float}</td>")
        parts.append(f"<td class='num'>{row.rerouting_threshold}</td>")
        parts.append(f"<td>{'yes' if row.is_critical else 'no'}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")

    if result.joint_blind_spot is not None:
        j = result.joint_blind_spot
        parts.append("<h2>Boundary: the single-slip blind spot</h2>")
        parts.append(
            "<div class='callout'>"
            f"<b>{escape(j.task_a)}</b> and <b>{escape(j.task_b)}</b> each absorb a "
            f"slip of {j.slip_each} days with <b>0</b> delay measured alone "
            f"({j.single_delay_a} and {j.single_delay_b}). Slipped together they delay "
            f"go-live <span class='big'>{j.joint_delay}</span> days. The single-slip "
            "ranking above cannot see this pair; pairwise search is the Pivot.</div>"
        )

    parts.append(
        "<p class='foot'>Generated by critical-path-risk from the committed program. "
        "Every number is reproduced by <code>make verify</code>.</p>"
    )
    parts.append("</div></body></html>")
    return "\n".join(parts)
