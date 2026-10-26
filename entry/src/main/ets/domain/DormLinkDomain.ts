/**
 * DormLink 领域层 —— 单一文件、零运行时外部依赖。
 *
 * 设计约束（同时满足两套工具链）：
 *  1. HarmonyOS ArkTS 编译器（.ets 页面 import 本文件，路径不带扩展名）；
 *  2. Node.js 24 类型擦除运行（测试 import 本文件，路径带 .ts 扩展名）。
 *
 * 因此本文件内不使用 enum / namespace / 装饰器 / 对象展开 / any，
 * 也不 import 其他领域文件，保证两种运行方式下行为完全一致。
 */

/* ============================================================
 * 一、基础类型
 * ============================================================ */

/** 可控设备类型：4 类 */
export type DeviceKind = 'light' | 'fan' | 'humidifier' | 'curtain';

/** 可调环境量：3 项 */
export type MetricKey = 'temperature' | 'humidity' | 'illuminance';

/** 比较运算 */
export type CompareOp = 'gt' | 'gte' | 'lt' | 'lte' | 'eq';

/** 多条件之间的组合方式 */
export type RuleLogic = 'and' | 'or';

export const DEVICE_KINDS: DeviceKind[] = ['light', 'fan', 'humidifier', 'curtain'];
export const METRIC_KEYS: MetricKey[] = ['temperature', 'humidity', 'illuminance'];
export const COMPARE_OPS: CompareOp[] = ['gt', 'gte', 'lt', 'lte', 'eq'];

/** 每类设备在 UI 上使用的符号与默认名称 */
export interface DeviceMeta {
  kind: DeviceKind;
  label: string;
  symbol: string;
  unitText: string;
  /** 该设备是否支持 0-100 的档位/开合度 */
  dimmable: boolean;
}

export const DEVICE_META: DeviceMeta[] = [
  { kind: 'light', label: '照明灯', symbol: '💡', unitText: '%', dimmable: true },
  { kind: 'fan', label: '风扇', symbol: '🌀', unitText: '档位', dimmable: true },
  { kind: 'humidifier', label: '加湿器', symbol: '💧', unitText: '%', dimmable: true },
  { kind: 'curtain', label: '窗帘', symbol: '🪟', unitText: '开合', dimmable: true }
];

export interface MetricMeta {
  key: MetricKey;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
}

/** 3 项可调整模拟环境数据及其合法区间 */
export const METRIC_META: MetricMeta[] = [
  { key: 'temperature', label: '温度', unit: '°C', min: -10, max: 50, step: 0.5 },
  { key: 'humidity', label: '湿度', unit: '%', min: 0, max: 100, step: 1 },
  { key: 'illuminance', label: '光照', unit: 'lux', min: 0, max: 2000, step: 10 }
];

export function metricMeta(key: MetricKey): MetricMeta {
  for (let i = 0; i < METRIC_META.length; i++) {
    if (METRIC_META[i].key === key) {
      return METRIC_META[i];
    }
  }
  return METRIC_META[0];
}

export function metricLabel(key: MetricKey): string {
  return metricMeta(key).label;
}

export function metricUnit(key: MetricKey): string {
  return metricMeta(key).unit;
}

/* ============================================================
 * 二、业务数据模型
 * ============================================================ */

/** 设备当前状态（持久化） */
export interface DeviceState {
  id: string;
  kind: DeviceKind;
  name: string;
  room: string;
  power: boolean;
  /** 0-100：亮度 / 风速 / 加湿强度 / 窗帘开合度 */
  level: number;
}

/** 模拟环境快照（持久化） */
export interface EnvState {
  temperature: number;
  humidity: number;
  illuminance: number;
}

/** 单条触发条件 */
export interface Condition {
  metric: MetricKey;
  op: CompareOp;
  value: number;
}

/** 单条设备动作 */
export interface DeviceAction {
  deviceId: string;
  power: boolean;
  level: number;
}

/** 自动化规则 */
export interface Rule {
  id: string;
  name: string;
  enabled: boolean;
  logic: RuleLogic;
  conditions: Condition[];
  actions: DeviceAction[];
  /** 1-10，数值越大越优先 */
  priority: number;
  /** 冷却秒数，0 表示不限制 */
  cooldownSec: number;
  /** 上次触发时间（毫秒时间戳），用于冷却判定与持久化 */
  lastFiredAt: number;
  updatedAt: number;
}

/** 一条冲突记录 */
export interface ConflictNote {
  deviceId: string;
  deviceName: string;
  winnerRuleId: string;
  winnerRuleName: string;
  loserRuleId: string;
  loserRuleName: string;
  reason: string;
}

/** 单次设备变化 */
export interface DeviceChange {
  deviceId: string;
  deviceName: string;
  beforeText: string;
  afterText: string;
}

/** 执行日志（写入 RDB） */
export interface LogEntry {
  id: string;
  at: number;
  source: string;
  order: number;
  ruleId: string;
  ruleName: string;
  priority: number;
  conditionsText: string;
  changesText: string;
  conflictText: string;
  /** 是否真正改变了设备 */
  fired: boolean;
}

/** 引擎一次执行结果 */
export interface EngineOutcome {
  devices: DeviceState[];
  rules: Rule[];
  logs: LogEntry[];
  conflicts: ConflictNote[];
  firedCount: number;
  skippedCount: number;
}

/** 引擎输入 */
export interface EngineInput {
  rules: Rule[];
  devices: DeviceState[];
  env: EnvState;
  /** 当前时间戳（毫秒），由调用方注入以保证可测试 */
  now: number;
  /** 日志来源标记 */
  source: string;
}

/* ============================================================
 * 三、通用工具
 * ============================================================ */

export function clamp(value: number, min: number, max: number): number {
  if (value !== value) {
    return min;
  }
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}

export function isFiniteNumber(value: number): boolean {
  return value === value && value !== Infinity && value !== -Infinity;
}

export function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

/** 把 JSON 中的任意值安全转成数字 */
export function toNumber(value: number, fallback: number): number {
  if (typeof value === 'number' && isFiniteNumber(value)) {
    return value;
  }
  return fallback;
}

export function toBool(value: boolean, fallback: boolean): boolean {
  if (value === true || value === false) {
    return value;
  }
  return fallback;
}

/* ============================================================
 * 四、条件求值
 * ============================================================ */

export function readMetric(env: EnvState, key: MetricKey): number {
  if (key === 'temperature') {
    return env.temperature;
  }
  if (key === 'humidity') {
    return env.humidity;
  }
  if (key === 'illuminance') {
    return env.illuminance;
  }
  return 0;
}

/** 单条件求值；op 为目标值左侧的实测值 */
export function evaluateCondition(cond: Condition, env: EnvState): boolean {
  const actual = readMetric(env, cond.metric);
  const target = cond.value;
  if (!isFiniteNumber(actual) || !isFiniteNumber(target)) {
    return false;
  }
  if (cond.op === 'gt') {
    return actual > target;
  }
  if (cond.op === 'gte') {
    return actual >= target;
  }
  if (cond.op === 'lt') {
    return actual < target;
  }
  if (cond.op === 'lte') {
    return actual <= target;
  }
  if (cond.op === 'eq') {
    // 浮点相等：允许 1e-6 容差，避免 28.0000001 判定失败
    return Math.abs(actual - target) < 0.000001;
  }
  return false;
}

/** 整条规则的条件组合求值；空条件视为不触发 */
export function evaluateRule(rule: Rule, env: EnvState): boolean {
  if (rule.conditions.length === 0) {
    return false;
  }
  if (rule.logic === 'or') {
    for (let i = 0; i < rule.conditions.length; i++) {
      if (evaluateCondition(rule.conditions[i], env)) {
        return true;
      }
    }
    return false;
  }
  for (let i = 0; i < rule.conditions.length; i++) {
    if (!evaluateCondition(rule.conditions[i], env)) {
      return false;
    }
  }
  return true;
}

/** 冷却是否仍在生效 */
export function isCoolingDown(rule: Rule, now: number): boolean {
  if (rule.cooldownSec <= 0) {
    return false;
  }
  if (rule.lastFiredAt <= 0) {
    return false;
  }
  return now - rule.lastFiredAt < rule.cooldownSec * 1000;
}

/* ============================================================
 * 五、文案格式化
 * ============================================================ */

export function opSymbol(op: CompareOp): string {
  if (op === 'gt') {
    return '>';
  }
  if (op === 'gte') {
    return '≥';
  }
  if (op === 'lt') {
    return '<';
  }
  if (op === 'lte') {
    return '≤';
  }
  return '=';
}

export function formatCondition(cond: Condition): string {
  const unit = metricUnit(cond.metric);
  return `${metricLabel(cond.metric)} ${opSymbol(cond.op)} ${cond.value}${unit}`;
}

export function formatConditions(rule: Rule): string {
  if (rule.conditions.length === 0) {
    return '（无条件）';
  }
  const joiner = rule.logic === 'or' ? ' 或 ' : ' 且 ';
  let text = '';
  for (let i = 0; i < rule.conditions.length; i++) {
    if (i > 0) {
      text += joiner;
    }
    text += formatCondition(rule.conditions[i]);
  }
  return text;
}

export function findDevice(devices: DeviceState[], id: string): DeviceState | null {
  for (let i = 0; i < devices.length; i++) {
    if (devices[i].id === id) {
      return devices[i];
    }
  }
  return null;
}

export function deviceText(devices: DeviceState[], id: string): string {
  const device = findDevice(devices, id);
  if (device === null) {
    return id;
  }
  return device.name;
}

/** 设备状态的可读描述，如「客厅灯 开 80%」「客厅灯 关」 */
export function stateText(device: DeviceState): string {
  if (!device.power) {
    return `${device.name} 关`;
  }
  return `${device.name} 开 ${device.level}%`;
}

export function actionText(action: DeviceAction, devices: DeviceState[]): string {
  const name = deviceText(devices, action.deviceId);
  if (!action.power) {
    return `${name} 关`;
  }
  return `${name} 开 ${action.level}%`;
}

export function formatActions(rule: Rule, devices: DeviceState[]): string {
  if (rule.actions.length === 0) {
    return '（无动作）';
  }
  let text = '';
  for (let i = 0; i < rule.actions.length; i++) {
    if (i > 0) {
      text += '；';
    }
    text += actionText(rule.actions[i], devices);
  }
  return text;
}

/* ============================================================
 * 六、规则引擎：排序 → 冲突裁决 → 设备变更 → 日志
 * ============================================================ */

interface RuleRef {
  rule: Rule;
}

/** 候选规则排序：优先级降序；同优先级按规则 ID 升序（保证确定性） */
export function sortCandidates(rules: Rule[]): Rule[] {
  const list: Rule[] = [];
  for (let i = 0; i < rules.length; i++) {
    list.push(rules[i]);
  }
  list.sort((a: Rule, b: Rule): number => {
    if (a.priority !== b.priority) {
      return b.priority - a.priority;
    }
    if (a.id < b.id) {
      return -1;
    }
    if (a.id > b.id) {
      return 1;
    }
    return 0;
  });
  return list;
}

/**
 * 执行一次规则评估。
 *
 * 冲突策略（写进需求说明书与报告）：
 *   1. 候选规则按 priority 降序、id 升序排定执行顺序；
 *   2. 同一设备只接受第一次（即最高优先级）写入，后续写入被丢弃；
 *   3. 被丢弃的写入生成 ConflictNote，说明谁胜出、原因；
 *   4. 所有命中规则的触发条件、设备变化、执行序号都写入日志。
 */
export function runEngine(input: EngineInput): EngineOutcome {
  const working: DeviceState[] = [];
  for (let i = 0; i < input.devices.length; i++) {
    const d = input.devices[i];
    working.push({ id: d.id, kind: d.kind, name: d.name, room: d.room, power: d.power, level: d.level });
  }

  const candidates: Rule[] = [];
  let skipped = 0;
  for (let i = 0; i < input.rules.length; i++) {
    const rule = input.rules[i];
    if (!rule.enabled) {
      skipped++;
      continue;
    }
    if (!evaluateRule(rule, input.env)) {
      skipped++;
      continue;
    }
    if (isCoolingDown(rule, input.now)) {
      skipped++;
      continue;
    }
    candidates.push(rule);
  }

  const ordered = sortCandidates(candidates);
  const logs: LogEntry[] = [];
  const conflicts: ConflictNote[] = [];
  const firedIds: string[] = [];
  // 设备 -> 胜出规则 ID
  const owner: Map<string, string> = new Map<string, string>();
  const ownerName: Map<string, string> = new Map<string, string>();

  let firedCount = 0;
  for (let i = 0; i < ordered.length; i++) {
    const rule = ordered[i];
    const order = i + 1;
    const changes: DeviceChange[] = [];
    const conflictTexts: string[] = [];

    for (let a = 0; a < rule.actions.length; a++) {
      const action = rule.actions[a];
      const device = findDevice(working, action.deviceId);
      if (device === null) {
        conflictTexts.push(`动作目标不存在：${action.deviceId}`);
        continue;
      }
      const winnerId = owner.get(action.deviceId);
      if (winnerId !== undefined && winnerId !== rule.id) {
        const winnerName = ownerName.get(action.deviceId);
        const reason = `设备「${device.name}」已由更高优先级规则「${winnerName}」控制`;
        conflictTexts.push(`${device.name}：被「${winnerName}」优先占用`);
        conflicts.push({
          deviceId: device.id,
          deviceName: device.name,
          winnerRuleId: winnerId,
          winnerRuleName: winnerName === undefined ? winnerId : winnerName,
          loserRuleId: rule.id,
          loserRuleName: rule.name,
          reason: reason
        });
        continue;
      }

      const nextPower = action.power;
      const nextLevel = action.power ? Math.round(clamp(action.level, 0, 100)) : 0;
      const before = stateText(device);
      device.power = nextPower;
      device.level = nextLevel;
      const after = stateText(device);
      if (before !== after) {
        changes.push({ deviceId: device.id, deviceName: device.name, beforeText: before, afterText: after });
      }
      owner.set(device.id, rule.id);
      ownerName.set(device.id, rule.name);
    }

    let changesText = '';
    for (let c = 0; c < changes.length; c++) {
      if (c > 0) {
        changesText += '；';
      }
      changesText += `${changes[c].beforeText} → ${changes[c].afterText}`;
    }
    if (changesText === '') {
      changesText = '无设备变化';
    }

    let conflictText = '';
    for (let c = 0; c < conflictTexts.length; c++) {
      if (c > 0) {
        conflictText += '；';
      }
      conflictText += conflictTexts[c];
    }

    const fired = changes.length > 0;
    if (fired) {
      firedCount++;
      firedIds.push(rule.id);
    }

    logs.push({
      id: `log_${input.now}_${order}`,
      at: input.now,
      source: input.source,
      order: order,
      ruleId: rule.id,
      ruleName: rule.name,
      priority: rule.priority,
      conditionsText: formatConditions(rule),
      changesText: changesText,
      conflictText: conflictText,
      fired: fired
    });
  }

  // 回写 lastFiredAt（仅真正触发且改变了设备的规则）
  const nextRules: Rule[] = [];
  for (let i = 0; i < input.rules.length; i++) {
    const rule = input.rules[i];
    const hit = firedIds.indexOf(rule.id) >= 0;
    nextRules.push({
      id: rule.id,
      name: rule.name,
      enabled: rule.enabled,
      logic: rule.logic,
      conditions: rule.conditions,
      actions: rule.actions,
      priority: rule.priority,
      cooldownSec: rule.cooldownSec,
      lastFiredAt: hit ? input.now : rule.lastFiredAt,
      updatedAt: rule.updatedAt
    });
  }

  return {
    devices: working,
    rules: nextRules,
    logs: logs,
    conflicts: conflicts,
    firedCount: firedCount,
    skippedCount: skipped
  };
}

/* ============================================================
 * 七、规则校验（正常 / 边界 / 异常）
 * ============================================================ */

export interface ValidationIssue {
  field: string;
  message: string;
}

export interface ValidationResult {
  ok: boolean;
  issues: ValidationIssue[];
}

export const MAX_RULES = 12;
export const MAX_CONDITIONS = 3;
export const MAX_ACTIONS = 4;

function issue(field: string, message: string): ValidationIssue {
  return { field: field, message: message };
}

/** 校验一条规则；selfId 用于编辑时排除自身的重名判断 */
export function validateRule(rule: Rule, allRules: Rule[], deviceIds: string[], selfId: string): ValidationResult {
  const issues: ValidationIssue[] = [];
  const name = rule.name.trim();
  if (name.length === 0) {
    issues.push(issue('name', '规则名称不能为空'));
  } else if (name.length > 20) {
    issues.push(issue('name', '规则名称不能超过 20 个字符'));
  }
  for (let i = 0; i < allRules.length; i++) {
    const other = allRules[i];
    if (other.id !== selfId && other.name.trim() === name && name.length > 0) {
      issues.push(issue('name', `规则名称「${name}」已存在`));
      break;
    }
  }

  if (rule.logic !== 'and' && rule.logic !== 'or') {
    issues.push(issue('logic', '条件组合方式仅支持 且/或'));
  }

  if (rule.conditions.length === 0) {
    issues.push(issue('conditions', '至少需要 1 条触发条件'));
  } else if (rule.conditions.length > MAX_CONDITIONS) {
    issues.push(issue('conditions', `触发条件最多 ${MAX_CONDITIONS} 条`));
  }
  for (let i = 0; i < rule.conditions.length; i++) {
    const cond = rule.conditions[i];
    const meta = metricMeta(cond.metric);
    if (METRIC_KEYS.indexOf(cond.metric) < 0) {
      issues.push(issue('conditions', `第 ${i + 1} 条条件的指标不合法`));
      continue;
    }
    if (COMPARE_OPS.indexOf(cond.op) < 0) {
      issues.push(issue('conditions', `第 ${i + 1} 条条件的比较符不合法`));
    }
    if (!isFiniteNumber(cond.value)) {
      issues.push(issue('conditions', `第 ${i + 1} 条条件的阈值不是有效数字`));
    } else if (cond.value < meta.min || cond.value > meta.max) {
      issues.push(issue('conditions', `${meta.label}阈值需在 ${meta.min}-${meta.max}${meta.unit} 之间`));
    }
  }

  if (rule.actions.length === 0) {
    issues.push(issue('actions', '至少需要 1 条设备动作'));
  } else if (rule.actions.length > MAX_ACTIONS) {
    issues.push(issue('actions', `设备动作最多 ${MAX_ACTIONS} 条`));
  }
  for (let i = 0; i < rule.actions.length; i++) {
    const action = rule.actions[i];
    if (deviceIds.indexOf(action.deviceId) < 0) {
      issues.push(issue('actions', `第 ${i + 1} 条动作的设备不存在`));
    }
    if (!isFiniteNumber(action.level) || action.level < 0 || action.level > 100) {
      issues.push(issue('actions', `第 ${i + 1} 条动作的目标值需在 0-100 之间`));
    }
    if (action.power !== true && action.power !== false) {
      issues.push(issue('actions', `第 ${i + 1} 条动作的开关状态不合法`));
    }
  }

  if (!isFiniteNumber(rule.priority) || rule.priority < 1 || rule.priority > 10) {
    issues.push(issue('priority', '优先级需为 1-10 的整数'));
  } else if (Math.floor(rule.priority) !== rule.priority) {
    issues.push(issue('priority', '优先级需为整数'));
  }

  if (!isFiniteNumber(rule.cooldownSec) || rule.cooldownSec < 0 || rule.cooldownSec > 3600) {
    issues.push(issue('cooldownSec', '冷却时间需在 0-3600 秒之间'));
  }

  return { ok: issues.length === 0, issues: issues };
}

/** 新增规则前的总量校验 */
export function canAddRule(allRules: Rule[]): boolean {
  return allRules.length < MAX_RULES;
}

/* ============================================================
 * 八、持久化编解码（Preferences 中保存的 JSON 快照）
 * ============================================================ */

export const SNAPSHOT_VERSION = 2;

export interface Snapshot {
  version: number;
  savedAt: number;
  activeScenarioId: string;
  env: EnvState;
  devices: DeviceState[];
  rules: Rule[];
}

export function dumpSnapshot(snapshot: Snapshot): string {
  return JSON.stringify(snapshot);
}

export function defaultEnv(): EnvState {
  return { temperature: 26.5, humidity: 62, illuminance: 300 };
}

export function defaultDevices(): DeviceState[] {
  return [
    { id: 'dev_light', kind: 'light', name: '书桌灯', room: '卧室', power: false, level: 60 },
    { id: 'dev_fan', kind: 'fan', name: '循环扇', room: '卧室', power: false, level: 40 },
    { id: 'dev_humidifier', kind: 'humidifier', name: '加湿器', room: '卧室', power: false, level: 50 },
    { id: 'dev_curtain', kind: 'curtain', name: '遮光帘', room: '卧室', power: false, level: 0 }
  ];
}

function sanitizeEnv(raw: EnvState): EnvState {
  const fallback = defaultEnv();
  if (raw === null || raw === undefined) {
    return fallback;
  }
  return {
    temperature: toNumber(raw.temperature, fallback.temperature),
    humidity: clamp(toNumber(raw.humidity, fallback.humidity), 0, 100),
    illuminance: clamp(toNumber(raw.illuminance, fallback.illuminance), 0, 2000)
  };
}

function sanitizeDevice(raw: DeviceState, index: number): DeviceState {
  return {
    id: typeof raw.id === 'string' && raw.id.length > 0 ? raw.id : `dev_${index}`,
    kind: DEVICE_KINDS.indexOf(raw.kind) >= 0 ? raw.kind : 'light',
    name: typeof raw.name === 'string' && raw.name.length > 0 ? raw.name : `设备${index + 1}`,
    room: typeof raw.room === 'string' ? raw.room : '卧室',
    power: toBool(raw.power, false),
    level: Math.round(clamp(toNumber(raw.level, 0), 0, 100))
  };
}

function sanitizeCondition(raw: Condition): Condition {
  return {
    metric: METRIC_KEYS.indexOf(raw.metric) >= 0 ? raw.metric : 'temperature',
    op: COMPARE_OPS.indexOf(raw.op) >= 0 ? raw.op : 'gt',
    value: toNumber(raw.value, 0)
  };
}

function sanitizeRule(raw: Rule, index: number): Rule {
  const conditions: Condition[] = [];
  if (Array.isArray(raw.conditions)) {
    for (let i = 0; i < raw.conditions.length; i++) {
      conditions.push(sanitizeCondition(raw.conditions[i]));
    }
  }
  const actions: DeviceAction[] = [];
  if (Array.isArray(raw.actions)) {
    for (let i = 0; i < raw.actions.length; i++) {
      const a = raw.actions[i];
      actions.push({
        deviceId: typeof a.deviceId === 'string' ? a.deviceId : '',
        power: toBool(a.power, false),
        level: Math.round(clamp(toNumber(a.level, 0), 0, 100))
      });
    }
  }
  return {
    id: typeof raw.id === 'string' && raw.id.length > 0 ? raw.id : `rule_${index}`,
    name: typeof raw.name === 'string' ? raw.name : `规则${index + 1}`,
    enabled: toBool(raw.enabled, true),
    logic: raw.logic === 'or' ? 'or' : 'and',
    conditions: conditions,
    actions: actions,
    priority: Math.round(clamp(toNumber(raw.priority, 5), 1, 10)),
    cooldownSec: Math.round(clamp(toNumber(raw.cooldownSec, 0), 0, 3600)),
    lastFiredAt: toNumber(raw.lastFiredAt, 0),
    updatedAt: toNumber(raw.updatedAt, 0)
  };
}

/**
 * 解析快照。任何损坏、截断、版本过新都返回 null，由调用方回退到种子数据，
 * 保证「进程被杀后再次启动」不会白屏或崩溃。
 */
export function parseSnapshot(text: string): Snapshot | null {
  if (typeof text !== 'string' || text.length === 0) {
    return null;
  }
  let raw: Snapshot | null = null;
  try {
    raw = JSON.parse(text) as Snapshot;
  } catch (err) {
    return null;
  }
  if (raw === null || raw === undefined || typeof raw !== 'object') {
    return null;
  }
  if (Array.isArray(raw)) {
    return null;
  }
  const version = toNumber(raw.version, -1);
  if (version < 1 || version > SNAPSHOT_VERSION) {
    return null;
  }
  const devices: DeviceState[] = [];
  if (Array.isArray(raw.devices) && raw.devices.length > 0) {
    for (let i = 0; i < raw.devices.length; i++) {
      devices.push(sanitizeDevice(raw.devices[i], i));
    }
  } else {
    const seed = defaultDevices();
    for (let i = 0; i < seed.length; i++) {
      devices.push(seed[i]);
    }
  }
  const rules: Rule[] = [];
  if (Array.isArray(raw.rules)) {
    for (let i = 0; i < raw.rules.length; i++) {
      rules.push(sanitizeRule(raw.rules[i], i));
    }
  }
  return {
    version: SNAPSHOT_VERSION,
    savedAt: toNumber(raw.savedAt, 0),
    activeScenarioId: typeof raw.activeScenarioId === 'string' ? raw.activeScenarioId : '',
    env: sanitizeEnv(raw.env),
    devices: devices,
    rules: rules
  };
}

/** v1 快照（无 cooldownSec / lastFiredAt）升级到 v2 */
export function migrateSnapshot(text: string): Snapshot | null {
  const parsed = parseSnapshot(text);
  if (parsed === null) {
    return null;
  }
  const migrated: Rule[] = [];
  for (let i = 0; i < parsed.rules.length; i++) {
    const r = parsed.rules[i];
    migrated.push({
      id: r.id,
      name: r.name,
      enabled: r.enabled,
      logic: r.logic,
      conditions: r.conditions,
      actions: r.actions,
      priority: r.priority,
      cooldownSec: r.cooldownSec,
      lastFiredAt: r.lastFiredAt,
      updatedAt: r.updatedAt
    });
  }
  parsed.rules = migrated;
  return parsed;
}

/* ============================================================
 * 九、种子数据与 2 组模拟场景
 * ============================================================ */

export interface Scenario {
  id: string;
  name: string;
  description: string;
  env: EnvState;
}

export function seedScenarios(): Scenario[] {
  return [
    {
      id: 'sc_night_study',
      name: '深夜自习',
      description: '23:40 宿舍熄灯后，室内偏暗、温度适中，检查补光灯与静音风。',
      env: { temperature: 24.5, humidity: 52, illuminance: 120 }
    },
    {
      id: 'sc_rainy_noon',
      name: '梅雨午后',
      description: '连续阴雨，湿度逼近 90%，窗外闷热，检查除湿、遮光与通风。',
      env: { temperature: 31.5, humidity: 88, illuminance: 900 }
    }
  ];
}

export function seedRules(now: number): Rule[] {
  return [
    {
      id: 'rule_01_hot_fan',
      name: '高温启动循环扇',
      enabled: true,
      logic: 'and',
      conditions: [{ metric: 'temperature', op: 'gte', value: 28 }],
      actions: [{ deviceId: 'dev_fan', power: true, level: 60 }],
      priority: 5,
      cooldownSec: 60,
      lastFiredAt: 0,
      updatedAt: now
    },
    {
      id: 'rule_02_damp',
      name: '闷热联动除湿',
      enabled: true,
      logic: 'and',
      conditions: [
        { metric: 'temperature', op: 'gte', value: 26 },
        { metric: 'humidity', op: 'gte', value: 75 }
      ],
      actions: [{ deviceId: 'dev_humidifier', power: true, level: 70 }],
      priority: 8,
      cooldownSec: 0,
      lastFiredAt: 0,
      updatedAt: now
    },
    {
      id: 'rule_03_dim_light',
      name: '光线不足基础补光',
      enabled: true,
      logic: 'and',
      conditions: [{ metric: 'illuminance', op: 'lt', value: 150 }],
      actions: [{ deviceId: 'dev_light', power: true, level: 40 }],
      priority: 3,
      cooldownSec: 0,
      lastFiredAt: 0,
      updatedAt: now
    },
    {
      id: 'rule_04_study_boost',
      name: '自习强补光',
      enabled: true,
      logic: 'and',
      conditions: [{ metric: 'illuminance', op: 'lt', value: 200 }],
      actions: [{ deviceId: 'dev_light', power: true, level: 90 }],
      priority: 6,
      cooldownSec: 0,
      lastFiredAt: 0,
      updatedAt: now
    },
    {
      id: 'rule_05_glare',
      name: '强光自动合帘',
      enabled: true,
      logic: 'and',
      conditions: [{ metric: 'illuminance', op: 'gt', value: 800 }],
      actions: [{ deviceId: 'dev_curtain', power: true, level: 100 }],
      priority: 7,
      cooldownSec: 0,
      lastFiredAt: 0,
      updatedAt: now
    },
    {
      id: 'rule_06_sleep',
      name: '就寝一键关灯',
      enabled: false,
      logic: 'and',
      conditions: [{ metric: 'illuminance', op: 'lte', value: 30 }],
      actions: [
        { deviceId: 'dev_light', power: false, level: 0 },
        { deviceId: 'dev_fan', power: false, level: 0 }
      ],
      priority: 9,
      cooldownSec: 0,
      lastFiredAt: 0,
      updatedAt: now
    }
  ];
}

/* ============================================================
 * 九点五、不可变更新辅助（供 ArkUI 状态刷新使用）
 * ============================================================ */

/** 复制快照（浅拷贝数组与字段），并刷新 savedAt */
export function cloneSnapshot(source: Snapshot, now: number): Snapshot {
  const devices: DeviceState[] = [];
  for (let i = 0; i < source.devices.length; i++) {
    const d = source.devices[i];
    devices.push({ id: d.id, kind: d.kind, name: d.name, room: d.room, power: d.power, level: d.level });
  }
  const rules: Rule[] = [];
  for (let i = 0; i < source.rules.length; i++) {
    const r = source.rules[i];
    rules.push({
      id: r.id,
      name: r.name,
      enabled: r.enabled,
      logic: r.logic,
      conditions: r.conditions,
      actions: r.actions,
      priority: r.priority,
      cooldownSec: r.cooldownSec,
      lastFiredAt: r.lastFiredAt,
      updatedAt: r.updatedAt
    });
  }
  return {
    version: SNAPSHOT_VERSION,
    savedAt: now,
    activeScenarioId: source.activeScenarioId,
    env: { temperature: source.env.temperature, humidity: source.env.humidity, illuminance: source.env.illuminance },
    devices: devices,
    rules: rules
  };
}

/** 替换一台设备，返回新数组（触发 ArkUI 状态刷新） */
export function replaceDevice(devices: DeviceState[], next: DeviceState): DeviceState[] {
  const out: DeviceState[] = [];
  for (let i = 0; i < devices.length; i++) {
    out.push(devices[i].id === next.id ? next : devices[i]);
  }
  return out;
}

/** 新增或替换一条规则 */
export function upsertRule(rules: Rule[], next: Rule): Rule[] {
  const out: Rule[] = [];
  let replaced = false;
  for (let i = 0; i < rules.length; i++) {
    if (rules[i].id === next.id) {
      out.push(next);
      replaced = true;
    } else {
      out.push(rules[i]);
    }
  }
  if (!replaced) {
    out.push(next);
  }
  return out;
}

/** 删除一条规则 */
export function removeRule(rules: Rule[], id: string): Rule[] {
  const out: Rule[] = [];
  for (let i = 0; i < rules.length; i++) {
    if (rules[i].id !== id) {
      out.push(rules[i]);
    }
  }
  return out;
}

/** 在系统中查找规则，未找到返回 null */
export function findRule(rules: Rule[], id: string): Rule | null {
  for (let i = 0; i < rules.length; i++) {
    if (rules[i].id === id) {
      return rules[i];
    }
  }
  return null;
}

/** 创建一个空规则草稿（用于「新建规则」） */
export function createDraftRule(now: number, id: string): Rule {
  return {
    id: id,
    name: '',
    enabled: true,
    logic: 'and',
    conditions: [{ metric: 'temperature', op: 'gte', value: 28 }],
    actions: [{ deviceId: 'dev_fan', power: true, level: 60 }],
    priority: 5,
    cooldownSec: 0,
    lastFiredAt: 0,
    updatedAt: now
  };
}

export function defaultSnapshot(now: number): Snapshot {
  return {
    version: SNAPSHOT_VERSION,
    savedAt: now,
    activeScenarioId: '',
    env: defaultEnv(),
    devices: defaultDevices(),
    rules: seedRules(now)
  };
}
