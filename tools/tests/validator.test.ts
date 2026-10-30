/**
 * 规则校验单元测试（正常 / 边界 / 异常）
 * 运行：node --test tools/tests
 */
import { test } from 'node:test';
import assert from 'node:assert';

import {
  validateRule,
  canAddRule,
  seedRules,
  defaultDevices,
  type Rule
} from '../../entry/src/main/ets/domain/DormLinkDomain.ts';

const NOW = 1_700_000_000_000;
const deviceIds = defaultDevices().map((d) => d.id);

function rule(overrides: Partial<Rule>): Rule {
  const base: Rule = {
    id: 'rule_new',
    name: '新风规则',
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

test('正常：合法规则通过校验', () => {
  const result = validateRule(rule({}), seedRules(NOW), deviceIds, 'rule_new');
  assert.equal(result.ok, true);
  assert.deepEqual(result.issues, []);
});

test('正常：编辑自身时不会误报重名', () => {
  const existing = seedRules(NOW);
  const self = existing[0];
  const result = validateRule(self, existing, deviceIds, self.id);
  assert.equal(result.ok, true, '与自身同名应允许');
});

test('异常：名称为空、重名、超长均被拦截', () => {
  const existing = seedRules(NOW);
  const empty = validateRule(rule({ name: '   ' }), existing, deviceIds, 'rule_new');
  assert.equal(empty.ok, false);
  assert.ok(empty.issues.some((i) => i.field === 'name' && i.message.includes('不能为空')));

  const duplicated = validateRule(rule({ name: '高温启动循环扇' }), existing, deviceIds, 'rule_new');
  assert.equal(duplicated.ok, false);
  assert.ok(duplicated.issues.some((i) => i.message.includes('已存在')));

  const tooLong = validateRule(rule({ name: '一二三四五六七八九十一二三四五六七八九十一' }), existing, deviceIds, 'rule_new');
  assert.equal(tooLong.ok, false);
  assert.ok(tooLong.issues.some((i) => i.message.includes('20')));
});

test('异常：没有任何条件或动作的规则被拒绝', () => {
  const noCondition = validateRule(rule({ conditions: [] }), [], deviceIds, 'rule_new');
  assert.equal(noCondition.ok, false);
  assert.ok(noCondition.issues.some((i) => i.field === 'conditions'));

  const noAction = validateRule(rule({ actions: [] }), [], deviceIds, 'rule_new');
  assert.equal(noAction.ok, false);
  assert.ok(noAction.issues.some((i) => i.field === 'actions'));
});

test('边界：条件数 1 与 3 合法，4 条被拒绝', () => {
  const one = validateRule(rule({}), [], deviceIds, 'rule_new');
  assert.equal(one.ok, true);

  const three = validateRule(
    rule({
      conditions: [
        { metric: 'temperature', op: 'gte', value: 26 },
        { metric: 'humidity', op: 'gte', value: 70 },
        { metric: 'illuminance', op: 'lt', value: 200 }
      ]
    }),
    [],
    deviceIds,
    'rule_new'
  );
  assert.equal(three.ok, true, '3 条条件应在允许范围内');

  const four = validateRule(
    rule({
      conditions: [
        { metric: 'temperature', op: 'gte', value: 26 },
        { metric: 'humidity', op: 'gte', value: 70 },
        { metric: 'illuminance', op: 'lt', value: 200 },
        { metric: 'temperature', op: 'lt', value: 40 }
      ]
    }),
    [],
    deviceIds,
    'rule_new'
  );
  assert.equal(four.ok, false);
  assert.ok(four.issues.some((i) => i.message.includes('最多')));
});

test('边界：阈值处于指标区间端点合法，越界被拒绝', () => {
  const minOk = validateRule(
    rule({ conditions: [{ metric: 'temperature', op: 'gte', value: -10 }] }),
    [],
    deviceIds,
    'rule_new'
  );
  assert.equal(minOk.ok, true, '-10°C 为温度区间下界，应允许');

  const maxOk = validateRule(
    rule({ conditions: [{ metric: 'illuminance', op: 'lte', value: 2000 }] }),
    [],
    deviceIds,
    'rule_new'
  );
  assert.equal(maxOk.ok, true, '2000lux 为光照区间上界，应允许');

  const over = validateRule(
    rule({ conditions: [{ metric: 'humidity', op: 'gte', value: 101 }] }),
    [],
    deviceIds,
    'rule_new'
  );
  assert.equal(over.ok, false);
  assert.ok(over.issues.some((i) => i.message.includes('0-100')));
});

test('边界：优先级 1 与 10 合法，0 与 11 被拒绝', () => {
  assert.equal(validateRule(rule({ priority: 1 }), [], deviceIds, 'rule_new').ok, true);
  assert.equal(validateRule(rule({ priority: 10 }), [], deviceIds, 'rule_new').ok, true);
  assert.equal(validateRule(rule({ priority: 0 }), [], deviceIds, 'rule_new').ok, false);
  assert.equal(validateRule(rule({ priority: 11 }), [], deviceIds, 'rule_new').ok, false);
  assert.equal(validateRule(rule({ priority: 5.5 }), [], deviceIds, 'rule_new').ok, false);
});

test('边界：动作目标值 0 与 100 合法，越界被拒绝', () => {
  assert.equal(validateRule(rule({ actions: [{ deviceId: 'dev_fan', power: true, level: 0 }] }), [], deviceIds, 'rule_new').ok, true);
  assert.equal(validateRule(rule({ actions: [{ deviceId: 'dev_fan', power: true, level: 100 }] }), [], deviceIds, 'rule_new').ok, true);
  assert.equal(validateRule(rule({ actions: [{ deviceId: 'dev_fan', power: true, level: 101 }] }), [], deviceIds, 'rule_new').ok, false);
});

test('异常：动作指向不存在的设备被拒绝', () => {
  const result = validateRule(
    rule({ actions: [{ deviceId: 'dev_ghost', power: true, level: 50 }] }),
    [],
    deviceIds,
    'rule_new'
  );
  assert.equal(result.ok, false);
  assert.ok(result.issues.some((i) => i.message.includes('设备不存在')));
});

test('异常：冷却时间超过 3600 秒被拒绝', () => {
  assert.equal(validateRule(rule({ cooldownSec: 3600 }), [], deviceIds, 'rule_new').ok, true);
  assert.equal(validateRule(rule({ cooldownSec: 3601 }), [], deviceIds, 'rule_new').ok, false);
  assert.equal(validateRule(rule({ cooldownSec: -1 }), [], deviceIds, 'rule_new').ok, false);
});

test('边界：规则总数达到 12 条上限时不允许继续新增', () => {
  const eleven: Rule[] = [];
  for (let i = 0; i < 11; i++) {
    eleven.push(rule({ id: `rule_${i}`, name: `规则${i}` }));
  }
  assert.equal(canAddRule(eleven), true, '11 条时仍可新增');

  eleven.push(rule({ id: 'rule_11', name: '规则11' }));
  assert.equal(canAddRule(eleven), false, '12 条时达到上限');
});
