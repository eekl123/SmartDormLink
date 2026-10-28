import { common } from '@kit.AbilityKit';
import { promptAction, router } from '@kit.ArkUI';
import { DormLinkRepository } from '../service/DormLinkRepository';
import {
  COMPARE_OPS,
  CompareOp,
  Condition,
  DeviceAction,
  DeviceState,
  METRIC_META,
  MetricMeta,
  Rule,
  METRIC_KEYS,
  MetricKey,
  ValidationIssue,
  canAddRule,
  createDraftRule,
  findRule,
  metricMeta,
  opSymbol,
  upsertRule,
  validateRule
} from '../domain/DormLinkDomain';

const ACCENT: string = '#2F6BFF';
const TEXT_MAIN: string = '#1A1D26';
const TEXT_SUB: string = '#6B7280';
const DANGER: string = '#E5484D';

interface EditorParams {
  ruleId: string;
}

@Entry
@Component
struct RuleEditor {
  @State rule: Rule = createDraftRule(0, '');
  @State issues: ValidationIssue[] = [];
  @State devices: DeviceState[] = [];
  @State allRules: Rule[] = [];
  @State loaded: boolean = false;
  @State isNew: boolean = true;

  private repo: DormLinkRepository = DormLinkRepository.getInstance();

  aboutToAppear(): void {
    this.loadDraft();
  }

  async loadDraft(): Promise<void> {
    const context = getContext(this) as common.UIAbilityContext;
    await this.repo.init(context);
    const snapshot = await this.repo.loadSnapshot(Date.now());
    this.devices = snapshot.devices;
    this.allRules = snapshot.rules;

    const params = router.getParams() as EditorParams;
    const ruleId: string = params === null || params === undefined ? '' : params.ruleId;
    const existing = findRule(snapshot.rules, ruleId);
    if (existing === null) {
      this.rule = createDraftRule(Date.now(), this.newRuleId());
      this.isNew = true;
    } else {
      this.rule = existing;
      this.isNew = false;
    }
    this.loaded = true;
  }

  newRuleId(): string {
    const stamp: number = Date.now();
    const salt: number = Math.floor(Math.random() * 1000);
    return `rule_${stamp}_${salt}`;
  }

  /* ---------------- 不可变修改 ---------------- */

  patchRule(next: Rule): void {
    this.rule = next;
  }

  patchName(name: string): void {
    this.patchRule({
      id: this.rule.id,
      name: name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: this.rule.conditions,
      actions: this.rule.actions,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  patchPriority(priority: number): void {
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: this.rule.conditions,
      actions: this.rule.actions,
      priority: Math.round(priority),
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  patchCooldown(seconds: number): void {
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: this.rule.conditions,
      actions: this.rule.actions,
      priority: this.rule.priority,
      cooldownSec: Math.round(seconds),
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  patchLogic(orLogic: boolean): void {
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: orLogic ? 'or' : 'and',
      conditions: this.rule.conditions,
      actions: this.rule.actions,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  patchCondition(index: number, next: Condition): void {
    const list: Condition[] = [];
    for (let i = 0; i < this.rule.conditions.length; i++) {
      list.push(i === index ? next : this.rule.conditions[i]);
    }
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: list,
      actions: this.rule.actions,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  addCondition(): void {
    if (this.rule.conditions.length >= 3) {
      promptAction.showToast({ message: '最多 3 条触发条件' });
      return;
    }
    const list: Condition[] = [];
    for (let i = 0; i < this.rule.conditions.length; i++) {
      list.push(this.rule.conditions[i]);
    }
    list.push({ metric: 'humidity', op: 'gte', value: 70 });
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: list,
      actions: this.rule.actions,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  removeCondition(index: number): void {
    if (this.rule.conditions.length <= 1) {
      promptAction.showToast({ message: '至少保留 1 条触发条件' });
      return;
    }
    const list: Condition[] = [];
    for (let i = 0; i < this.rule.conditions.length; i++) {
      if (i !== index) {
        list.push(this.rule.conditions[i]);
      }
    }
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: list,
      actions: this.rule.actions,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  patchAction(index: number, next: DeviceAction): void {
    const list: DeviceAction[] = [];
    for (let i = 0; i < this.rule.actions.length; i++) {
      list.push(i === index ? next : this.rule.actions[i]);
    }
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: this.rule.conditions,
      actions: list,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  addAction(): void {
    if (this.rule.actions.length >= 4) {
      promptAction.showToast({ message: '最多 4 条设备动作' });
      return;
    }
    const list: DeviceAction[] = [];
    for (let i = 0; i < this.rule.actions.length; i++) {
      list.push(this.rule.actions[i]);
    }
    const deviceId = this.devices.length > 0 ? this.devices[0].id : 'dev_fan';
    list.push({ deviceId: deviceId, power: true, level: 50 });
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: this.rule.conditions,
      actions: list,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  removeAction(index: number): void {
    if (this.rule.actions.length <= 1) {
      promptAction.showToast({ message: '至少保留 1 条设备动作' });
      return;
    }
    const list: DeviceAction[] = [];
    for (let i = 0; i < this.rule.actions.length; i++) {
      if (i !== index) {
        list.push(this.rule.actions[i]);
      }
    }
    this.patchRule({
      id: this.rule.id,
      name: this.rule.name,
      enabled: this.rule.enabled,
      logic: this.rule.logic,
      conditions: this.rule.conditions,
      actions: list,
      priority: this.rule.priority,
      cooldownSec: this.rule.cooldownSec,
      lastFiredAt: this.rule.lastFiredAt,
      updatedAt: Date.now()
    });
  }

  /* ---------------- 保存 ---------------- */

  async save(): Promise<void> {
    const deviceIds: string[] = [];
    for (let i = 0; i < this.devices.length; i++) {
      deviceIds.push(this.devices[i].id);
    }
    if (this.isNew && !canAddRule(this.allRules)) {
      this.issues = [{ field: 'rules', message: '规则数量已达上限 12 条，请先删除旧规则' }];
      return;
    }
    const result = validateRule(this.rule, this.allRules, deviceIds, this.rule.id);
    this.issues = result.issues;
    if (!result.ok) {
      promptAction.showToast({ message: `校验未通过：${result.issues[0].message}` });
      return;
    }

    const snapshot = await this.repo.loadSnapshot(Date.now());
    snapshot.rules = upsertRule(snapshot.rules, this.rule);
    const saved = await this.repo.saveSnapshot(snapshot);
    if (!saved) {
      promptAction.showToast({ message: '保存失败，请检查存储空间' });
      return;
    }
    promptAction.showToast({ message: this.isNew ? '规则已创建' : '规则已更新' });
    router.back();
  }

  /* ---------------- 视图 ---------------- */

  metricIndexOf(key: MetricKey): number {
    return METRIC_KEYS.indexOf(key);
  }

  opIndexOf(op: CompareOp): number {
    return COMPARE_OPS.indexOf(op);
  }

  deviceIndexOf(deviceId: string): number {
    for (let i = 0; i < this.devices.length; i++) {
      if (this.devices[i].id === deviceId) {
        return i;
      }
    }
    return 0;
  }

  deviceName(deviceId: string): string {
    for (let i = 0; i < this.devices.length; i++) {
      if (this.devices[i].id === deviceId) {
        return `${this.devices[i].name}（${this.devices[i].room}）`;
      }
    }
    return '未知设备';
  }

  @Builder
  sectionTitle(title: string, hint: string) {
    Row() {
      Text(title).fontSize(14).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
      Blank()
      Text(hint).fontSize(11).fontColor(TEXT_SUB)
    }
    .width('100%')
  }

  @Builder
  conditionEditor(cond: Condition, index: number) {
    Column({ space: 8 }) {
      Row() {
        Text(`条件 ${index + 1}`).fontSize(12).fontColor(TEXT_SUB)
        Blank()
        Text('删除')
          .fontSize(11)
          .fontColor(DANGER)
          .onClick(() => {
            this.removeCondition(index);
          })
      }
      .width('100%')

      Row({ space: 8 }) {
        Select(METRIC_META.map((m: MetricMeta): SelectOption => {
          return { value: m.label };
        }))
          .selected(this.metricIndexOf(cond.metric))
          .value(metricMeta(cond.metric).label)
          .font({ size: 13 })
          .layoutWeight(1)
          .onSelect((idx: number, value: string) => {
            const meta = METRIC_META[idx];
            const next: Condition = {
              metric: meta.key,
              op: cond.op,
              value: Math.min(cond.value, meta.max)
            };
            this.patchCondition(index, next);
          })

        Select(COMPARE_OPS.map((op: CompareOp): SelectOption => {
          return { value: opSymbol(op) };
        }))
          .selected(this.opIndexOf(cond.op))
          .value(opSymbol(cond.op))
          .font({ size: 13 })
          .width(74)
          .onSelect((idx: number, value: string) => {
            const next: Condition = { metric: cond.metric, op: COMPARE_OPS[idx], value: cond.value };
            this.patchCondition(index, next);
          })
      }
      .width('100%')

      Row() {
        Text(`${cond.value}${metricMeta(cond.metric).unit}`)
          .fontSize(13)
          .fontColor(ACCENT)
        Blank()
        Text(`范围 ${metricMeta(cond.metric).min}~${metricMeta(cond.metric).max}`)
          .fontSize(10)
          .fontColor('#A8ADBC')
      }
      .width('100%')

      Slider({
        value: cond.value,
        min: metricMeta(cond.metric).min,
        max: metricMeta(cond.metric).max,
        step: metricMeta(cond.metric).step,
        style: SliderStyle.OutSet
      })
        .selectedColor(ACCENT)
        .trackColor('#E7EAF3')
        .onChange((value: number, mode: SliderChangeMode) => {
          const next: Condition = { metric: cond.metric, op: cond.op, value };
          this.patchCondition(index, next);
        })
    }
    .width('100%')
    .padding(12)
    .borderRadius(12)
    .backgroundColor('#F7F9FE')
  }

  @Builder
  actionEditor(action: DeviceAction, index: number) {
    Column({ space: 8 }) {
      Row() {
        Text(`动作 ${index + 1}`).fontSize(12).fontColor(TEXT_SUB)
        Blank()
        Text('删除')
          .fontSize(11)
          .fontColor(DANGER)
          .onClick(() => {
            this.removeAction(index);
          })
      }
      .width('100%')

      Row({ space: 8 }) {
        Select(this.devices.map((d: DeviceState): SelectOption => {
          return { value: `${d.name}` };
        }))
          .selected(this.deviceIndexOf(action.deviceId))
          .value(this.deviceName(action.deviceId))
          .font({ size: 13 })
          .layoutWeight(1)
          .onSelect((idx: number, value: string) => {
            const device = this.devices[idx];
            const next: DeviceAction = { deviceId: device.id, power: action.power, level: action.level };
            this.patchAction(index, next);
          })

        Toggle({ type: ToggleType.Switch, isOn: action.power })
          .selectedColor(ACCENT)
          .onChange((isOn: boolean) => {
            const next: DeviceAction = { deviceId: action.deviceId, power: isOn, level: action.level };
            this.patchAction(index, next);
          })
      }
      .width('100%')

      Row() {
        Text(action.power ? `目标 ${action.level}%` : '目标 关闭')
          .fontSize(13)
          .fontColor(action.power ? ACCENT : TEXT_SUB)
        Blank()
      }
      .width('100%')

      Slider({ value: action.level, min: 0, max: 100, step: 1, style: SliderStyle.OutSet })
        .selectedColor(ACCENT)
        .trackColor('#E7EAF3')
        .enabled(action.power)
        .opacity(action.power ? 1 : 0.4)
        .onChange((value: number, mode: SliderChangeMode) => {
          const next: DeviceAction = { deviceId: action.deviceId, power: action.power, level: Math.round(value) };
          this.patchAction(index, next);
        })
    }
    .width('100%')
    .padding(12)
    .borderRadius(12)
    .backgroundColor('#F7F9FE')
  }

  build() {
    Column() {
      Row() {
        Text('← 返回')
          .fontSize(14)
          .fontColor(ACCENT)
          .onClick(() => {
            router.back();
          })
        Blank()
        Text(this.isNew ? '新建规则' : '编辑规则')
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor(TEXT_MAIN)
        Blank()
        Text('保存')
          .fontSize(14)
          .fontColor(ACCENT)
          .onClick(() => {
            this.save();
          })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 12, bottom: 10 })

      Scroll() {
        Column({ space: 12 }) {
          Column({ space: 8 }) {
            this.sectionTitle('基础信息', `${this.rule.conditions.length} 条件 / ${this.rule.actions.length} 动作`)
            TextInput({ text: this.rule.name, placeholder: '例如：高温启动循环扇' })
              .height(42)
              .fontSize(14)
              .maxLength(20)
              .onChange((value: string) => {
                this.patchName(value);
              })

            Row() {
              Text('条件组合').fontSize(12).fontColor(TEXT_SUB)
              Blank()
              Row({ space: 6 }) {
                Button('且')
                  .height(30)
                  .fontSize(12)
                  .backgroundColor(this.rule.logic === 'and' ? ACCENT : '#EEF2FF')
                  .fontColor(this.rule.logic === 'and' ? '#FFFFFF' : ACCENT)
                  .onClick(() => {
                    this.patchLogic(false);
                  })
                Button('或')
                  .height(30)
                  .fontSize(12)
                  .backgroundColor(this.rule.logic === 'or' ? ACCENT : '#EEF2FF')
                  .fontColor(this.rule.logic === 'or' ? '#FFFFFF' : ACCENT)
                  .onClick(() => {
                    this.patchLogic(true);
                  })
              }
            }
            .width('100%')

            Row() {
              Text(`优先级 P${this.rule.priority}`).fontSize(12).fontColor(TEXT_SUB)
              Blank()
              Text('数值越大越优先').fontSize(10).fontColor('#A8ADBC')
            }
            .width('100%')

            Slider({ value: this.rule.priority, min: 1, max: 10, step: 1, style: SliderStyle.OutSet })
              .selectedColor(ACCENT)
              .trackColor('#E7EAF3')
              .onChange((value: number, mode: SliderChangeMode) => {
                this.patchPriority(value);
              })

            Row() {
              Text(this.rule.cooldownSec > 0 ? `冷却 ${this.rule.cooldownSec} 秒` : '无冷却限制')
                .fontSize(12)
                .fontColor(TEXT_SUB)
              Blank()
            }
            .width('100%')

            Slider({ value: this.rule.cooldownSec, min: 0, max: 600, step: 10, style: SliderStyle.OutSet })
              .selectedColor(ACCENT)
              .trackColor('#E7EAF3')
              .onChange((value: number, mode: SliderChangeMode) => {
                this.patchCooldown(value);
              })
          }
          .width('100%')
          .padding(14)
          .borderRadius(16)
          .backgroundColor('#FFFFFF')

          Column({ space: 10 }) {
            Row() {
              Text('触发条件').fontSize(14).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
              Blank()
              Text('+ 添加条件')
                .fontSize(12)
                .fontColor(ACCENT)
                .onClick(() => {
                  this.addCondition();
                })
            }
            .width('100%')

            ForEach(this.rule.conditions, (cond: Condition, index: number) => {
              this.conditionEditor(cond, index)
            }, (cond: Condition, index: number) => `${index}_${cond.metric}_${cond.op}_${cond.value}`)
          }
          .width('100%')
          .padding(14)
          .borderRadius(16)
          .backgroundColor('#FFFFFF')

          Column({ space: 10 }) {
            Row() {
              Text('设备动作').fontSize(14).fontWeight(FontWeight.Medium).fontColor(TEXT_MAIN)
              Blank()
              Text('+ 添加动作')
                .fontSize(12)
                .fontColor(ACCENT)
                .onClick(() => {
                  this.addAction();
                })
            }
            .width('100%')

            ForEach(this.rule.actions, (action: DeviceAction, index: number) => {
              this.actionEditor(action, index)
            }, (action: DeviceAction, index: number) => `${index}_${action.deviceId}_${action.power}_${action.level}`)
          }
          .width('100%')
          .padding(14)
          .borderRadius(16)
          .backgroundColor('#FFFFFF')

          if (this.issues.length > 0) {
            Column({ space: 4 }) {
              Text('校验未通过').fontSize(13).fontWeight(FontWeight.Medium).fontColor(DANGER)
              ForEach(this.issues, (item: ValidationIssue) => {
                Text(`· ${item.message}`).fontSize(11).fontColor(DANGER).width('100%')
              }, (item: ValidationIssue) => item.field + item.message)
            }
            .alignItems(HorizontalAlign.Start)
            .width('100%')
            .padding(12)
            .borderRadius(12)
            .backgroundColor('#FDECEC')
          }

          Button(this.isNew ? '创建规则' : '保存修改')
            .width('100%')
            .height(44)
            .fontSize(15)
            .backgroundColor(ACCENT)
            .onClick(() => {
              this.save();
            })
        }
        .width('100%')
        .padding({ left: 14, right: 14, top: 4, bottom: 28 })
      }
      .layoutWeight(1)
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F4F6FB')
  }
}
