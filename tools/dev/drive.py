"""Step-by-step driver for capturing the DormLink report screenshots.

Unlike capture.py this script is tailored to this app: it resets to factory state first,
scrolls when a control is below the fold, waits out toasts, and prints the on-screen text
after every step so the result can be verified without looking at the pictures.
"""
from __future__ import annotations

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
CACHE = os.path.join(ROOT, "docs", ".cache")
TMP = os.path.join(ROOT, "docs", ".cache")
PKG = "com.zhaoshuo.dormlink"
W, H = 1260, 2720
TAB_Y = 2625
TABS = {"dashboard": 157, "rules": 472, "logs": 787, "scenarios": 1102}


def hdc(*args: str, timeout: int = 90) -> str:
    try:
        p = subprocess.run([HDC] + list(args), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "(timeout)"


def dump() -> list[dict]:
    os.makedirs(TMP, exist_ok=True)
    local = os.path.join(TMP, "l.json")
    hdc("shell", "rm", "-f", "/data/local/tmp/l.json")
    hdc("shell", "uitest", "dumpLayout", "-p", "/data/local/tmp/l.json")
    hdc("file", "recv", "/data/local/tmp/l.json", local)
    if not os.path.exists(local):
        return []
    try:
        data = json.load(open(local, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    nodes: list[dict] = []

    def walk(n: dict) -> None:
        a = n.get("attributes", {})
        text = (a.get("text") or "").strip()
        bounds = a.get("bounds") or ""
        if text and bounds:
            nums = [int(v) for v in re.findall(r"-?\d+", str(bounds))]
            if len(nums) == 4:
                nodes.append({"text": text, "b": nums})
        for c in n.get("children", []) or []:
            walk(c)

    walk(data)
    return nodes


def show(nodes: list[dict], label: str, limit: int = 12) -> None:
    print(f"  [{label}] " + " | ".join(n["text"][:20] for n in nodes[:limit]))


def find(nodes: list[dict], *keywords: str):
    for kw in keywords:
        for n in nodes:
            if n["text"] == kw:
                x1, y1, x2, y2 = n["b"]
                return ((x1 + x2) // 2, (y1 + y2) // 2)
    for kw in keywords:
        for n in nodes:
            if kw in n["text"]:
                x1, y1, x2, y2 = n["b"]
                return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None


def tap(x: int, y: int, settle: float = 1.5) -> None:
    hdc("shell", "uitest", "uiInput", "click", str(x), str(y))
    time.sleep(settle)


def tap_text(nodes: list[dict], *keywords: str, settle: float = 1.5) -> bool:
    hit = find(nodes, *keywords)
    if not hit:
        print(f"    ! not found: {keywords}")
        return False
    print(f"    tap {keywords[0]} @ {hit}")
    tap(hit[0], hit[1], settle)
    return True


def swipe_up(times: int = 1) -> None:
    for _ in range(times):
        hdc("shell", "uitest", "uiInput", "swipe", "630", "2200", "630", "900", "400")
        time.sleep(1.2)


def tab(name: str) -> None:
    tap(TABS[name], TAB_Y, 2.0)


def shot(name: str) -> None:
    remote = f"/data/local/tmp/{name}.jpeg"
    hdc("shell", "rm", "-f", remote)
    hdc("shell", "snapshot_display", "-f", remote)
    jpg = os.path.join(TMP, f"{name}.jpeg")
    hdc("file", "recv", remote, jpg)
    if not os.path.exists(jpg):
        print(f"  ! shot failed: {name}")
        return
    from PIL import Image
    with Image.open(jpg) as img:
        img.save(os.path.join(OUT, f"{name}.png"))
        size = img.size
    os.remove(jpg)
    nodes = dump()
    with open(os.path.join(OUT, f"{name}.layout.txt"), "w", encoding="utf-8") as fh:
        for n in nodes:
            fh.write(f"{n['text']}\t{n['b']}\n")
    print(f"  shot {name}.png {size} | {len(nodes)} text nodes")


def restart_app(wait: float = 9.0) -> None:
    hdc("shell", "aa", "force-stop", PKG)
    time.sleep(2)
    hdc("shell", "aa", "start", "-a", "EntryAbility", "-b", PKG)
    time.sleep(wait)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    print("== 0. restart app to a known state")
    restart_app()
    nodes = dump()
    show(nodes, "dashboard")

    print("== 1. factory reset so the dashboard shows default values")
    if tap_text(nodes, "恢复出厂", settle=1.5):
        nodes = dump()
        show(nodes, "dialog")
        tap_text(nodes, "恢复", settle=3.0)
    nodes = dump()
    show(nodes, "after reset", 16)
    shot("01-dashboard")

    print("== 2. rules list")
    tab("rules")
    nodes = dump()
    show(nodes, "rules")
    shot("02-rules")

    print("== 3. editor + validation (save with empty name, then scroll to the error block)")
    if tap_text(nodes, "新建", settle=2.5):
        nodes = dump()
        show(nodes, "editor")
        tap_text(nodes, "保存", settle=2.0)          # header save -> triggers validation
        swipe_up(2)                                   # bring the red error block into view
        nodes = dump()
        show(nodes, "editor after save", 20)
        shot("03-rule-editor")
        tap_text(nodes, "← 返回", "返回", settle=2.0)

    print("== 4. scenario run then back to dashboard for the result card")
    tab("scenarios")
    nodes = dump()
    show(nodes, "scenarios")
    tap_text(nodes, "一键演练", settle=4.0)           # toast needs ~3s to clear
    tab("dashboard")
    time.sleep(1.5)
    nodes = dump()
    show(nodes, "dashboard after run", 18)
    shot("04-scenario-result")

    print("== 5. logs")
    tab("logs")
    time.sleep(1.5)
    nodes = dump()
    show(nodes, "logs", 18)
    shot("05-logs")

    print("== 6. persistence: capture, kill process, relaunch, capture again")
    tab("dashboard")
    time.sleep(1.5)
    shot("06-restore-before")
    hdc("shell", "aa", "force-stop", PKG)
    time.sleep(2)
    hdc("shell", "aa", "start", "-a", "EntryAbility", "-b", PKG)
    time.sleep(9)
    nodes = dump()
    show(nodes, "after restart", 18)
    shot("07-restore-after")

    print("done")


if __name__ == "__main__":
    main()
