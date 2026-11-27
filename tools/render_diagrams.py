#!/usr/bin/env python
"""Render the architecture diagram to a committed SVG.

Diagrams are rendered by a tool in the repository so a reviewer can regenerate
them and so the image renders identically on GitHub, in a PDF export and offline.
This builds the SVG directly from a node and edge spec rather than through a
diagram library, which sidesteps the rendering traps that cost time on earlier
builds: the SVG is valid XML (text labels, not HTML in a foreignObject), it has
explicit width and height taken from the viewBox (not a percentage width an
img tag cannot size), and it paints one light background rectangle so edge
labels are legible in a dark GitHub theme. See references/ci-and-rendering-traps.

The node and edge spec below is the source; the README shows the same pipeline as
a short text fence underneath the image.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "docs" / "diagrams" / "architecture.svg"

W, H = 940, 560

# (id, x, y, w, h, line1, line2)
NODES = [
    ("input", 360, 20, 220, 46, "fixtures/program.json", "tasks, durations, deps"),
    ("model", 360, 100, 220, 46, "model.Schedule", "validate, refuse a bad DAG"),
    ("cpm", 320, 180, 300, 54, "cpm", "topo sort, forward/backward pass,", "floats, critical path"),
    ("chains", 40, 290, 250, 60, "chains", "maximal slack chains,", "apparent vs shared buffer"),
    ("sens", 345, 290, 250, 60, "sensitivity", "per-task blast radius,", "re-routing thresholds"),
    ("joint", 650, 290, 250, 60, "joint", "pairwise blind spot", "(the boundary)"),
    ("analysis", 345, 400, 250, 50, "analysis", "apply the policy gate"),
    ("report", 60, 486, 230, 50, "report", "console and HTML, exit codes"),
    ("receipts", 650, 486, 230, 50, "tools/receipts", "re-measure, check_numbers"),
]

# (from, to)
EDGES = [
    ("input", "model"),
    ("model", "cpm"),
    ("cpm", "chains"),
    ("cpm", "sens"),
    ("cpm", "joint"),
    ("chains", "analysis"),
    ("sens", "analysis"),
    ("joint", "analysis"),
    ("analysis", "report"),
    ("analysis", "receipts"),
]

NODE_INDEX = {n[0]: n for n in NODES}


def _center_bottom(node):
    _id, x, y, w, h, *_ = node
    return x + w / 2, y + h


def _center_top(node):
    _id, x, y, w, _h, *_ = node
    return x + w / 2, y


def _nearest_points(a, b):
    """Pick anchor points so the arrow leaves the bottom and enters the top."""
    ax, ay = _center_bottom(a)
    bx, by = _center_top(b)
    return ax, ay, bx, by


def build_svg() -> str:
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Helvetica, Arial, sans-serif">'
    )
    # Light background so edge labels are legible in a dark theme.
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fbfbfc"/>')
    parts.append(
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" '
        'orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L8,3 L0,6 z" fill="#5b6472"/></marker></defs>'
    )

    # Edges first so nodes sit on top.
    for src, dst in EDGES:
        ax, ay, bx, by = _nearest_points(NODE_INDEX[src], NODE_INDEX[dst])
        midy = (ay + by) / 2
        path = f"M{ax},{ay} C{ax},{midy} {bx},{midy} {bx},{by - 2}"
        parts.append(
            f'<path d="{path}" fill="none" stroke="#5b6472" stroke-width="1.5" '
            'marker-end="url(#arrow)"/>'
        )

    palette = {
        "input": "#e8eef7",
        "model": "#eef2f6",
        "cpm": "#dfeafc",
        "chains": "#fff1e0",
        "sens": "#fff1e0",
        "joint": "#fff1e0",
        "analysis": "#e3f1e4",
        "report": "#eef2f6",
        "receipts": "#eef2f6",
    }
    for node in NODES:
        nid, x, y, w, h, *labels = node
        fill = palette.get(nid, "#eef2f6")
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" ry="7" '
            f'fill="{fill}" stroke="#b7c0cc" stroke-width="1"/>'
        )
        n_lines = len(labels)
        first_dy = -((n_lines - 1) * 8)
        cy = y + h / 2 + 4
        for i, line in enumerate(labels):
            weight = "700" if i == 0 else "400"
            size = "13" if i == 0 else "11.5"
            color = "#1a1a1a" if i == 0 else "#44505f"
            ty = cy + first_dy + i * 16
            parts.append(
                f'<text x="{x + w / 2}" y="{ty}" text-anchor="middle" '
                f'font-size="{size}" font-weight="{weight}" fill="{color}">'
                f"{escape(line)}</text>"
            )

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
