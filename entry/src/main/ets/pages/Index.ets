import { common } from '@kit.AbilityKit';
import { promptAction, router } from '@kit.ArkUI';
import { DormLinkRepository } from '../service/DormLinkRepository';
import {
  DeviceState,
  EngineOutcome,
  EnvState,
  LogEntry,
  METRIC_META,
  MetricMeta,
  Rule,
  Scenario,
  Snapshot,
  cloneSnapshot,
  defaultSnapshot,
  findDevice,
  findRule,
  removeRule,
  replaceDevice,
  runEngine,
  seedScenarios,
  upsertRule
} from '../domain/DormLinkDomain';
import { DeviceCard } from '../components/DeviceCard';
import { EnvRow } from '../components/EnvRow';
import { RuleCard } from '../components/RuleCard';
import { LogCard } from '../components/LogCard';
import { ScenarioCard } from '../components/ScenarioCard';

const ACCENT: string = '#2F6BFF';
const SURFACE: string = '#FFFFFF';
const BG: string = '#F4F6FB';
const TEXT_MAIN: string = '#1A1D26';
const TEXT_SUB: string = '#6B7280';
const DANGER: string = '#E5484D';
const SUCCESS: string = '#12A594';

interface EditorParams {
  ruleId: string;
}

@Entry
@Component
struct Index {
  @State snapshot: Snapshot = defaultSnapshot(0);
  @State logs: LogEntry[] = [];
  @State currentTab: number = 0;
  @State loaded: boolean = false;
  @State storageNote: string = '正在加载本地数据…';
  @State resultTitle: string = '';
  @State resultDetail: string = '';
  @State resultConflict: string = '';
  @State showResult: boolean = false;
  @State activeScenarioId: string = '';

  private repo: DormLinkRepository = DormLinkRepository.getInstance();
  private scenarios: Scenario[] = seedScenarios();

  aboutToAppear(): void {
    this.bootstrap();
  }

  onPageShow(): void {
    if (this.loaded) {
      this.reload();
    }
  }

  /* ---------------- 数据装载 ---------------- */

  async bootstrap(): Promise<void> {
    const context = getContext(this) as common.UIAbilityContext;
    await this.repo.init(context);
    await this.reload();
    this.storageNote = this.repo.isStorageReady() ? '本地数据已就绪（Preferences + RDB）' : '存储不可用，当前为内存态';
    this.loaded = true;
  }

  async reload(): Promise<void> {
    const now = Date.now();
    this.snapshot = await this.repo.loadSnapshot(now);
    this.activeScenarioId = this.snapshot.activeScenarioId;
    this.logs = await this.repo.queryLogs(60);
  }

  async persist(): Promise<void> {
    const ok = await this.repo.saveSnapshot(this.snapshot);
    if (!ok) {
      promptAction.showToast({ message: '保存失败，请检查存储空间' });
    }
  }

  /* ---------------- 设备与环境 ---------------- */

  envValue(key: string): number {
    if (key === 'temperature') {
      return this.snapshot.env.temperature;
    }
    if (key === 'humidity') {
      return this.snapshot.env.humidity;
    }
    return this.snapshot.env.illuminance;
  }

  setEnv(next: EnvState, persist: boolean): void {
    const draft = cloneSnapshot(this.snapshot, Date.now());
    draft.env = next;
    this.snapshot = draft;
    if (persist) {
      this.persist();
    }
  }

  applyMetric(key: string, value: number, persist: boolean): void {
    const env = this.snapshot.env;
    let next: EnvState;
    if (key === 'temperature') {
      next = { temperature: Math.round(value * 10) / 10, humidity: env.humidity, illuminance: env.illuminance };
    } else if (key === 'humidity') {
      next = { temperature: env.temperature, humidity: Math.round(value), illuminance: env.illuminance };
    } else {
      next = { temperature: env.temperature, humidity: env.humidity, illuminance: Math.round(value) };
    }
    this.setEnv(next, persist);
  }

  updateDevice(id: string, power: boolean, level: number, persist: boolean): void {
    const device = findDevice(this.snapshot.devices, id);
    if (device === null) {
      return;
    }
    const next: DeviceState = {
      id: device.id,
      kind: device.kind,
      name: device.name,
      room: device.room,
      power: power,
      level: level
    };
    const draft = cloneSnapshot(this.snapshot, Date.now());
    draft.devices = replaceDevice(draft.devices, next);
    this.snapshot = draft;
    if (persist) {
      this.persist();
    }
  }

  /* ---------------- 规则 ---------------- */

  toggleRule(id: string, enabled: boolean): void {
    const rule = findRule(this.snapshot.rules, id);
    if (rule === null) {
      return;
    }
    const next: Rule = {
      id: rule.id,
      name: rule.name,
      enabled: enabled,
      logic: rule.logic,
      conditions: rule.conditions,
      actions: rule.actions,
      priority: rule.priority,
      cooldownSec: rule.cooldownSec,
      lastFiredAt: rule.lastFiredAt,
      updatedAt: Date.now()
    };
    const draft = cloneSnapshot(this.snapshot, Date.now());
    draft.rules = upsertRule(draft.rules, next);
    this.snapshot = draft;
    this.persist();
  }

  openEditor(ruleId: string): void {
    const params: EditorParams = { ruleId: ruleId };
    router.pushUrl({ url: 'pages/RuleEditor', params: params });
  }

  confirmDelete(ruleId: string): void {
    const rule = findRule(this.snapshot.rules, ruleId);
    if (rule === null) {
      return;
    }
    AlertDialog.show({
      title: '删除规则',
      message: `确定删除「${rule.name}」？该操作不可撤销。`,
      primaryButton: {
        value: '取消',
        action: () => {
        }
      },
      secondaryButton: {
        value: '删除',
        fontColor: DANGER,
        action: () => {
          const draft = cloneSnapshot(this.snapshot, Date.now());
          draft.rules = removeRule(draft.rules, ruleId);
          this.snapshot = draft;
          this.persist();
          promptAction.showToast({ message: '规则已删除' });
        }
      }
    });
  }

  /* ---------------- 联动执行 ---------------- */

  execute(source: string): void {
    const outcome: EngineOutcome = runEngine({
      rules: this.snapshot.rules,
      devices: this.snapshot.devices,
      env: this.snapshot.env,
      now: Date.now(),
      source: source
    });

    const draft = cloneSnapshot(this.snapshot, Date.now());
    draft.devices = outcome.devices;
    draft.rules = outcome.rules;
    this.snapshot = draft;

    let title = '';
    if (outcome.firedCount === 0) {
      title = '本次没有规则被满足，设备保持不变';
    } else {
      title = `命中 ${outcome.firedCount} 条规则，设备已联动`;
    }
    let detail = '';
    for (let i = 0; i < outcome.logs.length && i < 4; i++) {
      const log = outcome.logs[i];
      if (detail.length > 0) {
        detail += '\n';
      }
      detail += `#${log.order} ${log.ruleName}：${log.changesText}`;
    }
    if (detail.length === 0) {
      detail = '可拖动环境滑块或套用场景后再试。';
    }

    const conflictTexts: string[] = [];
    for (let i = 0; i < outcome.conflicts.length; i++) {
      const c = outcome.conflicts[i];
      conflictTexts.push(`${c.deviceName}：${c.winnerRuleName} 优先于 ${c.loserRuleName}`);
    }

    this.resultTitle = title;
    this.resultDetail = detail;
    this.resultConflict = conflictTexts.join('；');
    animateTo({ duration: 260, curve: Curve.EaseOut }, () => {
      this.showResult = true;
    });

    this.persist();
    this.appendLogs(outcome.logs);
  }

  async appendLogs(entries: LogEntry[]): Promise<void> {
    if (entries.length > 0) {
      await this.repo.appendLogs(entries);
    }
    this.logs = await this.repo.queryLogs(60);
  }

  runScenario(scenarioId: string): void {
    let picked: Scenario | null = null;
    for (let i = 0; i < this.scenarios.length; i++) {
      if (this.scenarios[i].id === scenarioId) {
        picked = this.scenarios[i];
      }
    }
    if (picked === null) {
      return;
    }
    const draft = cloneSnapshot(this.snapshot, Date.now());
    draft.env = picked.env;
    draft.activeScenarioId = picked.id;
    this.snapshot = draft;
    this.activeScenarioId = picked.id;
    this.execute('scenario');
    promptAction.showToast({ message: `已套用「${picked.name}」并完成演练` });
  }

  clearLogs(): void {
    AlertDialog.show({
      title: '清空日志',
      message: '将删除 RDB 中的全部执行记录，确定继续？',
      primaryButton: {
        value: '取消',
        action: () => {
        }
      },
      secondaryButton: {
        value: '清空',
        fontColor: DANGER,
        action: () => {
          this.doClearLogs();
        }
      }
    });
  }

  async doClearLogs(): Promise<void> {
    await this.repo.clearLogs();
    this.logs = [];
    promptAction.showToast({ message: '执行日志已清空' });
  }

  resetAll(): void {
    AlertDialog.show({
      title: '恢复出厂',
      message: '将清空规则、设备状态与日志并恢复默认配置，确定继续？',
      primaryButton: {
        value: '取消',
        action: () => {
        }
      },
      secondaryButton: {
        value: '恢复',
        fontColor: DANGER,
        action: () => {
          this.doResetAll();
        }
      }
    });
  }

  async doResetAll(): Promise<void> {
    const fresh = await this.repo.resetAll(Date.now());
    this.snapshot = fresh;
    this.logs = [];
    this.activeScenarioId = '';
    this.showResult = false;
    promptAction.showToast({ message: '已恢复默认配置' });
  }

  runningCount(): number {
    let count = 0;
    for (let i = 0; i < this.snapshot.devices.length; i++) {
      if (this.snapshot.devices[i].power) {
        count++;
      }
    }
    return count;
  }

  enabledCount(): number {
    let count = 0;
    for (let i = 0; i < this.snapshot.rules.length; i++) {
      if (this.snapshot.rules[i].enabled) {
        count++;
      }
    }
    return count;
  }

  /* ---------------- 视图 ---------------- */

  @Builder
  tabItem(title: string, tabIdx: number) {
    Column({ space: 2 }) {
      Text(title)
        .fontSize(12)
        .fontColor(this.currentTab === tabIdx ? ACCENT : '#8A90A2')
        .fontWeight(this.currentTab === tabIdx ? FontWeight.Medium : FontWeight.Normal)
    }
    .justifyContent(FlexAlign.Center)
    .height('100%')
    .width('100%')
  }

  @Builder
  storageBanner() {
    Row({ space: 6 }) {
      Text(this.storageNote)
        .fontSize(11)
        .fontColor(this.repo.isStorageReady() ? SUCCESS : DANGER)
        .layoutWeight(1)
      Button('恢复出厂')
        .fontSize(11)
        .height(26)
        .backgroundColor('#F1F3F9')
        .fontColor(TEXT_SUB)
        .onClick(() => {
          this.resetAll();
        })
    }
    .width('100%')
    .padding({ left: 12, right: 12, top: 8, bottom: 8 })
    .borderRadius(10)
    .backgroundColor(SURFACE)
  }

  @Builder
  dashboard() {
    Scroll() {
      Column({ space: 12 }) {
        this.storageBanner()

        Column({ space: 10 }) {
          Row() {
            Text('环境模拟').fontSize(15).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
            Blank()
            Text('拖动滑块修改 Mock 数据').fontSize(11).fontColor(TEXT_SUB)
          }
          .width('100%')

          ForEach(METRIC_META, (meta: MetricMeta) => {
            EnvRow({
              meta: meta,
              value: this.envValue(meta.key),
              onValueChange: (key: string, value: number) => {
                this.applyMetric(key, value, false);
              }
            })
          }, (meta: MetricMeta) => meta.key)

          Button('执行一次联动')
            .width('100%')
            .height(42)
            .fontSize(15)
            .backgroundColor(ACCENT)
            .onClick(() => {
              this.execute('manual');
            })
        }
        .width('100%')
        .padding(14)
        .borderRadius(16)
        .backgroundColor(SURFACE)
        .shadow({ radius: 14, color: '#0F1A3D14', offsetY: 6 })

        if (this.showResult) {
          Column({ space: 6 }) {
            Row() {
              Text(this.resultTitle).fontSize(13).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
              Blank()
              Text('收起')
                .fontSize(11)
                .fontColor(TEXT_SUB)
                .onClick(() => {
                  this.showResult = false;
                })
            }
            .width('100%')

            Text(this.resultDetail).fontSize(12).fontColor('#4A5163').width('100%')
            if (this.resultConflict.length > 0) {
              Text(`冲突裁决：${this.resultConflict}`).fontSize(11).fontColor(DANGER).width('100%')
            }
          }
          .width('100%')
          .padding(12)
          .borderRadius(14)
          .backgroundColor('#F0F5FF')
          .transition(TransitionEffect.OPACITY.animation({ duration: 200 }))
        }

        Column({ space: 10 }) {
          Row() {
            Text('设备状态').fontSize(15).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
            Blank()
            Text(`${this.runningCount()}/${this.snapshot.devices.length} 台运行中`)
              .fontSize(11)
              .fontColor(TEXT_SUB)
          }
          .width('100%')

          Grid() {
            ForEach(this.snapshot.devices, (device: DeviceState) => {
              GridItem() {
                DeviceCard({
                  device: device,
                  onPowerChange: (id: string, power: boolean) => {
                    const target = findDevice(this.snapshot.devices, id);
                    if (target !== null) {
                      this.updateDevice(id, power, target.level, true);
                    }
                  },
                  onLevelChange: (id: string, level: number) => {
                    const target = findDevice(this.snapshot.devices, id);
                    if (target !== null) {
                      this.updateDevice(id, target.power, level, false);
                    }
                  }
                })
              }
            }, (device: DeviceState) => `${device.id}_${device.power}_${device.level}`)
          }
          .columnsTemplate('1fr 1fr')
          .columnsGap(10)
          .rowsGap(10)
          .height(360)
        }
        .width('100%')
        .padding(14)
        .borderRadius(16)
        .backgroundColor('#EFF2F9')
      }
      .width('100%')
      .padding({ left: 14, right: 14, top: 12, bottom: 24 })
    }
    .scrollBar(BarState.Off)
    .width('100%')
    .height('100%')
  }

  @Builder
  rulesPage() {
    Column({ space: 10 }) {
      Row() {
        Column({ space: 2 }) {
          Text('自动化规则').fontSize(16).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
          Text(`${this.enabledCount()} 条启用 / 共 ${this.snapshot.rules.length} 条（上限 12 条）`)
            .fontSize(11)
            .fontColor(TEXT_SUB)
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1)

        Button('新建')
          .height(34)
          .fontSize(13)
          .backgroundColor(ACCENT)
          .onClick(() => {
            this.openEditor('');
          })
      }
      .width('100%')
      .padding({ left: 14, right: 14, top: 12 })

      List({ space: 10 }) {
        ForEach(this.snapshot.rules, (rule: Rule) => {
          ListItem() {
            RuleCard({
              rule: rule,
              devices: this.snapshot.devices,
              onToggle: (id: string, enabled: boolean) => {
                this.toggleRule(id, enabled);
              },
              onEdit: (id: string) => {
                this.openEditor(id);
              },
              onDelete: (id: string) => {
                this.confirmDelete(id);
              }
            })
          }
        }, (rule: Rule) => `${rule.id}_${rule.updatedAt}_${rule.enabled}`)
      }
      .width('100%')
      .layoutWeight(1)
      .padding({ left: 14, right: 14 })
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  logsPage() {
    Column({ space: 10 }) {
      Row() {
        Column({ space: 2 }) {
          Text('执行日志').fontSize(16).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
          Text(`RDB 中最近 ${this.logs.length} 条记录，按触发时间倒序`)
            .fontSize(11)
            .fontColor(TEXT_SUB)
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1)

        Button('清空')
          .height(34)
          .fontSize(13)
          .backgroundColor('#FDECEC')
          .fontColor(DANGER)
          .onClick(() => {
            this.clearLogs();
          })
      }
      .width('100%')
      .padding({ left: 14, right: 14, top: 12 })

      if (this.logs.length === 0) {
        Column({ space: 8 }) {
          Text('还没有执行记录').fontSize(14).fontColor(TEXT_SUB)
          Text('去「驾驶舱」拖动环境滑块并执行联动，或到「场景」一键演练')
            .fontSize(12)
            .fontColor('#A8ADBC')
            .textAlign(TextAlign.Center)
        }
        .width('100%')
        .padding(40)
        .justifyContent(FlexAlign.Center)
      } else {
        List({ space: 8 }) {
          ForEach(this.logs, (entry: LogEntry, index: number) => {
            ListItem() {
              LogCard({ entry: entry, index: index })
            }
          }, (entry: LogEntry) => entry.id)
        }
        .width('100%')
        .layoutWeight(1)
        .padding({ left: 14, right: 14 })
        .scrollBar(BarState.Off)
      }
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  scenariosPage() {
    Scroll() {
      Column({ space: 12 }) {
        Column({ space: 4 }) {
          Text('场景演练').fontSize(16).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
          Text('套用一组 Mock 环境数据，立即观察规则命中、设备联动与冲突裁决')
            .fontSize(11)
            .fontColor(TEXT_SUB)
        }
        .alignItems(HorizontalAlign.Start)
        .width('100%')

        ForEach(this.scenarios, (scenario: Scenario) => {
          ScenarioCard({
            scenario: scenario,
            activeId: this.activeScenarioId,
            onRun: (id: string) => {
              this.runScenario(id);
            }
          })
        }, (scenario: Scenario) => scenario.id)

        Column({ space: 6 }) {
          Text('冲突处理策略').fontSize(13).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
          Text('1. 命中的规则按优先级从高到低排序，优先级相同则按规则编号升序')
            .fontSize(11)
            .fontColor(TEXT_SUB)
          Text('2. 同一台设备只接受第一条写入，后续写入被丢弃并记录冲突')
            .fontSize(11)
            .fontColor(TEXT_SUB)
          Text('3. 每条命中的规则都会写入 RDB 日志，含触发条件、设备变化和执行序号')
            .fontSize(11)
            .fontColor(TEXT_SUB)
        }
        .alignItems(HorizontalAlign.Start)
        .width('100%')
        .padding(14)
        .borderRadius(14)
        .backgroundColor('#FFF8E8')
      }
      .width('100%')
      .padding({ left: 14, right: 14, top: 12, bottom: 24 })
    }
    .scrollBar(BarState.Off)
    .width('100%')
    .height('100%')
  }

  build() {
    Column() {
      Row() {
        Text('智舍联动站').fontSize(18).fontWeight(FontWeight.Bold).fontColor(TEXT_MAIN)
        Blank()
        Text('DormLink v1.0').fontSize(11).fontColor(TEXT_SUB)
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 10, bottom: 8 })

      Tabs({ barPosition: BarPosition.End, index: this.currentTab }) {
        TabContent() {
          this.dashboard()
        }.tabBar(this.tabItem('驾驶舱', 0))

        TabContent() {
          this.rulesPage()
        }.tabBar(this.tabItem('规则', 1))

        TabContent() {
          this.logsPage()
        }.tabBar(this.tabItem('日志', 2))

        TabContent() {
          this.scenariosPage()
        }.tabBar(this.tabItem('场景', 3))
      }
      .barHeight(52)
      .layoutWeight(1)
      .onChange((index: number) => {
        this.currentTab = index;
      })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(BG)
  }
}
