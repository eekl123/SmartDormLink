"""Generate the architecture and rule-execution diagrams used by README and the report.

The drawing code measures every string and shrinks/wraps it until it fits its box,
so the output stays readable without manual pixel tweaking.

Run:  python tools/report/make_diagrams.py
Out:  docs/images/architecture.png, docs/images/rule_flow.png
"""
from __future__ import annotations

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT_DIR = os.path.join(ROOT, 'docs', 'images')

FONT_CANDIDATES = [
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\msyhbd.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
    r'C:\Windows\Fonts\simsun.ttc',
]

ACCENT = (47, 107, 255)
INK = (26, 29, 38)
SUB = (107, 114, 128)
LINE = (150, 158, 178)
RED = (229, 72, 77)
FILLS = {
    'ui': (232, 240, 255),
    'state': (235, 248, 245),
    'domain': (255, 246, 228),
    'data': (240, 237, 255),
    'store': (233, 236, 243),
    'test': (255, 240, 240),
}

_FONT_PATH = None
_CACHE: dict[int, ImageFont.FreeTypeFont] = {}


def font_path() -> str:
    global _FONT_PATH
    if _FONT_PATH:
        return _FONT_PATH
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            _FONT_PATH = path
            return path
    raise SystemExit('no CJK font found')


def load_font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _CACHE:
        _CACHE[size] = ImageFont.truetype(font_path(), size)
    return _CACHE[size]


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: float) -> list[str]:
    """Character-wise wrapping that also honours explicit newlines."""
    out: list[str] = []
    for raw in text.split('\n'):
        if not raw:
            out.append('')
            continue
        cur = ''
        for ch in raw:
            if draw.textlength(cur + ch, font=font) <= max_w or not cur:
                cur += ch
            else:
                out.append(cur)
                cur = ch
        out.append(cur)
    return out


def fit(draw: ImageDraw.ImageDraw, text: str, max_w: float, max_h: float,
        sizes=(24, 22, 21, 20, 19, 18, 17, 16, 15, 14)):
    """Pick the largest font size whose wrapped text fits the given area."""
    best = None
    for size in sizes:
        font = load_font(size)
        lines = wrap(draw, text, font, max_w)
        line_h = size + 5
        if line_h * len(lines) <= max_h:
            best = (font, lines, line_h)
            break
    if best is None:
        size = sizes[-1]
        font = load_font(size)
        lines = wrap(draw, text, font, max_w)
        best = (font, lines, size + 5)
    return best


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=LINE, radius=14, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(draw: ImageDraw.ImageDraw, box, text: str, color=INK, sizes=(24, 22, 21, 20, 19, 18, 17, 16, 15, 14)):
    x0, y0, x1, y1 = box
    max_w = (x1 - x0) - 16
    max_h = (y1 - y0) - 8
    font, lines, line_h = fit(draw, text, max_w, max_h, sizes)
    total = line_h * len(lines)
    y = y0 + ((y1 - y0) - total) / 2
    for line in lines:
        w = draw.textlength(line, font=font)
        draw.text((x0 + ((x1 - x0) - w) / 2, y), line, font=font, fill=color)
        y += line_h


def block(draw: ImageDraw.ImageDraw, xy, text: str, max_w: float, size: int = 17, color=SUB,
          spacing: int = 6):
    """Left-aligned wrapped paragraph."""
    font = load_font(size)
    x, y = xy
    for line in wrap(draw, text, font, max_w):
        draw.text((x, y), line, font=font, fill=color)
        y += size + spacing
    return y


def trim(img: Image.Image, margin: int = 50) -> Image.Image:
    """Crop the canvas to the drawn content so nothing is clipped at the edges."""
    from PIL import ImageChops
    bg = Image.new('RGB', img.size, 'white')
    bbox = ImageChops.difference(img.convert('RGB'), bg).getbbox()
    if bbox is None:
        return img
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - margin)
    y0 = max(0, y0 - margin)
    x1 = min(img.size[0], x1 + margin)
    y1 = min(img.size[1], y1 + margin)
    return img.crop((x0, y0, x1, y1))


def arrow(draw: ImageDraw.ImageDraw, start, end, color=LINE, width=3, head=13):
    draw.line([start, end], fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    p1 = (x2 - ux * head + px * head * 0.55, y2 - uy * head + py * head * 0.55)
    p2 = (x2 - ux * head - px * head * 0.55, y2 - uy * head - py * head * 0.55)
    draw.polygon([end, p1, p2], fill=color)


def architecture() -> str:
    W, H = 1720, 1200
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)

    d.text((60, 42), '智舍联动站（DormLink）系统架构图', font=load_font(34), fill=INK)
    d.text((60, 92), 'HarmonyOS 5.0.5 (API 17) · ArkTS + ArkUI Stage 模型 · 独立完成',
           font=load_font(19), fill=SUB)

    layers = [
        ('表现层（ArkUI 声明式 UI）', 'ui', [
            'pages/Index.ets\n驾驶舱 / 规则 / 日志 / 场景',
            'pages/RuleEditor.ets\n规则新建、编辑与校验',
            'components/*\nDeviceCard · EnvRow · RuleCard\nLogCard · ScenarioCard',
        ]),
        ('状态与编排层（ArkUI 状态管理）', 'state', [
            '@State snapshot\n整份业务快照',
            '@Prop 单向传参\n+ 回调上抛事件',
            'cloneSnapshot()\n整体替换以触发刷新',
        ]),
        ('领域层 DormLinkDomain.ts（纯 TypeScript，零系统依赖）', 'domain', [
            '数据模型\nDeviceState / EnvState\nRule / LogEntry',
            '规则引擎\n条件求值 · 优先级排序\n冲突裁决',
            '校验与编解码\nvalidateRule\ndump / parseSnapshot',
            '场景种子\nseedRules / seedScenarios',
        ]),
        ('数据访问层 DormLinkRepository.ets', 'data', [
            'Preferences\nsnapshot_v2 JSON 快照',
            'RDB\ntrigger_log 执行日志',
            '异常降级\ntry/catch → hilog → 种子数据',
        ]),
        ('本地存储', 'store', [
            'Preferences\ndormlink_prefs',
            'RDB\ndormlink.db',
            '进程重启后恢复\n设备 / 规则 / 环境 / 日志',
        ]),
    ]

    top = 150
    layer_h = 168
    left = 70
    width = 1180
    for idx, (title, key, boxes) in enumerate(layers):
        y0 = top + idx * (layer_h + 26)
        y1 = y0 + layer_h
        rounded(d, (left, y0, left + width, y1), FILLS[key], ACCENT, 18, 3)
        d.text((left + 24, y0 + 14), title, font=load_font(22), fill=INK)
        n = len(boxes)
        inner_w = (width - 48 - (n - 1) * 16) / n
        for bi, text in enumerate(boxes):
            bx0 = left + 24 + bi * (inner_w + 16)
            by0 = y0 + 58
            by1 = y1 - 16
            rounded(d, (bx0, by0, bx0 + inner_w, by1), 'white', LINE, 12, 2)
            center_text(d, (bx0 + 6, by0, bx0 + inner_w - 6, by1), text)

    for idx in range(len(layers) - 1):
        y1 = top + idx * (layer_h + 26) + layer_h
        y2 = top + (idx + 1) * (layer_h + 26)
        cx = left + width / 2
        arrow(d, (cx, y1 + 3), (cx, y2 - 3))
        d.text((cx + 14, (y1 + y2) / 2 - 14), '调用 / 数据流', font=load_font(16), fill=SUB)

    rx = left + width + 40
    rw = W - rx - 46
    rounded(d, (rx, top, rx + rw, top + 250), FILLS['test'], RED, 16, 3)
    d.text((rx + 18, top + 14), '测试与验证', font=load_font(22), fill=INK)
    block(d, (rx + 18, top + 58),
          'tools/tests/*.test.ts\nnode --test 直接 import 领域层\n36 条用例：正常 / 边界 / 异常\n\nentry/src/test/*.test.ets\nHypium 本地单测镜像（DevEco 运行）',
          rw - 36, 17, INK, 7)
    arrow(d, (rx - 4, top + 190), (left + width + 6, top + 300), color=RED, width=3)

    ay0 = top + 282
    rounded(d, (rx, ay0, rx + rw, ay0 + 132), 'white', ACCENT, 16, 3)
    d.text((rx + 18, ay0 + 14), '本人负责范围', font=load_font(22), fill=ACCENT)
    block(d, (rx + 18, ay0 + 54), '全部模块（独立完成）\n含集成、测试与交付', rw - 36, 17, INK, 7)

    ay1 = ay0 + 160
    rounded(d, (rx, ay1, rx + rw, ay1 + 230), (247, 249, 254), LINE, 16, 2)
    d.text((rx + 18, ay1 + 14), '典型数据流', font=load_font(22), fill=INK)
    block(d, (rx + 18, ay1 + 56),
          '滑块 onChange → applyMetric()\n→ 新 EnvState\n→ runEngine()\n→ 设备 / 规则 / 日志\n→ Preferences + RDB\n→ 日志 Tab 刷新',
          rw - 36, 16, SUB, 6)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, 'architecture.png')
    img.save(out)
    return out


def rule_flow() -> str:
    W, H = 1560, 2200
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)

    d.text((60, 42), '规则执行与冲突裁决流程图', font=load_font(34), fill=INK)
    d.text((60, 92), 'runEngine(input) → EngineOutcome：候选筛选 → 优先级排序 → 设备占用裁决 → 日志落库',
           font=load_font(19), fill=SUB)

    cx = 560
    bw, bh = 470, 76

    def box(y, text, fill=(232, 240, 255)):
        rounded(d, (cx - bw / 2, y, cx + bw / 2, y + bh), fill, ACCENT, 14, 2)
        center_text(d, (cx - bw / 2 + 8, y, cx + bw / 2 - 8, y + bh), text)
        return y + bh

    def diamond(y, text):
        h, w = 120, 390
        pts = [(cx, y), (cx + w / 2, y + h / 2), (cx, y + h), (cx - w / 2, y + h / 2)]
        d.polygon(pts, fill=(255, 246, 228), outline=ACCENT, width=3)
        center_text(d, (cx - w / 2 + 26, y + 16, cx + w / 2 - 26, y + h - 16), text, sizes=(19, 18, 17, 16, 15))
        return y + h

    def side_note(y_mid, text):
        d.text((cx + 205, y_mid - 26), text, font=load_font(16), fill=SUB)

    y = 150
    y = box(y, '开始：读取 Preferences 快照 + RDB 历史日志', (233, 236, 243))
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, '用户拖动环境滑块 / 套用场景 / 点击「执行一次联动」')
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, '遍历每条规则', (235, 248, 245))
    arrow(d, (cx, y + 2), (cx, y + 22))

    y = diamond(y + 24, '规则已启用？')
    side_note(y - 86, '否 → 跳过并计数')
    arrow(d, (cx + 195, y - 60), (cx + 330, y - 60))
    arrow(d, (cx, y + 2), (cx, y + 22))

    y = diamond(y + 24, '全部条件满足？\n（且 / 或 组合）')
    side_note(y - 86, '否 → 跳过并计数')
    arrow(d, (cx + 195, y - 60), (cx + 330, y - 60))
    arrow(d, (cx, y + 2), (cx, y + 22))

    y = diamond(y + 24, '冷却期已结束？')
    side_note(y - 86, '否 → 跳过并计数')
    arrow(d, (cx + 195, y - 60), (cx + 330, y - 60))
    arrow(d, (cx, y + 2), (cx, y + 22))

    y = box(y + 24, '加入候选集', (235, 248, 245))
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, '候选排序：priority 降序 → 规则 ID 升序', (240, 237, 255))
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, '按序取出规则，逐个执行其设备动作')
    arrow(d, (cx, y + 2), (cx, y + 22))

    y = diamond(y + 24, '目标设备已被占用？')
    side_note(y - 86, '是 → 丢弃该动作')
    d.text((cx + 205, y - 60), '并生成 ConflictNote', font=load_font(16), fill=SUB)
    arrow(d, (cx + 195, y - 60), (cx + 330, y - 60))
    arrow(d, (cx, y + 2), (cx, y + 22))

    y = box(y + 24, '写入设备状态（level 裁剪到 0-100）')
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, '生成日志：序号 · 触发条件 · 设备变化 · 冲突说明')
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, '汇总：命中 / 跳过 / 冲突', (235, 248, 245))
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, 'Preferences 保存快照 + RDB 写入日志', (240, 237, 255))
    arrow(d, (cx, y + 2), (cx, y + 26))
    y = box(y + 28, '界面刷新：设备卡片 / 结果卡 / 日志列表', (233, 236, 243))

    nx = 940
    nw = W - nx - 50
    rounded(d, (nx, 400, nx + nw, 620), (255, 240, 240), RED, 14, 2)
    d.text((nx + 18, 416), '异常与边界（已被单测覆盖）', font=load_font(20), fill=INK)
    block(d, (nx + 18, 456),
          '· 动作目标设备不存在 → 跳过并留痕\n· 环境值为 NaN → 条件判 false\n· level 越界 → 裁剪到 0-100\n· 零条件规则 → 不触发\n· 快照损坏 / 版本过新 → 回退种子数据',
          nw - 36, 16, INK, 7)

    rounded(d, (nx, 660, nx + nw, 830), 'white', ACCENT, 14, 2)
    d.text((nx + 18, 676), '实现位置', font=load_font(20), fill=ACCENT)
    block(d, (nx + 18, 716),
          'domain/DormLinkDomain.ts\n  runEngine() / sortCandidates()\npages/Index.ets\n  execute() / appendLogs()',
          nw - 36, 16, SUB, 7)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, 'rule_flow.png')
    img = trim(img)
    img.save(out)
    return out


if __name__ == '__main__':
    print('wrote', architecture())
    print('wrote', rule_flow())
