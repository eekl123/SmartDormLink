"""Drive the DormLink app on a HarmonyOS device/emulator through hdc and capture the
report screenshots automatically.

Usage (after the app has been installed and launched once via DevEco "Run"):
    python tools/dev/capture.py --probe          # check device + screen size only
    python tools/dev/capture.py --all            # capture 01..05
    python tools/dev/capture.py --restore        # capture 06 (before) / 07 (after restart)
    python tools/dev/capture.py --record 60      # record demo.mp4

The script prefers locating widgets by their text via `uitest dumpLayout`, and falls back
to geometry derived from the real screenshot size when the dump is unavailable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

HDC = r"E:\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "docs", "images")
REMOTE = "/data/local/tmp"


def run(args: list[str], timeout: int = 60) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "(timeout)"


def hdc(*args: str, timeout: int = 60) -> str:
    return run([HDC] + list(args), timeout)


def device() -> str | None:
    out = hdc("list", "targets")
    for line in out.splitlines():
        line = line.strip()
        if line and "Empty" not in line and not line.startswith("["):
            return line
    return None


def shot(name: str) -> bool:
    remote = f"{REMOTE}/{name}.jpeg"
    hdc("shell", "rm", "-f", remote)
    hdc("shell", "snapshot_display", "-f", remote, timeout=90)
    local = os.path.join(OUT, f"{name}.png")
    os.makedirs(OUT, exist_ok=True)
    # pull as jpeg first, convert to png for uniform naming
    tmp = os.path.join(OUT, f"_{name}.jpeg")
    out = hdc("file", "recv", remote, tmp, timeout=90)
    if not os.path.exists(tmp):
        print(f"  ! snapshot failed: {out.strip()[:160]}")
        return False
    try:
        from PIL import Image
        img = Image.open(tmp)
        img.save(local)
        img.close()
        os.remove(tmp)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! convert failed: {exc}")
        return False
    print(f"  shot -> {local} ({os.path.getsize(local) // 1024} KB)")
    # companion text dump: proves what the screenshot actually shows
    nodes = dump_layout()
    if nodes:
        side = os.path.join(OUT, f"{name}.layout.txt")
        with open(side, "w", encoding="utf-8") as fh:
            for n in nodes:
                fh.write(f"{n['text']}\t{n['bounds']}\n")
        print(f"  text -> {side} ({len(nodes)} nodes)")
    return True


def screen_size() -> tuple[int, int]:
    """Read the real resolution from a screenshot."""
    probe = os.path.join(OUT, "_probe.jpeg")
    hdc("shell", "rm", "-f", f"{REMOTE}/_probe.jpeg")
    hdc("shell", "snapshot_display", "-f", f"{REMOTE}/_probe.jpeg", timeout=90)
    hdc("file", "recv", f"{REMOTE}/_probe.jpeg", probe, timeout=90)
    try:
        from PIL import Image
        with Image.open(probe) as img:
            size = img.size
        os.remove(probe)
        return size
    except Exception:  # noqa: BLE001
        return (1260, 2720)


def tap(x: int, y: int) -> None:
    hdc("shell", "uitest", "uiInput", "click", str(x), str(y))
    time.sleep(1.2)


def dump_layout() -> list[dict]:
    remote = f"{REMOTE}/layout.json"
    local = os.path.join(OUT, "_layout.json")
    hdc("shell", "rm", "-f", remote)
    hdc("shell", "uitest", "dumpLayout", "-p", remote, timeout=90)
    hdc("file", "recv", remote, local, timeout=90)
    if not os.path.exists(local):
        return []
    try:
        with open(local, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        return []
    nodes: list[dict] = []

    def walk(n: dict) -> None:
        text = n.get("attributes", {}).get("text") or n.get("text")
        bounds = n.get("attributes", {}).get("bounds") or n.get("bounds")
        if text and bounds:
            nums = [int(v) for v in re.findall(r"-?\d+", str(bounds))]
            if len(nums) == 4:
                nodes.append({"text": text.strip(), "bounds": nums})
        for child in n.get("children", []) or []:
            walk(child)

    walk(data if isinstance(data, dict) else {})
    return nodes


def find_center(nodes: list[dict], *keywords: str) -> tuple[int, int] | None:
    for kw in keywords:
        for n in nodes:
            if kw in n["text"]:
                x1, y1, x2, y2 = n["bounds"]
                return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None


def tab_points(w: int, h: int) -> dict[str, tuple[int, int]]:
    """Bottom tab bar: 4 equal slots, ~26dp above the bottom edge."""
    y = h - int(h * 0.035)
    return {
        "dashboard": (w // 8, y),
        "rules": (w * 3 // 8, y),
        "logs": (w * 5 // 8, y),
        "scenarios": (w * 7 // 8, y),
    }


def probe() -> None:
    dev = device()
    print("device:", dev or "(none)")
    if not dev:
        sys.exit(2)
    w, h = screen_size()
    print("screen:", w, "x", h)
    nodes = dump_layout()
    print("layout nodes with text:", len(nodes))
    for n in nodes[:25]:
        print("   ", n["text"][:24], n["bounds"])
    print("tab points:", tab_points(w, h))


def go_tab(name: str, w: int, h: int, nodes: list[dict]) -> None:
    labels = {"dashboard": ("驾驶舱",), "rules": ("规则",), "logs": ("日志",), "scenarios": ("场景",)}
    hit = find_center(nodes, *labels[name])
    if hit:
        tap(*hit)
    else:
        tap(*tab_points(w, h)[name])


def capture_all() -> None:
    w, h = screen_size()
    print("screen:", w, "x", h)
    nodes = dump_layout()
    go_tab("dashboard", w, h, nodes)

    print("[1/5] dashboard")
    shot("01-dashboard")

    print("[2/5] rules list")
    nodes = dump_layout()
    go_tab("rules", w, h, nodes)
    nodes = dump_layout()
    shot("02-rules")

    print("[3/5] rule editor validation")
    new_btn = find_center(nodes, "新建")
    if new_btn:
        tap(*new_btn)
        time.sleep(2)
        nodes = dump_layout()
        save_btn = find_center(nodes, "创建规则", "保存修改")
        if save_btn:
            tap(*save_btn)
            time.sleep(1.5)
        shot("03-rule-editor")
        back = find_center(nodes, "← 返回", "返回")
        if back:
            tap(*back)
        else:
            hdc("shell", "uitest", "uiInput", "keyEvent", "Back")
    else:
        print("  ! 新建 button not found, skipped")

    print("[4/5] scenario run")
    nodes = dump_layout()
    go_tab("scenarios", w, h, nodes)
    nodes = dump_layout()
    run_btn = find_center(nodes, "一键演练")
    if run_btn:
        tap(*run_btn)
        time.sleep(3)
    shot("04-scenario-result")

    print("[5/5] logs")
    nodes = dump_layout()
    go_tab("logs", w, h, nodes)
    time.sleep(1.5)
    shot("05-logs")


def capture_restore() -> None:
    w, h = screen_size()
    nodes = dump_layout()
    go_tab("dashboard", w, h, nodes)
    time.sleep(1)
    print("before restart")
    shot("06-restore-before")
    pkg = "com.zhaoshuo.dormlink"
    print("force-stop", pkg)
    hdc("shell", "aa", "force-stop", pkg)
    time.sleep(2)
    print("relaunch")
    hdc("shell", "aa", "start", "-a", "EntryAbility", "-b", pkg, timeout=60)
    time.sleep(8)
    shot("07-restore-after")


def record(seconds: int) -> None:
    remote = f"{REMOTE}/demo.mp4"
    hdc("shell", "rm", "-f", remote)
    print(f"recording {seconds}s ...")
    hdc("shell", "screenrecord", "--time", str(seconds), remote, timeout=seconds + 120)
    local = os.path.join(ROOT, "docs", "demo.mp4")
    out = hdc("file", "recv", remote, local, timeout=180)
    if os.path.exists(local):
        print("video ->", local, os.path.getsize(local) // 1024, "KB")
    else:
        print("record failed:", out.strip()[:200])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--record", type=int, default=0)
    args = ap.parse_args()

    if not device():
        print("no device. start an emulator or connect a phone with USB debugging.")
        sys.exit(2)
    if args.probe:
        probe()
    if args.all:
        capture_all()
    if args.restore:
        capture_restore()
    if args.record:
        record(args.record)
