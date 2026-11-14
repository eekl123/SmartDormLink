"""Short scripted demo used while screen recording is running (approx. 45 s)."""
from __future__ import annotations

import time

from capture import TABS, TAB_Y, hdc, tap, dump, shot

PKG = "com.zhaoshuo.dormlink"


def tab(name: str, settle: float = 2.5) -> None:
    tap(TABS[name], TAB_Y, settle)


def main() -> None:
    print("restart app")
    hdc("shell", "aa", "force-stop", PKG)
    time.sleep(2)
    hdc("shell", "aa", "start", "-a", "EntryAbility", "-b", PKG)
    time.sleep(8)

    print("dashboard")
    time.sleep(3)
    nodes = dump()
    print("  ", " | ".join(n["text"][:16] for n in nodes[:8]))

    print("scenario tab + run")
    tab("scenarios")
    nodes = dump()
    for n in nodes:
        if n["text"] == "一键演练":
            x1, y1, x2, y2 = n["b"]
            tap((x1 + x2) // 2, (y1 + y2) // 2, 5.0)
            break
    tab("dashboard")          # show the result card and device changes
    time.sleep(3)

    print("logs")
    tab("logs", 3.5)
    time.sleep(2)

    print("rules")
    tab("rules", 3.5)
    time.sleep(2)

    print("back to dashboard")
    tab("dashboard", 3.0)
    time.sleep(2)
    print("demo finished")


if __name__ == "__main__":
    main()
