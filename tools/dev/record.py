"""Record a demo video of the running app.

The emulator image has no `screenrecord`, and its window is not composited on this
session's desktop, so the video is assembled from real device frames captured with
`hdc shell snapshot_display` while a script drives the UI, then encoded with ffmpeg.

Output: docs/demo.mp4 (and docs/video_frames/ with the raw frames, git-ignored).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time

HDC = r"E:\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
FFMPEG = r"D:\Proteus 8 Professional\BIN\ffmpeg.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FRAMES = os.path.join(ROOT, "docs", "video_frames")
OUT = os.path.join(ROOT, "docs", "demo.mp4")
PKG = "com.zhaoshuo.dormlink"
TAB_Y = 2625
TABS = {"dashboard": 157, "rules": 472, "logs": 787, "scenarios": 1102}


def hdc(*args: str, timeout: int = 60) -> str:
    try:
        p = subprocess.run([HDC] + list(args), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return ""


def tap(x: int, y: int, settle: float = 1.6) -> None:
    hdc("shell", "uitest", "uiInput", "click", str(x), str(y))
    time.sleep(settle)


def tab(name: str, settle: float = 2.2) -> None:
    tap(TABS[name], TAB_Y, settle)


def tap_text(keyword: str, settle: float = 2.0) -> bool:
    import json
    import re
    hdc("shell", "uitest", "dumpLayout", "-p", "/data/local/tmp/l.json")
    local = os.path.join(FRAMES, "_l.json")
    hdc("file", "recv", "/data/local/tmp/l.json", local)
    try:
        data = json.load(open(local, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    found = None

    def walk(n: dict) -> None:
        nonlocal found
        a = n.get("attributes", {})
        text = (a.get("text") or "").strip()
        if text == keyword and a.get("bounds"):
            nums = [int(v) for v in re.findall(r"-?\d+", str(a["bounds"]))]
            if len(nums) == 4:
                found = ((nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2)
        for c in n.get("children", []) or []:
            walk(c)

    walk(data)
    if found:
        tap(found[0], found[1], settle)
        return True
    return False


def main() -> None:
    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES, exist_ok=True)

    stop = threading.Event()
    counter = {"n": 0}

    def capture_loop() -> None:
        while not stop.is_set():
            remote = "/data/local/tmp/_frame.jpeg"
            hdc("shell", "rm", "-f", remote, timeout=20)
            hdc("shell", "snapshot_display", "-f", remote, timeout=30)
            local = os.path.join(FRAMES, f"frame_{counter['n']:04d}.jpeg")
            hdc("file", "recv", remote, local, timeout=30)
            counter["n"] += 1

    print("restart app")
    hdc("shell", "aa", "force-stop", PKG)
    time.sleep(2)
    hdc("shell", "aa", "start", "-a", "EntryAbility", "-b", PKG)
    time.sleep(9)

    thread = threading.Thread(target=capture_loop, daemon=True)
    thread.start()

    print("demo: dashboard")
    time.sleep(4)
    print("demo: scenario tab")
    tab("scenarios", 3.0)
    print("demo: run scenario")
    tap_text("一键演练", 3.0)
    print("demo: dashboard with result")
    tab("dashboard", 3.5)
    print("demo: logs")
    tab("logs", 4.0)
    print("demo: rules")
    tab("rules", 4.0)
    print("demo: open editor")
    tap_text("新建", 3.0)
    tap_text("保存", 2.5)       # triggers validation
    time.sleep(2)
    print("demo: back")
    tap_text("← 返回", 2.5)
    print("demo: done")

    stop.set()
    thread.join(timeout=10)

    frames = sorted(f for f in os.listdir(FRAMES) if f.startswith("frame_"))
    print(f"frames captured: {len(frames)}")

    if not frames:
        print("no frames, abort")
        return

    fps = max(2, min(6, round(len(frames) / 24)))  # spread frames over about 24 seconds
    cmd = [FFMPEG, "-y", "-framerate", str(fps),
           "-i", os.path.join(FRAMES, "frame_%04d.jpeg"),
           "-vf", "scale=630:-2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", OUT]
    print(" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-800:])
        return
    print("video:", OUT, round(os.path.getsize(OUT) / 1024, 1), "KB", "| fps:", fps)


if __name__ == "__main__":
    main()
