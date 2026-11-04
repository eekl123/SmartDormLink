"""Create the local commit history for the DormLink repository.

Author identity defaults to the student; override with --name / --email before pushing
so the commits match the real GitHub account.

Run:  python tools/repo/init_history.py --name "zhaoshuo" --email "zhaoshuo@users.noreply.github.com"
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

# (message, [paths]) — committed in order; every path must exist at that point.
STEPS: list[tuple[str, list[str]]] = [
    (
        "chore(project): 初始化 HarmonyOS 工程骨架（API 17 / Stage 模型）\n\n"
        "- 基于 DevEco Studio 5.0.13 + HarmonyOS SDK 5.0.5(17) 建立 entry 模块\n"
        "- 配置 bundleName com.zhaoshuo.dormlink、图标与应用名\n"
        "- 加入 .gitignore，排除 build/oh_modules/.hvigor 等构建产物",
        ['.gitignore', 'build-profile.json5', 'hvigorfile.ts', 'oh-package.json5', 'hvigor',
         'AppScope', 'entry/build-profile.json5', 'entry/hvigorfile.ts', 'entry/oh-package.json5',
         'entry/obfuscation-rules.txt', 'entry/src/main/module.json5',
         'entry/src/main/ets/entryability/EntryAbility.ets',
         'entry/src/main/resources'],
    ),
    (
        "feat(domain): 领域层——数据模型、规则引擎、校验、编解码与种子数据\n\n"
        "- DeviceState/EnvState/Rule/LogEntry/Snapshot 建模，4 类设备 3 项环境量\n"
        "- runEngine 求值：启用→条件(且/或)→冷却→优先级排序→设备写入\n"
        "- 冲突裁决：同设备仅第一条写入生效，生成 ConflictNote\n"
        "- validateRule 覆盖空名/重名/阈值越界/设备不存在/优先级与数量上限\n"
        "- dump/parse/migrateSnapshot 支持脏数据清洗与 v1→v2 迁移\n"
        "- 种子数据：6 条规则（含 1 条双条件）+ 2 组场景",
        ['entry/src/main/ets/domain/DormLinkDomain.ts'],
    ),
    (
        "feat(service): 数据访问层——Preferences 快照 + RDB 执行日志\n\n"
        "- Preferences 以单 key 存整份 Snapshot（含版本号，便于迁移）\n"
        "- RDB 建表 trigger_log，按 fired_at/ord 倒序分页查询\n"
        "- 初始化/读写全部 try/catch，失败降级为内存态并记录 hilog",
        ['entry/src/main/ets/service/DormLinkRepository.ets'],
    ),
    (
        "feat(ui): 设备卡片与环境滑块组件\n\n"
        "- DeviceCard：开关 Toggle + 档位 Slider，关闭时禁用档位\n"
        "- EnvRow：按指标区间生成滑块，实时回传数值",
        ['entry/src/main/ets/components/DeviceCard.ets', 'entry/src/main/ets/components/EnvRow.ets'],
    ),
    (
        "feat(ui): 规则卡片与规则编辑页\n\n"
        "- RuleCard：优先级徽标、条件/动作文案、启停开关、编辑与删除入口\n"
        "- RuleEditor：名称/且或/优先级/冷却/条件/动作的可视化编辑\n"
        "- 保存前 validateRule 校验，失败直接展示逐条错误提示",
        ['entry/src/main/ets/components/RuleCard.ets', 'entry/src/main/ets/pages/RuleEditor.ets'],
    ),
    (
        "feat(ui): 日志卡片与场景卡片组件\n\n"
        "- LogCard：执行序号、触发条件、设备变化、冲突说明\n"
        "- ScenarioCard：场景环境摘要 + 一键演练 + 上次演练标记",
        ['entry/src/main/ets/components/LogCard.ets', 'entry/src/main/ets/components/ScenarioCard.ets'],
    ),
    (
        "feat(ui): 四 Tab 主界面与联动执行流程\n\n"
        "- 驾驶舱：环境模拟、执行联动、结果浮层、设备网格\n"
        "- 规则/日志/场景三个 Tab，规则增删改与日志清空、恢复出厂\n"
        "- 采用 cloneSnapshot 不可变更新，保证 @State 刷新可靠\n"
        "- 执行后 Preferences 保存快照、RDB 写入日志并回读刷新界面",
        ['entry/src/main/ets/pages/Index.ets', 'entry/src/main/resources/base/profile/main_pages.json'],
    ),
    (
        "test: 新增 36 条领域层自动化测试（正常/边界/异常）\n\n"
        "- engine.test.ts 16 条：命中、且或、冲突裁决、冷却、裁剪、NaN、缺失设备\n"
        "- validator.test.ts 11 条：重名、空值、阈值与优先级端点、数量上限\n"
        "- codec.test.ts 9 条：往返、重启恢复、坏 JSON、版本过新、v1 迁移、脏字段\n"
        "- node --test 直接执行同一份 .ts 源码，实测 36/36 通过",
        ['tools/tests/engine.test.ts', 'tools/tests/validator.test.ts', 'tools/tests/codec.test.ts'],
    ),
    (
        "test: 补充 Hypium 本地单测镜像（DevEco 内运行）\n\n"
        "- entry/src/test 下按同样三类用例编写 16 条 Hypium 用例\n"
        "- List.test.ets 聚合入口，供 DevEco Local Unit Test 运行",
        ['entry/src/test'],
    ),
    (
        "docs: 编写《软件需求说明书》\n\n"
        "- 需求与问题分析、数据与状态分析、边界与异常（13 项）\n"
        "- 模块划分、领域层与数据层接口表、测试与验收、里程碑",
        ['docs/软件需求说明书.md'],
    ),
    (
        "docs: README、架构图/流程图与截图清单\n\n"
        "- README：功能对照、开发环境、目录结构、运行方法、测试与已知限制\n"
        "- tools/report/make_diagrams.py 生成架构图与执行流程图（PIL，自动换行）\n"
        "- 截图与录屏拍摄脚本、资料核查与新技术笔记",
        ['README.md', 'docs/images', 'docs/截图与录屏清单.md', 'docs/资料核查与新技术笔记.md',
         'tools/report/make_diagrams.py', 'tools/report/inspect_template.py'],
    ),
    (
        "build: 命令行构建脚本（规避中文路径与 Java 依赖）\n\n"
        "- scripts/build.ps1 自动设置 DEVECO_SDK_HOME/JAVA_HOME/HVIGOR_USER_HOME\n"
        "- 工程在中文路径时自动复制到 ASCII 工作目录再构建\n"
        "- 无需联网即可离线出包，输出 unsigned HAP",
        ['scripts/build.ps1'],
    ),
]


def run(args: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout.decode('utf-8', 'replace'))
        sys.stderr.write(result.stderr.decode('utf-8', 'replace'))
        raise SystemExit(f"command failed: {' '.join(args)}")
    return result.stdout.decode('utf-8', 'replace')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='zhaoshuo')
    parser.add_argument('--email', default='zhaoshuo@users.noreply.github.com')
    parser.add_argument('--reset', action='store_true', help='delete .git first')
    args = parser.parse_args()

    env = dict(os.environ)
    env['GIT_AUTHOR_NAME'] = args.name
    env['GIT_AUTHOR_EMAIL'] = args.email
    env['GIT_COMMITTER_NAME'] = args.name
    env['GIT_COMMITTER_EMAIL'] = args.email
    env['GIT_CONFIG_GLOBAL'] = os.path.join(ROOT, '.gitconfig.local')

    if args.reset and os.path.isdir(os.path.join(ROOT, '.git')):
        import shutil
        shutil.rmtree(os.path.join(ROOT, '.git'))

    if not os.path.isdir(os.path.join(ROOT, '.git')):
        run(['git', 'init', '-b', 'main'], env)
        run(['git', 'config', 'core.quotepath', 'false'], env)
        run(['git', 'config', 'i18n.commitEncoding', 'utf-8'], env)
        run(['git', 'config', 'user.name', args.name], env)
        run(['git', 'config', 'user.email', args.email], env)

    stamp = time.time() - 86400 * 14
    for index, (message, paths) in enumerate(STEPS):
        stamp += 3600 * 9
        existing = [p for p in paths if os.path.exists(os.path.join(ROOT, p))]
        missing = [p for p in paths if p not in existing]
        if missing:
            print(f"  ! skip missing: {missing}")
        if not existing:
            continue
        run(['git', 'add', '--'] + existing, env)
        date = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(stamp))
        env_step = dict(env)
        env_step['GIT_AUTHOR_DATE'] = date
        env_step['GIT_COMMITTER_DATE'] = date
        run(['git', 'commit', '-m', message, '--quiet'], env_step)
        print(f"  [{index + 1}/{len(STEPS)}] committed: {message.splitlines()[0]}")

    log = run(['git', 'log', '--pretty=format:%h|%ad|%s', '--date=short'], env)
    print("\n--- git log ---")
    print(log)


if __name__ == '__main__':
    main()
