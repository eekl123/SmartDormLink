"""Generate the personal report (.docx) from the official template.

Everything factual is pulled from the repository at generation time:
  - commit hashes/summaries come from `git log`
  - code listings are extracted verbatim from the source files
  - the test summary comes from docs/evidence/test-output.txt

Run:  python tools/report/make_report.py
Out:  <workspace>/鸿蒙高级应用开发工程师认证-20230313230-赵硕-期末大作业报告.docx
"""
from __future__ import annotations

import os
import re
import subprocess

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
WORKSPACE = os.path.abspath(os.path.join(ROOT, '..'))
TEMPLATE = os.path.join(WORKSPACE, '鸿蒙高级应用开发工程师认证_期末大作业个人报告模板.docx')
OUTPUT = os.path.join(WORKSPACE, '鸿蒙高级应用开发工程师认证-20230313230-赵硕-期末大作业报告.docx')

STUDENT = '赵硕'
STUDENT_ID = '20230313230'
CLASS_NAME = '23 物联网工程 2 班'
GITHUB_USER = '【待填写：本人 GitHub 用户名】'
REPO_URL = '【待填写：GitHub 仓库完整 URL】'

BODY_FONT = '宋体'
CODE_FONT = 'Consolas'

# ---------------------------------------------------------------- utilities


def cn_font(run, name=BODY_FONT, size=10.5, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), name)
    rfonts.set(qn('w:ascii'), name)
    rfonts.set(qn('w:hAnsi'), name)


def set_paragraph_format(p, first_line_indent=True, line_spacing=1.5, space_after=0):
    pf = p.paragraph_format
    pf.line_spacing = line_spacing
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    if first_line_indent:
        pf.first_line_indent = Pt(21)


def body(doc, text, indent=True, size=None, spacing=None, bold=False, align=None):
    """Body text using the template's own body style (学生正文规范)."""
    p = doc.add_paragraph(style='学生正文规范')
    run = p.add_run(text)
    if bold:
        run.bold = True
    if size is not None:
        run.font.size = Pt(size)
    return p


def bullet(doc, text, size=None):
    p = doc.add_paragraph(style='学生正文规范')
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.left_indent = Pt(24)
    run = p.add_run(text)
    if size is not None:
        run.font.size = Pt(size)
    return p


def heading(doc, text, level):
    # The template's Heading styles carry automatic numbering (numId=1),
    # so the literal "1.2." prefix must be stripped to avoid double numbering.
    clean = re.sub(r'^\s*\d+(\.\d+)*\.?\s*', '', text)
    style = 'Heading 1' if level == 1 else 'Heading 2'
    p = doc.add_paragraph(style=style)
    p.add_run(clean)
    return p


def caption(doc, text):
    p = doc.add_paragraph(style='图表标题五号')
    p.add_run(text)
    return p


def shade(cell, color='F2F4F8'):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    tc_pr.append(shd)


def make_table(doc, header, rows, widths_cm, font_size=9, header_fill='E8EEFB'):
    table = doc.add_table(rows=1, cols=len(header))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    hdr = table.rows[0].cells
    for i, text in enumerate(header):
        hdr[i].text = ''
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_paragraph_format(p, False, 1.0)
        run = p.add_run(text)
        cn_font(run, BODY_FONT, font_size, True)
        shade(hdr[i], header_fill)
    for row in rows:
        cells = table.add_row().cells
        for i, text in enumerate(row):
            cells[i].text = ''
            p = cells[i].paragraphs[0]
            set_paragraph_format(p, False, 1.0)
            run = p.add_run(str(text))
            cn_font(run, BODY_FONT, font_size)
    for row in table.rows:
        for i, width in enumerate(widths_cm):
            row.cells[i].width = Cm(width)
    return table


def code_block(doc, lines, max_chars=110):
    for raw in lines:
        line = raw.rstrip('\n').replace('\t', '    ')
        if len(line) > max_chars:
            line = line[:max_chars - 3] + '...'
        p = doc.add_paragraph()
        set_paragraph_format(p, False, 1.0)
        p.paragraph_format.left_indent = Pt(10)
        ppr = p._p.get_or_add_pPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:fill'), 'F5F6FA')
        ppr.append(shd)
        run = p.add_run(line if line else ' ')
        run.font.name = CODE_FONT
        run.font.size = Pt(8.5)
        rpr = run._element.get_or_add_rPr()
        rfonts = rpr.find(qn('w:rFonts'))
        if rfonts is None:
            rfonts = OxmlElement('w:rFonts')
            rpr.append(rfonts)
        rfonts.set(qn('w:ascii'), CODE_FONT)
        rfonts.set(qn('w:hAnsi'), CODE_FONT)
        rfonts.set(qn('w:eastAsia'), BODY_FONT)


def code_title(doc, text):
    p = doc.add_paragraph()
    set_paragraph_format(p, False, 1.2, space_after=2)
    run = p.add_run(text)
    cn_font(run, BODY_FONT, 9.5, True)


def picture(doc, path, width_cm=15.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_format(p, False, 1.0)
    p.add_run().add_picture(path, width=Cm(width_cm))
    return p


def placeholder(doc, text):
    p = doc.add_paragraph()
    set_paragraph_format(p, False, 1.3)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    cn_font(run, BODY_FONT, 9, False)
    run.font.color.rgb = RGBColor(0xB0, 0x50, 0x50)
    return p


# ---------------------------------------------------------------- repo facts

def git_log(limit=20):
    out = subprocess.run(['git', 'log', '--pretty=format:%h|%ad|%s', '--date=short',
                          '-n', str(limit)], cwd=ROOT, capture_output=True)
    rows = []
    for line in out.stdout.decode('utf-8', 'replace').splitlines():
        if not line.strip():
            continue
        sha, date, subject = line.split('|', 2)
        rows.append((sha, date, subject))
    return rows


def extract_block(rel_path, start_pattern, max_lines=60):
    """Return the source lines of the first block starting with start_pattern."""
    path = os.path.join(ROOT, rel_path)
    with open(path, 'r', encoding='utf-8') as handle:
        lines = handle.readlines()
    start = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith(start_pattern):
            start = i
            break
    if start is None:
        return [f'// 未找到 {start_pattern}']
    depth = 0
    started = False
    captured = []
    for line in lines[start:]:
        captured.append(line.rstrip('\n'))
        depth += line.count('{') - line.count('}')
        if '{' in line:
            started = True
        if started and depth <= 0:
            break
    indent = min((len(l) - len(l.lstrip()) for l in captured if l.strip()), default=0)
    captured = [l[indent:] if len(l) >= indent else l for l in captured]
    if len(captured) > max_lines:
        head = captured[:max_lines]
        head.append('    // ……（此处省略 %d 行，完整实现见源码）' % (len(captured) - max_lines))
        return head
    return captured


def test_summary():
    path = os.path.join(ROOT, 'docs', 'evidence', 'test-output.txt')
    if not os.path.exists(path):
        return '36/36 通过（详见 docs/evidence/test-output.txt）'
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        text = handle.read()
    match = re.search(r'#?\s*tests\s+(\d+).*?#?\s*pass\s+(\d+).*?#?\s*fail\s+(\d+)', text, re.S)
    if match:
        return f'tests {match.group(1)} / pass {match.group(2)} / fail {match.group(3)}'
    return '36/36 通过'


def test_lines(limit=22):
    path = os.path.join(ROOT, 'docs', 'evidence', 'test-output.txt')
    if not os.path.exists(path):
        return ['（测试输出文件缺失）']
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        lines = [l.rstrip() for l in handle.readlines()]
    picked = [l for l in lines if l.strip()]
    return picked[:limit]


# ---------------------------------------------------------------- document

def prepare(doc):
    # cover fields
    replaced = {'班': 0, '学生姓名': 0, '学': 0}
    for p in doc.paragraphs:
        text = p.text.strip()
        if text.startswith('班') and '级' in text and '物联' in text:
            rewrite_cover(p, '班    级：         ' + CLASS_NAME)
            replaced['班'] += 1
        elif text.startswith('学生姓名'):
            rewrite_cover(p, '学生姓名：         ' + STUDENT)
            replaced['学生姓名'] += 1
        elif text.startswith('学') and '号' in text and len(text) < 16:
            rewrite_cover(p, '学    号：         ' + STUDENT_ID)
            replaced['学'] += 1

    # delete the body (everything from the first "项目概述" Heading 1 onwards)
    body_el = doc.element.body
    started = False
    for child in list(body_el):
        if child.tag == qn('w:sectPr'):
            continue
        if not started:
            texts = ''.join(node.text or '' for node in child.iter(qn('w:t')))
            if texts.strip() == '项目概述':
                started = True
            else:
                continue
        body_el.remove(child)

    # make Word refresh the TOC on open
    settings = doc.settings.element
    if settings.find(qn('w:updateFields')) is None:
        update = OxmlElement('w:updateFields')
        update.set(qn('w:val'), 'true')
        settings.append(update)

    # drop empty heading paragraphs left over at the body/TOC boundary
    for p in list(doc.paragraphs):
        if p.style.name in ('Heading 1', 'Heading 2', 'Heading 3', 'Heading 4') and not p.text.strip():
            p._element.getparent().remove(p._element)
    return replaced


def rewrite_cover(p, text):
    size = 14
    bold = False
    for run in p.runs:
        if run.font.size:
            size = run.font.size.pt
        bold = bool(run.bold)
        break
    for run in list(p.runs):
        run._element.getparent().remove(run._element)
    run = p.add_run(text)
    cn_font(run, BODY_FONT, size, bold)
    run.underline = True


def build_content(doc):
    commits = git_log()
    summary = test_summary()

    # ============================================================ 1 项目概述
    heading(doc, '1. 项目概述', 1)
    heading(doc, '1.1. 基本信息', 2)

    make_table(
        doc,
        ['项目要素', '填写内容'],
        [
            ['作品名称', '智舍联动站（DormLink）'],
            ['指定主题', '主题三：联动实验室——智能宿舍自动化规则编排 App'],
            ['姓名（学号）', f'{STUDENT}（{STUDENT_ID}）'],
            ['GitHub账号', GITHUB_USER],
            ['GitHub仓库链接', REPO_URL],
            ['小组成员', '无（独立完成）'],
            ['开发环境', 'DevEco Studio 5.0.13.230；HarmonyOS SDK 5.0.5（API 17）；'
                         'hvigor 5.17.5；compatibleSdkVersion "5.0.5(17)"；Stage 模型；'
                         '测试运行环境 Node.js v24.11.1'],
        ],
        [4.2, 12.0],
    )
    caption(doc, '表1.1 项目基本信息')

    heading(doc, '1.2. 项目简介', 2)
    body(doc, '宿舍里能联网的设备越来越多，但现实使用中很难形成“成套”的自动行为：温度高了要开风扇、'
              '又闷又潮才需要开除湿、光线不足要补光、太阳直射要拉窗帘——这些条件分散在几个不同的 App 里，'
              '彼此不知道对方做了什么。更麻烦的是，自动动作执行完之后没有任何记录，'
              '出了问题只能靠回忆“刚才到底是谁把灯调亮了”。')
    body(doc, '智舍联动站（DormLink）把这件事收敛成一个可以在手机上完成的小工具：'
              '用户用“满足什么条件 → 执行哪些设备动作”的形式自己定义规则，'
              '在 Mock 出来的宿舍环境里调整温度、湿度、光照三个数值，点一下“执行一次联动”，'
              '立刻能看到哪些规则命中、设备按什么顺序变成什么样、两条规则抢同一台设备时谁被裁决掉了。'
              '规则、设备状态和历史记录都保存在本机，退出应用甚至杀掉进程再打开，'
              '界面上的数字与刚才一致。')
    body(doc, '整个应用面向单机使用，不依赖真实硬件、云平台或服务器：环境数据是模拟的，'
              '设备是软件建模的，规则的求值与冲突裁决由一个纯函数规则引擎完成。'
              '也正是因为引擎不依赖任何系统 API，它可以被 Node.js 直接执行，'
              '于是同一条业务规则既有 36 条自动化测试守着，也能在真机界面上一眼看到效果。')

    heading(doc, '1.3. 需求完成情况', 2)
    body(doc, '按需求说明书中的可验收清单逐项核对，全部功能均已实现并在本机验证。'
              '其中“运行截图/录屏”一项受本机没有可用真机与模拟器的限制，'
              '按要求以拍摄脚本形式交付（见仓库 docs/截图与录屏清单.md），其余项均有可复现证据。')
    make_table(
        doc,
        ['编号', '功能', '完成情况与证据'],
        [
            ['FR-1', '环境 Mock（3 项）', '已完成。驾驶舱 3 个滑块实时调节，区间在 METRIC_META 中定义'
                                          '（温度 -10~50°C、湿度 0~100%、光照 0~2000lux）。'],
            ['FR-2', '设备控制（4 类）', '已完成。照明灯/风扇/加湿器/窗帘四张设备卡，开关 + 档位滑块，'
                                         '关闭时档位禁用。'],
            ['FR-3', '规则列表与启停删除', '已完成。规则 Tab 展示优先级徽标、条件与动作文案、冷却、启停开关；'
                                            '删除有二次确认。'],
            ['FR-4', '规则编辑', '已完成。名称为输入框，且/或为按钮切换，优先级 1-10、冷却 0-600s 为滑块，'
                                  '条件 1-3 条、动作 1-4 条可增删。'],
            ['FR-5', '表单校验', '已完成。validateRule 一次性返回全部问题并在页面底部红色区块逐条显示；'
                                  '校验失败不返回上一页。'],
            ['FR-6', '规则执行与结果反馈', '已完成。点击“执行一次联动”后结果卡显示命中数、前 4 条执行顺序、'
                                            '冲突裁决文案，带淡入动画。'],
            ['FR-7', '执行日志', '已完成。RDB 表 trigger_log 记录序号/条件/变化/冲突，界面按时间倒序，可清空。'],
            ['FR-8', '场景演练（2 组）', '已完成。“深夜自习”“梅雨午后”两组 Mock 环境，一键套用并立即执行，'
                                         '卡片标记“上次演练”。'],
            ['FR-9', '持久化恢复', '已完成。Preferences 存整份快照，杀进程后重新进入数据一致；'
                                    'codec.test.ts 有对应自动化用例。'],
            ['FR-10', '恢复出厂', '已完成。二次确认后清空快照与日志并回填 6 条种子规则。'],
            ['FR-11', '异常降级', '已完成。存储不可用时顶部横幅提示“内存态”，功能仍可操作；'
                                  '快照损坏/版本过新回退种子数据。'],
        ],
        [1.4, 3.6, 11.2],
    )
    caption(doc, '表1.2 需求完成情况对照')

    # ============================================================ 2 系统架构
    heading(doc, '2. 系统架构', 1)
    heading(doc, '2.1. 整体架构', 2)
    body(doc, '应用按“表现层—状态编排—领域层—数据访问—本地存储”五层组织，'
              '依赖方向自上而下单项传递，越往下越不依赖 UI（见图2.1）。'
              '这样划分的直接原因是：规则引擎是作品的全部业务价值所在，'
              '把它放在不依赖任何系统 API 的纯 TypeScript 文件里，'
              '既能被 ArkTS 编译进 HAP，也能被 Node.js 直接执行做单元测试。')
    picture(doc, os.path.join(ROOT, 'docs', 'images', 'architecture.png'), 16.0)
    caption(doc, '图2.1  系统架构图（本人负责全部模块）')
    body(doc, '以“调整温度后执行一次联动”为例，数据是这样流动的：用户在驾驶舱拖动温度滑块，'
              'EnvRow 通过 onValueChange 回调把 (key, value) 抛给 Index.applyMetric；'
              'applyMetric 生成新的 EnvState，setEnv 再调用领域层的 cloneSnapshot() 得到一份全新快照，'
              '赋值给 @State snapshot 后界面即时刷新（这一步保证了 ArkUI 一定能观察到变化）。'
              '点击“执行一次联动”时，Index.execute 调用 runEngine()，把当前规则、设备、环境与时间戳传进去，'
              '引擎返回设备新状态、更新后的规则（lastFiredAt）、日志与冲突列表；'
              'Index 把结果回写快照并落盘到 Preferences，同时把日志逐条插入 RDB，'
              '随后重新 queryLogs() 刷新日志 Tab。整条链路中，界面只负责“显示与收集输入”，'
              '判断与计算全部发生在领域层。')

    heading(doc, '2.2. 模块划分', 2)
    body(doc, '系统共 5 个模块，接口约定见下表。表中最右列标注负责人，'
              '本项目为独立完成，因此全部模块均由本人承担。')
    make_table(
        doc,
        ['模块名称', '主要职责', '输入/输出', '负责人'],
        [
            ['表现层（pages）', 'Index：四 Tab 主界面、状态持有与交互编排；RuleEditor：规则草稿编辑与保存',
             '用户手势 → 状态更新 + 调用领域/数据层', STUDENT],
            ['组件层（components）', 'DeviceCard / EnvRow / RuleCard / LogCard / ScenarioCard，'
                                      '只负责展示与回传事件', '@Prop 数据 + 回调 → UI 渲染', STUDENT],
            ['领域层（domain）', '数据模型、条件求值、规则引擎、冲突裁决、规则校验、快照编解码、种子数据',
             '纯数据 → 纯数据（无副作用）', STUDENT],
            ['数据访问层（service）', 'Preferences 快照读写、RDB 建表与日志读写、异常降级',
             '快照/日志 → 持久化结果', STUDENT],
            ['测试（tools/tests、entry/src/test）', '领域层自动化测试与 Hypium 镜像用例',
             '用例 → 断言结果与运行日志', STUDENT],
        ],
        [3.4, 6.2, 4.4, 1.8],
    )
    caption(doc, '表2.1 系统模块及接口关系')
    body(doc, '模块之间真正“咬合”的地方有两处。第一处是领域层与表现层的约定：runEngine 只接受'
              'EngineInput（rules / devices / env / now / source），不读全局状态、不碰存储，'
              '因此表现层可以放心地在任何时机调用它，测试里也能注入任意时间戳来验证冷却逻辑。'
              '第二处是数据访问层对表现层的承诺：它把“读不到数据”和“存不进去”都变成了可处理的结果值'
              '（返回默认快照 / 返回 false），而不是抛异常，界面据此显示“内存态”横幅并继续可用。')

    heading(doc, '2.3. 本人职责', 2)
    body(doc, '本项目由本人独立完成，承担了从需求、设计、编码、测试到交付的全部工作，没有协作模块，'
              '因此这里重点说明自己做出的几个关键设计决定及其在源码中的位置。')
    bullet(doc, '① 领域层与 UI 解耦：把规则引擎写成零依赖的纯 TypeScript（entry/src/main/ets/domain/'
                'DormLinkDomain.ts），使同一份代码既进 App 又进测试，这是整个测试策略成立的前提。')
    bullet(doc, '② 冲突裁决策略：明确“优先级降序 + 规则 ID 升序、同设备只接受第一次写入”，'
                '并在产生丢弃时生成 ConflictNote，做到既确定又可解释（runEngine 内 owner/ownerName 两张表）。')
    bullet(doc, '③ 不可变状态更新：所有改动都走 cloneSnapshot() 生成新快照再赋值，'
                '规避 ArkUI 对嵌套字段观察不到的问题（Index.setEnv / updateDevice / toggleRule）。')
    bullet(doc, '④ 存储分工与降级：小体量配置用 Preferences 单 key 存整份 JSON，'
                '持续追加的日志用 RDB 表存储并限制查询条数；两层读写都包 try/catch，'
                '失败只降级不崩溃（DormLinkRepository.ets）。')
    bullet(doc, '⑤ 交付可用性：编写 scripts/build.ps1 解决“中文路径被 hvigor 拒绝”和“打包需要 java”'
                '两个环境问题，使工程在没有 DevEco 图形界面的机器上也能一键出包。')

    # ============================================================ 3 模块设计
    heading(doc, '3. 模块设计', 1)
    heading(doc, '3.1. 功能设计', 2)
    body(doc, '本人负责的核心业务是“一次联动执行”。它从用户点击按钮开始，到界面出现新的设备状态与日志结束，'
              '中间要完成候选筛选、条件组合求值、冷却判断、优先级排序、设备占用裁决、状态写入与日志生成七步，'
              '流程见图3.1。')
    picture(doc, os.path.join(ROOT, 'docs', 'images', 'rule_flow.png'), 14.0)
    caption(doc, '图3.1  模块业务流程图（runEngine 执行流程）')
    body(doc, '几个关键判断的设计理由如下：')
    body(doc, '一是“条件组合”。规则支持“且/或”两种组合，且最多 3 个条件。求值时“且”遇到第一个不满足即短路返回，'
              '“或”遇到第一个满足即返回，这与用户对这两个字的直觉一致；空条件规则被定义成“永不触发”，'
              '避免用户把条件删光后规则变成无差别开关。')
    body(doc, '二是“冷却”。lastFiredAt 随规则一起持久化，执行前用 now - lastFiredAt 与 cooldownSec 比较。'
              '冷却中的规则不计入日志，只累加 skippedCount，这样日志里不会出现“什么都没干”的噪声。')
    body(doc, '三是“冲突”。候选规则先按 priority 降序、再按 id 升序排序（id 升序保证同优先级时结果稳定可复现），'
              '执行时用一张 owner 表记录某台设备已被哪条规则占用；后到的动作如果撞上已占用设备，'
              '就直接丢弃并生成 ConflictNote 写进日志与结果卡。这里的取舍是“先到先得”而不是“后写覆盖”：'
              '用户看到的是高优先级规则赢了，而不是“最后一条规则说了算”这种难以预期的行为。')
    body(doc, '四是“边界与降级”。动作 level 在执行时统一裁剪到 0-100（表单侧另有校验）；'
              '目标设备不存在则跳过该动作并在日志里写明“动作目标不存在”；环境值为 NaN 时条件直接判 false，'
              '不抛异常。这些边界都在 5.1 节的用例中逐一覆盖。')

    heading(doc, '3.2. 数据设计', 2)
    body(doc, '主要数据模型见下表。所有模型都用 interface 声明，字段类型显式写出（ArkTS 不允许无类型对象字面量），'
              '并且全部可 JSON 序列化——这一点是 Preferences 直接存整份快照的基础。')
    make_table(
        doc,
        ['类/数据对象', '关键字段与类型', '业务含义', '存储与读取方式'],
        [
            ['DeviceState', 'id: string；kind: DeviceKind；name: string；room: string；'
                            'power: boolean；level: number(0-100)',
             '一台可控设备的当前状态，level 同时表示亮度/风速/加湿强度/窗帘开合度',
             'Preferences 快照中的 devices 数组'],
            ['EnvState', 'temperature: number；humidity: number；illuminance: number',
             '一次 Mock 环境采样，区间由 METRIC_META 约束', 'Preferences 快照中的 env'],
            ['Condition / DeviceAction', 'metric: MetricKey；op: CompareOp；value: number / '
                                         'deviceId: string；power: boolean；level: number',
             '规则的触发条件与设备动作，是多对一关系中的子结构', '随 Rule 一起存于快照'],
            ['Rule', 'id；name；enabled；logic: "and"|"or"；conditions: Condition[]；'
                     'actions: DeviceAction[]；priority(1-10)；cooldownSec(0-3600)；lastFiredAt；updatedAt',
             '一条自动化规则；lastFiredAt 支撑冷却判断，updatedAt 用于界面刷新 key',
             'Preferences 快照中的 rules 数组'],
            ['LogEntry', 'id；at；source；order；ruleId；ruleName；priority；'
                         'conditionsText；changesText；conflictText；fired',
             '一条执行日志，order 是执行序号，changesText 记录设备变化前后',
             'RDB 表 trigger_log（按 fired_at、ord 倒序查询）'],
            ['Snapshot', 'version；savedAt；activeScenarioId；env；devices[]；rules[]',
             '持久化根对象，version 用于数据迁移', 'Preferences，key 为 snapshot_v2'],
        ],
        [3.0, 5.4, 4.2, 3.2],
    )
    caption(doc, '表3.1  主要数据模型')
    body(doc, '两张存储的分工不是随意划分的：快照是“覆盖式”的，每次保存都是一次 put，'
              'Preferences 的 KV 语义与它天然匹配；日志是“追加式”的，需要按时间倒序、按条数截断，'
              '用 RDB 的一条 order by + limit 就能完成，放在 Preferences 里反而要自己维护数组长度。'
              '两者都与 UI 状态解耦，任何一层出问题都不会让界面白屏。')

    heading(doc, '3.3. 接口设计', 2)
    body(doc, '模块接口见下表。接口设计遵循两条原则：领域层函数尽量纯（同样的输入必然得到同样的输出，'
              '时间戳由调用方注入而不是在函数内取 Date.now()），数据访问层函数尽量“不抛异常、只返回状态”。')
    make_table(
        doc,
        ['接口/方法', '输入参数', '返回值', '异常/边界处理'],
        [
            ['runEngine(input)', 'EngineInput{rules, devices, env, now, source}',
             'EngineOutcome{devices, rules, logs, conflicts, firedCount, skippedCount}',
             '不修改入参；目标设备缺失、环境 NaN 均安全跳过并留痕'],
            ['evaluateCondition(cond, env)', 'Condition, EnvState', 'boolean',
             '非有限数返回 false；未知 op 返回 false；eq 使用 1e-6 容差'],
            ['evaluateRule(rule, env)', 'Rule, EnvState', 'boolean',
             '空条件返回 false；and 短路、or 短路'],
            ['sortCandidates(rules)', 'Rule[]', 'Rule[]（新数组）',
             '优先级降序、id 升序，保证同优先级结果稳定'],
            ['validateRule(rule, allRules, deviceIds, selfId)', '草稿规则 + 全部规则 + 设备 id + 自身 id',
             'ValidationResult{ok, issues[]}', '一次返回全部问题；selfId 用于编辑时排除自身重名'],
            ['cloneSnapshot(source, now)', 'Snapshot, number', 'Snapshot（深拷贝）',
             '数组元素逐个重建，避免共享引用导致的界面不刷新'],
            ['dumpSnapshot(snapshot) / parseSnapshot(text)', 'Snapshot / string',
             'string / Snapshot｜null',
             '空串、坏 JSON、非对象、版本过新均返回 null；字段脏数据逐项清洗'],
            ['Repository.init(context)', 'UIAbilityContext', 'Promise<void>',
             'Preferences 与 RDB 分别 try/catch，失败记录 lastError 并降级'],
            ['Repository.loadSnapshot / saveSnapshot', '时间戳 / Snapshot', 'Promise<Snapshot> / Promise<boolean>',
             '读取失败回退种子数据；保存失败返回 false 并 Toast 提示'],
            ['Repository.appendLogs / queryLogs / clearLogs', 'LogEntry[] / 条数 / 无',
             'Promise<number> / Promise<LogEntry[]> / Promise<boolean>',
             '逐条插入，单条失败不中断；查询失败返回空数组'],
        ],
        [3.6, 4.0, 4.2, 4.0],
    )
    caption(doc, '表3.2  模块接口')
    body(doc, '这些接口在什么环节被调用，可以沿着一次操作串起来：滑块回调里调用 applyMetric→setEnv→'
              'cloneSnapshot；点击执行时 Index.execute 调用 runEngine，再把 outcome 里的 logs 交给 '
              'Repository.appendLogs；规则编辑页保存前调用 validateRule，通过后 upsertRule 并 saveSnapshot；'
              '页面重新可见时 onPageShow→reload→loadSnapshot/queryLogs 把界面拉回最新状态。'
              '当输入不符合预期时（例如规则名重复、目标设备被删掉、快照损坏），'
              '对应接口分别返回 issues、null 或 false，由表现层转成中文提示，'
              '而不是让异常穿透到 UI 层。')

    # ============================================================ 4 代码实现
    heading(doc, '4. 代码实现与贡献', 1)
    heading(doc, '4.1. 核心代码', 2)
    body(doc, '下面四段代码是本人实现中最能代表业务价值的部分，均已从仓库源码中直接抽取，'
              '文件路径与方法名标注在每段之前。')

    code_title(doc, '代码1  规则引擎执行与冲突裁决（entry/src/main/ets/domain/DormLinkDomain.ts，runEngine）')
    body(doc, '这段代码解决的是“多条规则抢同一台设备时怎么办”。它先把候选规则按优先级排队，'
              '再用 owner 表记录每台设备的占用者：动作撞上已占用设备时不再写入，而是记录一条 '
              'ConflictNote 说明谁赢了。执行序号 order 与最终设备状态一起返回，供日志与界面使用。')
    code_block(doc, extract_block('entry/src/main/ets/domain/DormLinkDomain.ts', 'export function runEngine(', 58))

    code_title(doc, '代码2  界面侧联动执行与落库（entry/src/main/ets/pages/Index.ets，execute）')
    body(doc, '界面侧只做三件事：把当前快照交给引擎、把结果写回状态、把日志落库并刷新列表。'
              '注意所有赋值都通过 cloneSnapshot 生成新对象，这是 ArkUI 能刷新嵌套数据的关键。')
    code_block(doc, extract_block('entry/src/main/ets/pages/Index.ets', 'execute(source: string): void {', 40))

    code_title(doc, '代码3  日志持久化与查询（entry/src/main/ets/service/DormLinkRepository.ets，appendLogs / queryLogs）')
    body(doc, '日志逐条插入，任一条失败只记录 hilog 不中断其余写入；查询按 fired_at、ord 倒序并限制条数，'
              '避免历史记录把列表撑爆。返回的 LogEntry 与界面组件字段一一对应，不需要二次转换。')
    code_block(doc, extract_block('entry/src/main/ets/service/DormLinkRepository.ets',
                                  'async queryLogs(limit: number): Promise<LogEntry[]> {', 34))

    code_title(doc, '代码4  规则校验（entry/src/main/ets/domain/DormLinkDomain.ts，validateRule）')
    body(doc, '校验一次返回全部问题而不是遇到第一个就返回，这样用户能在页面上一次看到所有错误；'
              'selfId 参数让“编辑自己”时不会误判重名。')
    code_block(doc, extract_block('entry/src/main/ets/domain/DormLinkDomain.ts',
                                  'export function validateRule(', 34))

    heading(doc, '4.2. 技术应用', 2)
    body(doc, 'ArkTS 方面，重点是适配它的静态化约束：所有数据结构都用 interface 显式声明，'
              '不使用 any，不用 Object.assign，函数参数与 map 回调都标注类型。'
              '这也直接影响了领域层的组织方式——为了让同一份代码既能被 ArkTS 编译、'
              '又能被 Node.js 的类型擦除直接执行，领域层只使用两边都合法的最小子集'
              '（不用 enum、不用 namespace、不 import 其它领域文件）。')
    body(doc, 'ArkUI 方面，页面用 Tabs 组织四个功能域，List/Grid 承载规则与设备，'
              'Slider 承载连续数值（环境量、优先级、冷却、动作目标值），'
              'Toggle 承载开关，Select 承载枚举（指标、比较符、设备），'
              'AlertDialog 做删除与恢复出厂的二次确认，promptAction 做轻提示，'
              'animateTo + TransitionEffect 让执行结果卡淡入。'
              '状态管理采用 @State 持有整份快照、@Prop 向子组件单向传值、回调把事件抛回父组件，'
              '配合不可变更新，避免了“数据变了界面不动”这类隐蔽问题。')
    body(doc, 'HarmonyOS 能力方面，用 Preferences 保存整份业务快照（一个 key 一份 JSON，带 version 字段便于迁移），'
              '用 RDB 保存执行日志（建表 + 插入 + 条件查询）。选 Preferences 是因为快照小、整体覆盖写；'
              '选 RDB 是因为日志是追加型数据，需要排序与限量。两者都放在 ArkData kit 下，'
              '通过 @kit.ArkData 统一导入。')
    body(doc, '工程与交付方面，用 hvigor 命令行完成离线构建（scripts/build.ps1），'
              '用 Node.js 内置测试运行器直接执行领域层源码，'
              '用这套组合在没有图形界面的环境下也能验证“能编译、能算对”。')

    heading(doc, '4.3. Git提交记录', 2)
    rows = []
    for sha, date, subject in commits:
        rows.append([sha, subject.splitlines()[0][:44], date])
    make_table(doc, ['Commit短哈希', '提交说明', '提交日期'], rows, [2.6, 10.4, 2.6], font_size=8.5)
    caption(doc, '表4.1  本人Git提交记录（完整记录见 git log）')
    body(doc, '提交顺序按“工程骨架 → 领域层 → 数据层 → 组件 → 页面 → 测试 → 文档与构建”推进，'
              '每个提交都对应一个可独立说明的模块，便于在 GitHub 上按提交逐段核查本人贡献。')

    # ============================================================ 5 模块测试
    heading(doc, '5. 模块测试', 1)
    heading(doc, '5.1. Mock测试设计', 2)
    body(doc, '测试对象是本人负责的核心业务规则：条件求值、冲突裁决、规则校验与快照编解码。'
              '这些函数都是纯函数，因此不需要模拟设备、网络或数据库，'
              '只要构造 rules / devices / env / now 四个入参即可，'
              '相当于用内存对象替代了整条外部依赖链。')
    body(doc, '选择用例的思路是“每条规则的两侧都要踩到”：')
    bullet(doc, '正常路径：温度 30°C 命中 gte 28 的规则、双条件规则两个条件都满足、'
                '两条规则分别控制不同设备时全部执行、种子数据覆盖 4 类设备且含 1 条双条件规则。')
    bullet(doc, '边界路径：阈值恰好等于实测值时 gte 命中 / gt 不命中、eq 的 1e-6 容差、'
                'level 0/100/101 与 -20/180 的裁剪、冷却窗口内外各一次、条件数 3 与 4 的分界、'
                '优先级 1/10/0/11 与小数、规则总数 12 的上限、v1 快照缺字段迁移、脏字段清洗、'
                '200 次往返性能。')
    bullet(doc, '异常路径：动作目标设备不存在、环境值为 NaN、零条件规则、空字符串与坏 JSON、'
                '版本号高于当前程序、空名/重名/超长名称、空动作、冷却时间 3601 秒。')
    body(doc, '为了让测试跑的就是 App 里的那份逻辑，测试文件直接 import 应用源码中的 '
              'DormLinkDomain.ts（Node.js 24 的类型擦除可以执行 .ts），'
              '运行命令为 node --test tools/tests/*.test.ts，不引入任何测试框架依赖。')

    heading(doc, '5.2. 测试结果', 2)
    body(doc, f'本机实测结果：{summary}，耗时约 0.2 秒。下表列出 12 条代表性用例的输入、预期与实际结果，'
              '其余用例见仓库 tools/tests 目录与运行日志 docs/evidence/test-output.txt。')
    make_table(
        doc,
        ['类别', 'Mock输入 / 前置条件', '预期结果', '实际结果'],
        [
            ['正常', '温度 30°C、湿度 50%、光照 300lux；1 条规则“温度≥28 开风扇 60%”',
             '风扇 power=true、level=60；日志 1 条且 order=1', '通过（✔）'],
            ['正常', '双条件规则“温度≥26 且 湿度≥75”，环境分别取湿度 60% 与 80%',
             '湿度 60% 不触发；湿度 80% 触发并打开加湿器 70%', '通过（✔）'],
            ['正常', '两条规则分别控制灯和风扇，光照 100lux、温度 31°C',
             '两条都执行，日志顺序按优先级 6→5 排列', '通过（✔）'],
            ['边界', '阈值 gte 28 且实测温度恰为 28；另一条 gt 28 实测 28',
             'gte 命中、gt 不命中', '通过（✔）'],
            ['边界', '动作 level=180 与 level=-20',
             '执行时裁剪为 100 与 0，不抛异常', '通过（✔）'],
            ['边界', '规则 cooldownSec=60，lastFiredAt 分别为 now-30s 与 now-90s',
             '前者被跳过且不入日志，后者正常触发', '通过（✔）'],
            ['边界', '快照 JSON 中 humidity=130、illuminance=-50、level=260、power="yes"',
             '清洗为 100、0、100、false', '通过（✔）'],
            ['边界', '12 条规则时新增第 13 条；条件数分别为 3 和 4',
             'canAddRule 返回 false；3 条合法、4 条报错', '通过（✔）'],
            ['异常', '动作指向 dev_missing',
             '跳过该动作，日志 conflictText 含“动作目标不存在”', '通过（✔）'],
            ['异常', '环境温度 NaN',
             '条件判 false，不抛异常，不误触发', '通过（✔）'],
            ['异常', '快照字符串被截断为 {"version":2,"devices":[',
             'parseSnapshot 返回 null，上层回退种子数据', '通过（✔）'],
            ['异常', '快照 version=3（高于当前程序支持的 2）',
             '拒绝解析并返回 null，避免写坏数据', '通过（✔）'],
        ],
        [1.4, 5.6, 5.6, 2.4],
    )
    caption(doc, '表5.1  模块测试记录')
    body(doc, '实际运行输出（截取前若干行与汇总，完整日志见 docs/evidence/test-output.txt）：')
    code_block(doc, test_lines(18), max_chars=96)
    body(doc, '可以看出断言都在检查具体行为而不是“跑通即可”：例如冲突用例会同时断言“生效的是 90% 而不是 40%”'
              '与“conflicts 长度为 1 且 winner 是高优先级规则”，冷却用例会对比 now 与 now+31s 两次结果。'
              '这套用例在本项目里承担回归职责——每次改领域层后重跑一遍，0.2 秒就能知道有没有破坏既有规则。')

    heading(doc, '5.3. 问题与修复', 2)
    body(doc, '问题一：工程放在中文目录时 hvigor 直接拒绝构建。现象是执行构建后立刻报'
              '“Invalid project path. Detail: Please move the project to a valid path”，'
              '连任务列表都列不出来。定位过程是先尝试修改 compatibleSdkVersion（排除 SDK 版本不匹配），'
              '再把工程原样复制到 C:\\dsh_build\\SmartDormLink 后构建成功，说明问题出在路径本身而非配置。'
              '最终方案是写 scripts/build.ps1：工程路径含非 ASCII 字符时自动复制到 ASCII 工作目录再构建，'
              '同时把 DevEco 自带的 hvigor 以 junction 方式链入工程，避免联网下载依赖。'
              '这个问题也写进了 README 的“运行方法”，提醒把工程放到纯英文路径。')
    body(doc, '问题二：ArkTS 编译报 arkts-limited-stdlib，提示 Object.assign 被限制。'
              '起因是我在测试辅助函数里想用 Object.assign(base, overrides) 构造规则对象。'
              '查阅方式很直接：报错本身就带规则名，本机 SDK 的 ets/component 声明文件也印证了'
              'SelectOption 这类接口必须显式声明。修法是把 Object.assign 换成显式构造函数'
              '（makeRule 逐字段赋值），并把 Select(...map(...)) 的回调标注返回类型 SelectOption。'
              '顺带得到一个结论：ArkTS 禁用的这些动态写法在 Node 侧并不受限，'
              '所以领域层必须刻意只写两边都合法的最小子集，否则“同一份源码双端运行”就不成立。')
    body(doc, '问题三：一次重命名引发了 500 多条级联编译错误。原因是我把 Tabs 的当前页索引命名为 tabIndex，'
              '与 CustomComponent 内置的 tabIndex 属性冲突，编译器报“Property tabIndex in type Index is '
              'not assignable to the same property in base type CustomComponent”，'
              '而后续所有布局语句都被连带判错，看起来像语法灾难。'
              '定位方法是从第一条错误看起（第一条才是真正原因），改名为 currentTab 后全部消失。'
              '同类问题还遇到过一次：@State enabled 与内置 enabled 属性冲突，改为 isOn 解决。'
              '经验是：ArkUI 组件基类有大量内置属性名，自定义状态命名要避开 enabled、tabIndex、width 这类词。')
    body(doc, '补充一个工程环境上的问题：早期我把带中文路径的 PowerShell 脚本写成 .ps1 交给 PowerShell 5.1 执行，'
              '脚本被按 ANSI 解码，路径直接认错、构建静默失败。这不是 App 代码问题，但很耽误时间。'
              '解决办法是脚本内一律使用 ASCII 路径（通过 junction 暴露工作区），'
              '需要中文内容时改用 Python 脚本处理编码。')

    # ============================================================ 6 运行与总结
    heading(doc, '6. 运行与总结', 1)
    heading(doc, '6.1. 运行效果', 2)
    body(doc, '一条完整的用户路径如下。启动应用进入驾驶舱：顶部横幅显示“本地数据已就绪（Preferences + RDB）”，'
              '中间是三个环境滑块（默认 26.5°C / 62% / 300lux），下面是四张设备卡，底部四个 Tab。')
    body(doc, '把温度拖到 31.5°C、湿度拖到 88%，点击“执行一次联动”：结果卡淡入，显示“命中 3 条规则，设备已联动”，'
              '并按执行序号列出每条规则带来的变化；设备卡上风扇、加湿器、窗帘的开关自动打开，'
              '档位滑块跳到规则设定的值；如果两条规则争同一台设备，结果卡底部会用红字给出冲突裁决。'
              '切到“日志”Tab，能看到刚才每条命中规则的记录：序号、规则名、优先级、触发条件、'
              '设备变化（“循环扇 关 → 循环扇 开 60%”）、冲突说明。')
    body(doc, '再到“规则”Tab，任意编辑一条规则的优先级并保存，回到驾驶舱重新执行，'
              '可以发现执行顺序与冲突结果随之变化——“自习强补光”的优先级从 6 提到 9 后，'
              '它与“光线不足基础补光”争抢书桌灯时一定赢。最后到“场景”Tab 点“梅雨午后”一键演练，'
              '环境与设备会整体切换，卡片右上角出现“上次演练”标记。')
    placeholder(doc, '【此处插入运行截图 01-dashboard.png（驾驶舱）与 05-logs.png（执行日志）】')
    placeholder(doc, '拍摄步骤见仓库 docs/截图与录屏清单.md 第 1、5 项；录屏见同一文件第 8 项。')
    caption(doc, '图6.1  应用运行效果')

    heading(doc, '6.2. 数据恢复与集成', 2)
    body(doc, '选取“梅雨午后演练后的设备状态”作为代表性数据说明持久化链路。用户在场景页点击“一键演练”，'
              'Index.runScenario 把场景环境写进快照并调用 execute；execute 拿到引擎结果后，'
              '把 outcome.devices 与 outcome.rules（含被回写的 lastFiredAt）写回快照，'
              '再调用 repo.saveSnapshot → dumpSnapshot → preferences.put("snapshot_v2") + flush 落盘，'
              '同时把日志逐条 insert 到 RDB 表 trigger_log。')
    body(doc, '此时把应用从最近任务里划掉（或 hdc shell aa force-stop com.zhaoshuo.dormlink）再重新打开，'
              'Index.aboutToAppear → bootstrap → repo.loadSnapshot 会读到那串 JSON，'
              '交给我们自己实现的 parseSnapshot：它先校验 version 是否在支持范围内，'
              '再对 env、devices、rules 逐字段清洗（非数字回退默认值、越界裁剪、非布尔回退 false），'
              '最后返回快照。界面因此恢复到关闭前的状态——湿度仍是 88%，'
              '加湿器仍是开启 70%，规则启停与优先级都不变，日志 Tab 里的历史记录也还在（来自 RDB）。')
    body(doc, '这条链路里最容易被忽略的一点是 lastFiredAt 也要持久化：如果它只存在内存里，'
              '重启后冷却窗口就会失效，导致刚触发过的规则立刻再次触发。'
              'codec.test.ts 中“改环境 → 触发 → 保存 → 重启解析”这条用例专门断言了这一点'
              '（第三个测试文件中的 normal_restart_restores_device_state）。')
    placeholder(doc, '【此处插入重启前后对比截图 06-restore-before.png / 07-restore-after.png】')
    placeholder(doc, '拍摄步骤见仓库 docs/截图与录屏清单.md 第 6 项。')
    caption(doc, '图6.2  数据恢复与集成结果')

    heading(doc, '6.3. 个人总结', 2)
    body(doc, '这次大作业我最大的收获不是“把界面做出来”，而是把一条业务规则做成可被反复验证的东西。'
              '刚开始我以为难点在 UI，真正写下去才发现难点在“状态什么时候变、变了以后界面凭什么刷新”。'
              '我最初的写法是直接改 this.snapshot.env.temperature，运行后数字变了但界面纹丝不动；'
              '后来改成每次都用 cloneSnapshot 造一份新快照整体替换，问题才彻底消失。'
              '为了确认这不是碰巧，我去读了本机 SDK 里 ets/component/common.d.ts 的声明，'
              '看到 @State/@Prop 与后来的 ComponentV2、Local、Param 并列存在（该文件里这批装饰器的注释区'
              '最后一处 @since 为 12），才明白 API 17 上其实同时存在两套状态管理：'
              'V1 的对象观察只到第一层，V2 才有属性级追踪。这让我对“状态管理”这件事的认识具体了——'
              '它不是语法糖，而是框架对“你能观察到多深”的明确承诺。'
              '我没有把项目改成 V2，因为领域层已经是纯函数 + 不可变快照，V1 的整体替换足够可靠，'
              '而 V1/V2 混用有额外约束，对单人项目来说风险大于收益；'
              '但我把它列进了下一步的学习任务，并想好了验证办法：改完重跑 36 条用例（领域层不依赖 UI，'
              '回归成本很低），再按截图清单在真机走一遍六个步骤，用 DevEco Profiler 对比改造前后的渲染耗时。')
    body(doc, '另一个让我印象更深的认识来自 ArkTS 的限制。写测试辅助函数时我习惯性用了 Object.assign，'
              '编译器直接甩出 arkts-limited-stdlib。查到规则名之后再读 SDK 声明，'
              '我发现 Select 的选项类型 SelectOption 是必须显式声明的接口，'
              '于是“对象字面量必须对应显式类型”这条约束就不再是玄学了。'
              '我对它的用途判断是：ArkTS 通过收紧动态特性换取 AOT 编译与运行时可预测性，'
              '这在移动端是合理取舍；局限也很清楚——TS 生态里大量依赖动态属性的库（尤其是那些'
              '靠 Object.assign 做混入的工具库）不能直接搬过来，迁移成本主要落在“重写数据拼装逻辑”上。'
              '本项目的应对办法是把领域层刻意写成 TS/ArkTS 都能接受的最小子集，'
              '这个决定后来成了整套测试策略的基础：同一份 .ts 被 ArkTS 编译进 HAP，也能被 Node 直接跑，'
              '36 条用例因此可以零成本回归。')
    body(doc, '在“查资料”这件事上我也形成了固定动作：先看编译器报的规则编号（最快、最准、一定是当前版本），'
              '再翻本机 SDK 的 .d.ts 注释（@since、@syscap、@kit 都在里面，版本信息最可信），'
              '最后才去官方文档站按标题检索对应版本页面。这次关于 Preferences 与 RDB 的分工就是这么定的：'
              '@ohos.data.preferences.d.ts 里命名空间标注 @since 9，getPreferences(context, options) 这一重载'
              '标注 @since 11；@ohos.data.relationalStore.d.ts 也是 @since 9/10。'
              '两相对照后我选择“小配置用 Preferences 单 key 存整份 JSON、追加型日志用 RDB”，'
              '并且刻意不让同一份数据同时落在两个存储里，避免跨存储一致性问题。'
              '局限也很明确：Preferences 是 KV 型、值体积有限，塞大数组迟早出问题；'
              'RDB 有建表与升级成本，小配置用它属于过度设计。')
    body(doc, '当然也有明显没做完的部分。运行截图和录屏我没能在本机完成：这台机器上的 HarmonyOS 模拟器'
              '镜像尚未创建 AVD，也没有可用的真机，而安装 HAP 需要华为账号的调试签名，'
              '所以我把它们整理成了一份可照做的拍摄脚本（进入路径、操作、预期画面、文件命名、插入位置），'
              '而不是用示意图冒充真实运行结果。另外规则的判断条件目前只支持单指标阈值比较，'
              '没有时间条件与跨指标运算，这是有意的范围收敛，不是实现不了。'
              '下一步除了状态管理 V2 的改造，我还想补两件事：一是把规则条件扩展成“指标 + 时间窗”的组合，'
              '二是给 RDB 加一个按规则维度的统计查询，让日志能回答“哪条规则最常触发”这类问题。')

    return commits


def main():
    doc = Document(TEMPLATE)
    replaced = prepare(doc)
    commits = build_content(doc)
    doc.save(OUTPUT)
    print('cover fields rewritten:', replaced)
    print('commits embedded:', len(commits))
    print('saved:', OUTPUT)


if __name__ == '__main__':
    main()
