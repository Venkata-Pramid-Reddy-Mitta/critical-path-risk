#!/usr/bin/env python
"""Record a demo of the tool as a replay, not a screen recording.

Every line of terminal text in the output is real captured stdout from running
the command, never hand written, and each segment is paced by the command's
measured wall time so a slow step looks slow. The pipeline: run each command and
capture stdout, exit code and duration; build a self-contained HTML terminal that
types the command and reveals its captured output; record the page with
Playwright to webm; transcode to an MP4 and an autoplaying GIF with ffmpeg.

A manifest with every command, its exit code and its duration is committed next
to the video so the replay can be audited against the commands it claims to run.
Needs the evidence extra (playwright), a chromium install, and ffmpeg.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "docs" / "video"
ENV_SRC = str(REPO_ROOT / "src")

# Ordered as the argument, not the feature list: the full report first, then the
# gate exit code, then the result that generalizes, then the receipts.
COMMANDS = [
    ["cpr", "analyze", "fixtures/program.json"],
    ["cpr", "analyze", "fixtures/program.json", "--gate", "--quiet"],
    ["python", "experiments/exp05_robustness.py"],
    ["python", "tools/check_numbers.py"],
]


def _run(cmd: list[str]) -> dict:
    env = {"PYTHONPATH": ENV_SRC, "PATH": __import__("os").environ["PATH"]}
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env={**__import__("os").environ, **env})
    duration = time.perf_counter() - start
    out = (proc.stdout or "") + (proc.stderr or "")
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "duration_s": round(duration, 3),
        "output": out.rstrip("\n"),
    }


def _player_html(segments: list[dict]) -> str:
    data = json.dumps(
        [
            {"cmd": s["command"], "out": s["output"], "exit": s["exit_code"], "dur": s["duration_s"]}
            for s in segments
        ]
    )
    return """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#0f1117;}
  .term{width:900px;margin:18px auto;background:#11141b;border:1px solid #232733;
    border-radius:8px;padding:16px 18px;font-family:ui-monospace,Menlo,Consolas,monospace;
    font-size:13.5px;line-height:1.5;color:#d7dce5;min-height:460px;}
  .bar{color:#5b6472;margin-bottom:8px;}
  .dot{height:11px;width:11px;border-radius:50%;display:inline-block;margin-right:6px;}
  .r{background:#ff5f56;}.y{background:#ffbd2e;}.g{background:#27c93f;}
  .prompt{color:#7ee787;}.cmd{color:#e6edf3;}.out{white-space:pre-wrap;color:#b9c2d0;}
  .exit0{color:#7ee787;}.exit2{color:#ffbd2e;}
</style></head><body><div class="term" id="t">
  <div class="bar"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
  &nbsp; critical-path-risk demo (replay of captured output)</div>
  <div id="body"></div></div>
<script>
const SEG = __DATA__;
const body = document.getElementById('body');
function line(cls, text){const d=document.createElement('div');d.className=cls;d.textContent=text;body.appendChild(d);}
async function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
async function typeCmd(cmd){
  const d=document.createElement('div');
  const p=document.createElement('span');p.className='prompt';p.textContent='$ ';d.appendChild(p);
  const c=document.createElement('span');c.className='cmd';d.appendChild(c);body.appendChild(d);
  for(const ch of cmd){c.textContent+=ch;await sleep(16);}
}
async function run(){
  for(const s of SEG){
    await typeCmd(s.cmd);
    await sleep(Math.min(1400, 300 + s.dur*120));
    if(s.out){const o=document.createElement('div');o.className='out';o.textContent=s.out;body.appendChild(o);}
    const code=document.createElement('div');
    code.className = s.exit===0 ? 'exit0' : 'exit2';
    code.textContent = '[exit '+s.exit+']';
    body.appendChild(code);
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(900);
  }
  document.title = 'DONE';
}
run();
</script></body></html>""".replace("__DATA__", data)


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Warm the import so the first segment is not charged for interpreter start.
    subprocess.run(["cpr", "--help"], cwd=REPO_ROOT, capture_output=True,
                   env={**__import__("os").environ, "PYTHONPATH": ENV_SRC})

    segments = [_run(cmd) for cmd in COMMANDS]
    player = OUT_DIR / "player.html"
    player.write_text(_player_html(segments), encoding="utf-8")

    manifest = {"segments": segments}
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 940, "height": 520},
            record_video_dir=str(OUT_DIR),
            record_video_size={"width": 940, "height": 520},
        )
        page = context.new_page()
        page.goto(player.resolve().as_uri())
        # Wait for the animation to finish (title flips to DONE), with a ceiling.
        with contextlib.suppress(Exception):
            page.wait_for_function("document.title === 'DONE'", timeout=30000)
        page.wait_for_timeout(600)
        video_path = page.video.path()
        context.close()
        browser.close()

    webm = OUT_DIR / "demo.webm"
    Path(video_path).replace(webm)

    mp4 = OUT_DIR / "demo.mp4"
    gif = OUT_DIR / "demo.gif"
    palette = OUT_DIR / "palette.png"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(webm), "-movflags", "+faststart",
         "-pix_fmt", "yuv420p", "-vf", "scale=940:-2", str(mp4)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(webm), "-vf",
         "fps=10,scale=760:-1:flags=lanczos,palettegen", str(palette)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(webm), "-i", str(palette), "-lavfi",
         "fps=10,scale=760:-1:flags=lanczos[x];[x][1:v]paletteuse", str(gif)],
        check=True, capture_output=True,
    )
    palette.unlink(missing_ok=True)
    player.unlink(missing_ok=True)

    gif_mb = gif.stat().st_size / 1e6
    print(f"record_demo: wrote demo.gif ({gif_mb:.1f} MB), demo.mp4, manifest.json")
    if gif_mb > 5:
        print("record_demo: warning, GIF exceeds 5 MB; consider fewer frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
