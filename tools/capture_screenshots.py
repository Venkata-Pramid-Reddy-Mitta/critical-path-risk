#!/usr/bin/env python
"""Screenshot the real HTML report for the README.

The image is generated from the tool's own output so a reviewer can regenerate
it, and the tool rebuilds the report from the fixture if it is missing rather
than photographing whatever happens to be on disk. The one rule carried over from
earlier builds: read back the computed style of the verdict badge and fail if it
is invisible, because a screenshot is the only step in the pipeline that can see
pixels, and a badge that renders the same color as its background has shipped
before while every test still passed.

Needs the evidence extra (playwright) and a chromium install.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

REPORT = REPO_ROOT / "docs" / "report" / "program.html"
OUT_DIR = REPO_ROOT / "docs" / "screenshots"
FIXTURE = REPO_ROOT / "fixtures" / "program.json"


def _ensure_report() -> None:
    if REPORT.exists():
        return
    from cpr.analysis import analyze
    from cpr.config import load_policy
    from cpr.model import Schedule
    from cpr.report import render_html

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    result = analyze(Schedule.from_json(FIXTURE), load_policy())
    REPORT.write_text(render_html(result), encoding="utf-8")


def main() -> int:
    from playwright.sync_api import sync_playwright

    _ensure_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 900}, device_scale_factor=2)
        page.goto(REPORT.resolve().as_uri())

        badge = page.evaluate(
            """() => {
                const b = document.querySelector('.verdict');
                if (!b) return null;
                const s = getComputedStyle(b);
                return {color: s.color, background: s.backgroundColor,
                        visible: b.offsetWidth > 0 && b.offsetHeight > 0,
                        text: b.textContent};
            }"""
        )
        if not badge or not badge["visible"]:
            print("capture_screenshots: FAIL, verdict badge is not visible")
            return 1
        if badge["color"] == badge["background"]:
            print("capture_screenshots: FAIL, verdict badge color equals its background")
            return 1

        full = OUT_DIR / "report.png"
        page.screenshot(path=str(full), full_page=True)
        manifest.append({"image": full.name, "kind": "full report", "badge": badge})

        # A tighter crop of the first screen (verdict and the deception callout),
        # framed from the top of the page to the blast-radius heading.
        clip = page.evaluate(
            """() => {
                const h = [...document.querySelectorAll('h2')]
                    .find(e => e.textContent.includes('Blast-radius'));
                const top = 0;
                const bottom = h ? h.getBoundingClientRect().top + window.scrollY : 520;
                return {x: 0, y: top, width: document.body.scrollWidth, height: bottom};
            }"""
        )
        top = OUT_DIR / "report_top.png"
        page.screenshot(
            path=str(top),
            clip={"x": 0, "y": clip["y"], "width": clip["width"], "height": clip["height"]},
            full_page=True,
        )
        manifest.append({"image": top.name, "kind": "first screen", "framed_to": "Blast-radius"})

        browser.close()

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"capture_screenshots: wrote {len(manifest)} images, badge reads {manifest[0]['badge']['text']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
