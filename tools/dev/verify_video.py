"""校验 docs/demo.mp4 是真实交互录屏而非拼接的静态图。

思路：按 1fps 抽帧，统计相邻帧差异（有变化才算"真的在动"），
再把最后一帧与设备当下的实时截图做相关性比对（同一台设备、同一界面才算通过）。
"""
from __future__ import annotations

import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
VIDEO = os.path.join(ROOT, "docs", "demo.mp4")
WORK = r"C:\dsh_build\videocheck"
FFMPEG = r"D:\Proteus 8 Professional\BIN\ffmpeg.exe"
HDC = r"E:\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    for name in os.listdir(WORK):
        os.remove(os.path.join(WORK, name))

    # 1. 每秒抽一帧
    run([FFMPEG, "-y", "-i", VIDEO, "-vf", "fps=1", "-q:v", "2",
         os.path.join(WORK, "v_%03d.jpg")])
    frames = sorted(os.listdir(WORK))
    print(f"抽帧 {len(frames)} 张")

    imgs = [cv2.imread(os.path.join(WORK, f), cv2.IMREAD_GRAYSCALE) for f in frames]
    h, w = imgs[0].shape
    print(f"分辨率 {w}x{h}")

    # 2. 相邻帧差异：静态画面差异应接近 0，滑动/切页差异明显
    diffs = [float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))))
             for a, b in zip(imgs, imgs[1:])]
    moved = sum(1 for d in diffs if d > 1.0)
    jumps = [i + 1 for i, d in enumerate(diffs) if d > 12.0]
    print(f"有变化的秒数 {moved}/{len(diffs)}，平均差异 {np.mean(diffs):.2f}，最大 {max(diffs):.2f}")
    print(f"疑似整页切换的时间点 {jumps}")

    # 3. 唯一画面数：避免"同一张图循环"的假录屏
    gray = np.stack(imgs).reshape(len(imgs), -1).astype(np.float32)
    gray -= gray.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(gray, axis=1, keepdims=True) + 1e-6
    corr = (gray / norms) @ (gray / norms).T
    near_dup = int(np.sum(corr > 0.995)) - len(imgs)
    print(f"高度相似（>0.995）的帧对数 {max(near_dup, 0)}")

    # 4. 与设备实时画面比对
    remote, local = "/data/local/tmp/now.jpeg", os.path.join(WORK, "now.jpeg")
    subprocess.run([HDC, "shell", f"snapshot_display -f {remote}"],
                   capture_output=True, text=True)
    subprocess.run([HDC, "file", "recv", remote, local], capture_output=True, text=True)
    last = cv2.imread(os.path.join(WORK, frames[-1]), cv2.IMREAD_GRAYSCALE)
    now = cv2.imread(local, cv2.IMREAD_GRAYSCALE)
    if now is None:
        print("! 拿不到设备实时截图")
        return 1
    now = cv2.resize(now, (last.shape[1], last.shape[0]))
    a = last.astype(np.float32) - last.mean()
    b = now.astype(np.float32) - now.mean()
    r = float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-6))
    print(f"末帧 vs 设备当前画面 相关系数 {r:.4f}")
    print("结论：" + ("真实录屏（画面持续变化且与设备实时画面一致）" if moved > 40 and r > 0.8
                     else "存疑，需要人工复核"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
