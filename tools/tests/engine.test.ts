/**
 * 规则引擎单元测试（正常 / 边界 / 异常）
 * 运行：node --test tools/tests
 * 说明：直接 import 应用源码中的 DormLinkDomain.ts，与 App 内运行的是同一份实现。
 */
import { test } from 'node:test';
import assert from 'node:assert';

import {
  runEngine,
  evaluateCondition,
  evaluateRule,
  isCoolingDown,
  sortCandidates,
  seedRules,
  defaultDevices,
  defaultEnv,
  type Condition,
  type DeviceState,
  type EnvState,
  type Rule
} from '../../entry/src/main/ets/domain/DormLinkDomain.ts';

const NOW = 1_700_000_000_000;

function env(temperature: number, humidity: number, illuminance: number): EnvState {
  return { temperature, humidity, illuminance };
}

function singleRule(overrides: Partial<Rule>): Rule {
  const base: Rule = {
    id: 'rule_test',
    name: '测试规则',
    enabled: true,
    logic: 'and',
    conditions: [{ metric: 'temperature', op: 'gte', value: 28 }],
    actions: [{ deviceId: 'dev_fan', power: true, level: 60 }],
    priority: 5,
    cooldownSec: 0,
    lastFiredAt: 0,
    updatedAt: NOW
  };
  return Object.assign(base, overrides);
}

/* ---------- 正常用例 ---------- */

test('正常：温度超过阈值时规则命中并打开风扇', () => {
  const outcome = runEngine({
    rules: [singleRule({})],
    devices: defaultDevices(),
    env: env(30, 50, 300),
    now: NOW,
    source: 'test'
  });

  const fan = outcome.devices.find((d) => d.id === 'dev_fan');
  assert.ok(fan, '风扇设备应存在');
  assert.equal(fan!.power, true);
  assert.equal(fan!.level, 60);
  assert.equal(outcome.firedCount, 1);
  assert.equal(outcome.logs.length, 1);
  assert.equal(outcome.logs[0].order, 1);
  assert.equal(outcome.logs[0].fired, true);
  assert.match(outcome.logs[0].conditionsText, /温度 ≥ 28°C/);
  assert.match(outcome.logs[0].changesText, /循环扇 开 60%/);
});

test('正常：双条件规则按「且」组合，两个条件都满足才触发', () => {
  const rule = singleRule({
    id: 'rule_damp',
    name: '闷热联动除湿',
    logic: 'and',
    conditions: [
      { metric: 'temperature', op: 'gte', value: 26 },
      { metric: 'humidity', op: 'gte', value: 75 }
    ],
    actions: [{ deviceId: 'dev_humidifier', power: true, level: 70 }],
    priority: 8
  });

  const tooDry = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: env(30, 60, 300),
    now: NOW,
    source: 'test'
  });
  assert.equal(tooDry.firedCount, 0, '湿度不足时不应触发');

  const hit = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: env(30, 80, 300),
    now: NOW,
    source: 'test'
  });
  assert.equal(hit.firedCount, 1);
  const humidifier = hit.devices.find((d) => d.id === 'dev_humidifier');
  assert.equal(humidifier!.power, true);
  assert.equal(humidifier!.level, 70);
});

test('正常：「或」逻辑任一条件满足即触发', () => {
  const rule = singleRule({
    logic: 'or',
    conditions: [
      { metric: 'temperature', op: 'gt', value: 30 },
      { metric: 'illuminance', op: 'lt', value: 100 }
    ],
    actions: [{ deviceId: 'dev_light', power: true, level: 50 }]
  });
  assert.equal(
    evaluateRule(rule, env(20, 50, 80)),
    true,
    '光照条件单独满足也应触发'
  );
  assert.equal(evaluateRule(rule, env(20, 50, 500)), false);
});

test('正常：多条规则写入不同设备时全部执行，日志按顺序编号', () => {
  const rules: Rule[] = [
    singleRule({
      id: 'rule_a',
      name: 'A 补光',
      conditions: [{ metric: 'illuminance', op: 'lt', value: 200 }],
      actions: [{ deviceId: 'dev_light', power: true, level: 40 }],
      priority: 6
    }),
    singleRule({
      id: 'rule_b',
      name: 'B 开扇',
      conditions: [{ metric: 'temperature', op: 'gte', value: 28 }],
      actions: [{ deviceId: 'dev_fan', power: true, level: 30 }],
      priority: 5
    }),
    singleRule({
      id: 'rule_c',
      name: 'C 合帘',
      conditions: [{ metric: 'illuminance', op: 'gt', value: 800 }],
      actions: [{ deviceId: 'dev_curtain', power: true, level: 100 }],
      priority: 7
    })
  ];

  const outcome = runEngine({
    rules: rules,
    devices: defaultDevices(),
    env: env(31, 50, 100),
    now: NOW,
    source: 'test'
  });

  assert.equal(outcome.logs.length, 2, 'C 的条件不满足，不应进入日志');
  assert.equal(outcome.logs[0].ruleId, 'rule_a', '优先级 6 先执行');
  assert.equal(outcome.logs[1].ruleId, 'rule_b');
  assert.equal(outcome.logs[0].order, 1);
  assert.equal(outcome.logs[1].order, 2);
});

/* ---------- 边界用例 ---------- */

test('边界：gte 恰好等于阈值时触发，gt 恰好等于阈值时不触发', () => {
  const gte: Condition = { metric: 'temperature', op: 'gte', value: 28 };
  const gt: Condition = { metric: 'temperature', op: 'gt', value: 28 };
  assert.equal(evaluateCondition(gte, env(28, 50, 300)), true);
  assert.equal(evaluateCondition(gt, env(28, 50, 300)), false);
  assert.equal(evaluateCondition(gt, env(28.0001, 50, 300)), true);
});

test('边界：eq 比较使用 1e-6 容差，浮点抖动不影响判定', () => {
  const eq: Condition = { metric: 'humidity', op: 'eq', value: 60 };
  assert.equal(evaluateCondition(eq, env(20, 60.0000001, 300)), true);
  assert.equal(evaluateCondition(eq, env(20, 60.5, 300)), false);
});

test('边界：动作目标值越界时被裁剪到 0-100', () => {
  const rule = singleRule({
    actions: [{ deviceId: 'dev_fan', power: true, level: 180 }]
  });
  const outcome = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: env(30, 50, 300),
    now: NOW,
    source: 'test'
  });
  const fan = outcome.devices.find((d) => d.id === 'dev_fan');
  assert.equal(fan!.level, 100, '超过 100 应裁剪为 100');

  const negative = runEngine({
    rules: [singleRule({ actions: [{ deviceId: 'dev_fan', power: true, level: -20 }] })],
    devices: defaultDevices(),
    env: env(30, 50, 300),
    now: NOW,
    source: 'test'
  });
  assert.equal(negative.devices.find((d) => d.id === 'dev_fan')!.level, 0);
});

test('边界：冷却时间窗口内规则不重复触发，超出窗口后恢复', () => {
  const rule = singleRule({ cooldownSec: 60, lastFiredAt: NOW - 30_000 });
  assert.equal(isCoolingDown(rule, NOW), true);

  const blocked = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: env(30, 50, 300),
    now: NOW,
    source: 'test'
  });
  assert.equal(blocked.firedCount, 0);
  assert.equal(blocked.skippedCount, 1);

  const expired = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: env(30, 50, 300),
    now: NOW + 31_000,
    source: 'test'
  });
  assert.equal(expired.firedCount, 1, '冷却结束后应重新触发');
});

test('边界：零条件规则视为不触发，避免误触发全场设备', () => {
  const rule = singleRule({ conditions: [] });
  assert.equal(evaluateRule(rule, env(30, 50, 300)), false);
  const outcome = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: env(30, 50, 300),
    now: NOW,
    source: 'test'
  });
  assert.equal(outcome.logs.length, 0);
});

/* ---------- 异常用例 ---------- */

test('异常：动作指向不存在的设备时跳过该动作并记录冲突说明', () => {
  const rule = singleRule({
    id: 'rule_bad_action',
    actions: [{ deviceId: 'dev_missing', power: true, level: 50 }]
  });
  const outcome = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: env(30, 50, 300),
    now: NOW,
    source: 'test'
  });
  assert.equal(outcome.firedCount, 0);
  assert.match(outcome.logs[0].conflictText, /动作目标不存在/);
});

test('异常：环境数据为 NaN 时条件判为 false，不抛异常', () => {
  const rule = singleRule({});
  const outcome = runEngine({
    rules: [rule],
    devices: defaultDevices(),
    env: { temperature: NaN, humidity: 50, illuminance: 300 },
    now: NOW,
    source: 'test'
  });
  assert.equal(outcome.firedCount, 0);
  assert.equal(evaluateCondition({ metric: 'temperature', op: 'gt', value: 1 }, { temperature: NaN, humidity: 0, illuminance: 0 }), false);
});

/* ---------- 冲突与优先级 ---------- */

test('冲突：同一设备被两条规则控制时高优先级胜出并生成冲突记录', () => {
  const low = singleRule({
    id: 'rule_light_low',
    name: '基础补光',
    conditions: [{ metric: 'illuminance', op: 'lt', value: 400 }],
    actions: [{ deviceId: 'dev_light', power: true, level: 40 }],
    priority: 3
  });
  const high = singleRule({
    id: 'rule_light_high',
    name: '强补光',
    conditions: [{ metric: 'illuminance', op: 'lt', value: 400 }],
    actions: [{ deviceId: 'dev_light', power: true, level: 90 }],
    priority: 6
  });

  const outcome = runEngine({
    rules: [low, high],
    devices: defaultDevices(),
    env: env(25, 50, 100),
    now: NOW,
    source: 'test'
  });

  const light = outcome.devices.find((d) => d.id === 'dev_light');
  assert.equal(light!.level, 90, '高优先级规则的 90% 生效');
  assert.equal(outcome.conflicts.length, 1);
  assert.equal(outcome.conflicts[0].winnerRuleId, 'rule_light_high');
  assert.equal(outcome.conflicts[0].loserRuleId, 'rule_light_low');
  assert.equal(outcome.logs[0].ruleId, 'rule_light_high', '高优先级先执行');
  assert.match(outcome.logs[1].conflictText, /被「强补光」优先占用/);
});

test('冲突：同优先级时按规则 ID 升序先到先得，结果稳定可复现', () => {
  const a = singleRule({
    id: 'rule_aaa',
    name: 'A',
    conditions: [{ metric: 'illuminance', op: 'lt', value: 400 }],
    actions: [{ deviceId: 'dev_light', power: true, level: 70 }],
    priority: 5
  });
  const b = singleRule({
    id: 'rule_bbb',
    name: 'B',
    conditions: [{ metric: 'illuminance', op: 'lt', value: 400 }],
    actions: [{ deviceId: 'dev_light', power: true, level: 20 }],
    priority: 5
  });

  const sorted = sortCandidates([b, a]);
  assert.deepEqual(sorted.map((r) => r.id), ['rule_aaa', 'rule_bbb']);

  const outcome = runEngine({
    rules: [b, a],
    devices: defaultDevices(),
    env: env(25, 50, 100),
    now: NOW,
    source: 'test'
  });
  assert.equal(outcome.devices.find((d) => d.id === 'dev_light')!.level, 70);
  assert.equal(outcome.conflicts[0].winnerRuleId, 'rule_aaa');
});

test('正常：禁用规则与未命中规则计入跳过数，不产生日志', () => {
  const rules = seedRules(NOW);
  const outcome = runEngine({
    rules: rules,
    devices: defaultDevices(),
    env: defaultEnv(),
    now: NOW,
    source: 'test'
  });
  assert.equal(outcome.logs.length, 0, '默认环境不触发任何规则');
  assert.equal(outcome.skippedCount, rules.length);
});

test('正常：内置 6 条种子规则，含 1 条双条件规则，且覆盖 4 类设备', () => {
  const rules = seedRules(NOW);
  assert.ok(rules.length >= 4, '至少 4 条规则');
  const dual = rules.filter((r) => r.conditions.length >= 2);
  assert.equal(dual.length, 1, '含 1 条双条件规则');

  const deviceIds = new Set<string>();
  for (const r of rules) {
    for (const a of r.actions) {
      deviceIds.add(a.deviceId);
    }
  }
  assert.equal(deviceIds.size, 4, '覆盖 4 类设备');
});

test('正常：设备快照在引擎中不被就地修改（纯函数语义）', () => {
  const devices: DeviceState[] = defaultDevices();
  const before = JSON.stringify(devices);
  runEngine({
    rules: [singleRule({})],
    devices,
    env: env(35, 50, 300),
    now: NOW,
    source: 'test'
  });
  assert.equal(JSON.stringify(devices), before, '入参设备数组不应被修改');
});
