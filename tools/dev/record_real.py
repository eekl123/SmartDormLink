"""Record a genuine screen video of the running DormLink app.

The emulator image ships no `screenrecord`, so the recording is produced from real device
frames: four capture streams run in parallel on the device (about 40 frames per second in
total) while this script drives the UI with uitest. Every frame carries the millisecond it
was grabbed in its file name, so the braked, uneven stream is resampled back onto a uniform
30 fps timeline instead of being replayed at whatever rate it happened to come in.

Run with the emulator up and the app installed:
    python tools/dev/record_real.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

HDC = r"E:\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
FFMPEG = r"D:\Proteus 8 Professional\BIN\ffmpeg.exe"


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(ROOT, "docs", ".cache")
FRAMES = os.path.join(CACHE, "frames")
SEQ = os.path.join(CACHE, "seq")
OUT = os.path.join(ROOT, "docs", "demo.mp4")
LOG = os.path.join(ROOT, "docs", "evidence", "recording-driver-log.txt")

PKG = "com.zhaoshuo.dormlink"
STREAMS = 4
FPS = 30

TABS = {"dashboard": (157, 2625), "rules": (472, 2625), "logs": (787, 2625), "scenarios": (1102, 2625)}

_t0 = time.time()
_log_lines: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.time() - _t0:6.2f}s] {msg}"
    print(line)
    _log_lines.append(line)


def hdc(*args: str, timeout: int = 120) -> str:
    try:
        p = subprocess.run([HDC] + list(args), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return "(timeout)"


def tap(x: int, y: int, wait: float = 1.0) -> None:
    log(f"tap ({x},{y})")
    hdc("shell", "uitest", "uiInput", "click", str(x), str(y))
    time.sleep(wait)


def swipe(x1: int, y1: int, x2: int, y2: int, ms: int = 800, wait: float = 1.0) -> None:
    log(f"swipe ({x1},{y1})->({x2},{y2}) {ms}ms")
    hdc("shell", "uitest", "uiInput", "swipe", str(x1), str(y1), str(x2), str(y2), str(ms))
    time.sleep(wait)


def texts() -> list[dict]:
    local = os.path.join(CACHE, "live.json")
    hdc("shell", "rm", "-f", "/data/local/tmp/live.json")
    hdc("shell", "uitest", "dumpLayout", "-p", "/data/local/tmp/live.json")
    hdc("file", "recv", "/data/local/tmp/live.json", local)
    if not os.path.exists(local):
        return []
    try:
        data = json.load(open(local, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    found: list[dict] = []

    def walk(n: dict) -> None:
        a = n.get("attributes", {})
        text = (a.get("text") or "").strip()
        bounds = a.get("bounds") or ""
        if text and bounds:
            nums = [int(v) for v in re.findall(r"-?\d+", str(bounds))]
            if len(nums) == 4:
                found.append({"text": text, "b": nums})
        for c in n.get("children", []) or []:
            walk(c)

    walk(data)
    return found


def find(nodes: list[dict], *keywords: str) -> tuple[int, int] | None:
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


def tap_text(*keywords: str, wait: float = 1.2) -> bool:
    hit = find(texts(), *keywords)
    if not hit:
        log(f"  ! 未找到控件 {keywords}")
        return False
    tap(hit[0], hit[1], wait)
    return True


def launch(wait: float = 8.0) -> None:
    hdc("shell", "aa", "force-stop", PKG)
    time.sleep(1.5)
    hdc("shell", "aa", "start", "-a", "EntryAbility", "-b", PKG)
    time.sleep(wait)


def start_capture() -> subprocess.Popen:
    # hdc quotes every argv element it forwards, so compound commands must be one string.
    hdc("shell", "rm -rf /data/local/tmp/frames /data/local/tmp/stop")
    hdc("shell", "mkdir -p /data/local/tmp/frames")
    hdc("file", "send", os.path.join(HERE, "capture_stream.sh"), "/data/local/tmp/cap.sh")
    hdc("shell", "chmod 755 /data/local/tmp/cap.sh")
    cmd = " ".join([f"/data/local/tmp/cap.sh {i} &" for i in range(1, STREAMS + 1)]) + " wait"
    log(f"启动 {STREAMS} 路连拍")
    proc = subprocess.Popen([HDC, "shell", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3.0)
    growing = hdc("shell", "ls /data/local/tmp/frames | wc -l").strip()
    log(f"  3 秒内已写入 {growing} 帧")
    if not growing.isdigit() or int(growing) < 20:
        log("  ! 连拍没有正常启动，重试一次")
        hdc("shell", "rm -rf /data/local/tmp/frames")
        hdc("shell", "mkdir -p /data/local/tmp/frames")
        proc = subprocess.Popen([HDC, "shell", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3.0)
        log("  重试后帧数 " + hdc("shell", "ls /data/local/tmp/frames | wc -l").strip())
    return proc


def stop_capture(proc: subprocess.Popen) -> None:
    hdc("shell", "touch", "/data/local/tmp/stop")
    try:
        proc.wait(timeout=40)
    except subprocess.TimeoutExpired:
        proc.kill()
    hdc("shell", "rm", "-f", "/data/local/tmp/stop")
    count = hdc("shell", "ls /data/local/tmp/frames | wc -l").strip()
    per_stream = hdc("shell", "ls /data/local/tmp/frames | cut -d_ -f1 | sort | uniq -c").strip()
    first_last = hdc("shell", "ls /data/local/tmp/frames | sort | head -1; ls /data/local/tmp/frames | sort | tail -1").strip()
    log(f"停止连拍，设备端帧数 {count}")
    log("  每路帧数: " + " ".join(per_stream.split()))
    log("  首末帧: " + " / ".join(first_last.split()))


def pull_frames() -> list[str]:
    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES)
    log("回传帧")
    hdc("file", "recv", "/data/local/tmp/frames", CACHE, timeout=600)
    files = glob.glob(os.path.join(FRAMES, "s*_*_*.jpeg"))
    log(f"本地帧数 {len(files)}")
    return files


def ts_of(path: str) -> int:
    m = re.search(r"_(\d{10,})_\d+\.jpeg$", os.path.basename(path))
    return int(m.group(1)) if m else 0


def build_video(files: list[str]) -> None:
    files = sorted(files, key=ts_of)
    if len(files) < 30:
        raise SystemExit("帧数太少，放弃合成")
    t_first, t_last = ts_of(files[0]), ts_of(files[-1])
    span = (t_last - t_first) / 1000.0
    log(f"原始帧 {len(files)} 张，跨度 {span:.2f}s，平均 {len(files) / span:.1f} fps")

    if os.path.isdir(SEQ):
        shutil.rmtree(SEQ)
    os.makedirs(SEQ)
    total = int(span * FPS)
    j = 0
    for k in range(total):
        target = t_first + k * 1000.0 / FPS
        while j + 1 < len(files) and abs(ts_of(files[j + 1]) - target) <= abs(ts_of(files[j]) - target):
            j += 1
        os.link(files[j], os.path.join(SEQ, f"{k:05d}.jpg"))
    log(f"重采样到 {FPS}fps，共 {total} 帧")

    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-framerate", str(FPS), "-i", os.path.join(SEQ, "%05d.jpg"),
        "-vf", "scale=630:1360:flags=lanczos,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", "24",
        "-movflags", "+faststart", OUT,
    ]
    subprocess.run(cmd, check=True)
    size = os.path.getsize(OUT) / 1024 / 1024
    log(f"输出 {OUT} ({size:.2f} MB)")
    info = subprocess.run([FFMPEG, "-i", OUT], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stderr
    for line in info.splitlines():
        if "Duration" in line or "Stream #0:0" in line:
            log("  " + line.strip())


def walkthrough() -> None:
    log("== 1 驾驶舱：拖动温度与湿度")
    tap(*TABS["dashboard"], wait=1.6)
    log("  当前界面: " + " | ".join(n["text"][:12] for n in texts()[:10]))
    swipe(360, 291, 560, 291, 900, wait=1.2)
    swipe(340, 490, 560, 490, 900, wait=1.2)

    log("== 2 执行一次联动")
    tap(630, 881, wait=2.6)

    log("== 3 手动调高书桌灯亮度")
    swipe(200, 1518, 470, 1518, 900, wait=1.4)

    log("== 4 场景页：深夜自习一键演练")
    tap(*TABS["scenarios"], wait=2.0)
    tap(630, 1088, wait=4.0)
    log("  演练后: " + " | ".join(n["text"][:12] for n in texts()[:10]))

    log("== 5 回驾驶舱查看联动结果")
    tap(*TABS["dashboard"], wait=2.4)

    log("== 6 规则页：新建规则并触发校验")
    tap(*TABS["rules"], wait=2.0)
    swipe(630, 2100, 630, 1300, 600, wait=1.4)
    tap(1120, 347, wait=2.6)
    if not tap_text("保存", "完成", wait=2.4):
        log("  编辑器保存入口未找到，跳过")
    swipe(630, 2100, 630, 1200, 600, wait=1.0)
    swipe(630, 2100, 630, 1200, 600, wait=1.4)
    tap_text("← 返回", "返回", wait=2.2)

    log("== 7 日志页：执行记录与冲突说明")
    tap(*TABS["logs"], wait=2.4)
    swipe(630, 2100, 630, 1400, 600, wait=1.6)

    log("== 8 结束进程后重启，验证恢复")
    tap(*TABS["dashboard"], wait=2.0)
    launch(wait=9.0)
    log("  重启后: " + " | ".join(n["text"][:12] for n in texts()[:10]))
    time.sleep(2.0)


def main() -> None:
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

    log("准备：冷启动应用到驾驶舱")
    launch(wait=8.0)

    proc = start_capture()
    time.sleep(2.0)
    try:
        walkthrough()
    finally:
        stop_capture(proc)

    files = pull_frames()
    build_video(files)
    hdc("shell", "rm", "-rf", "/data/local/tmp/frames")

    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_log_lines) + "\n")
    log(f"驱动日志已写入 {LOG}")


if __name__ == "__main__":
    sys.exit(main())
