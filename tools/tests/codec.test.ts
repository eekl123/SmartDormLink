/**
 * 持久化编解码单元测试（正常 / 边界 / 异常）
 * 覆盖「退出应用再启动后恢复进度」所依赖的序列化链路。
 * 运行：node --test tools/tests
 */
import { test } from 'node:test';
import assert from 'node:assert';

import {
  dumpSnapshot,
  parseSnapshot,
  migrateSnapshot,
  defaultSnapshot,
  seedRules,
  defaultDevices,
  defaultEnv,
  runEngine,
  SNAPSHOT_VERSION,
  type Snapshot
} from '../../entry/src/main/ets/domain/DormLinkDomain.ts';

const NOW = 1_700_000_000_000;

test('正常：快照 dump 后 parse 可完整还原设备、环境与规则', () => {
  const snapshot = defaultSnapshot(NOW);
  const text = dumpSnapshot(snapshot);
  assert.equal(typeof text, 'string');

  const restored = parseSnapshot(text);
  assert.ok(restored, '应能解析出快照');
  assert.equal(restored!.version, SNAPSHOT_VERSION);
  assert.equal(restored!.devices.length, defaultDevices().length);
  assert.equal(restored!.env.temperature, defaultEnv().temperature);
  assert.equal(restored!.rules.length, seedRules(NOW).length);
  assert.equal(restored!.rules[1].conditions.length, 2, '双条件规则应完整保留');
});

test('正常：模拟「改环境 → 触发规则 → 保存 → 重启恢复」全链路', () => {
  const snapshot = defaultSnapshot(NOW);
  // 1. 用户把环境改成梅雨午后
  snapshot.env = { temperature: 31.5, humidity: 88, illuminance: 900 };
  // 2. 引擎执行，设备状态发生变化
  const outcome = runEngine({
    rules: snapshot.rules,
    devices: snapshot.devices,
    env: snapshot.env,
    now: NOW,
    source: 'unit-test'
  });
  assert.ok(outcome.firedCount >= 2, '梅雨午后应至少触发 2 条规则');
  snapshot.devices = outcome.devices;
  snapshot.rules = outcome.rules;

  // 3. 落盘
  const text = dumpSnapshot(snapshot);
  // 4. 模拟进程重启后重新读取
  const restored = parseSnapshot(text)!;

  assert.equal(restored.env.humidity, 88);
  const humidifier = restored.devices.find((d) => d.id === 'dev_humidifier')!;
  assert.equal(humidifier.power, true, '加湿器开着，开机后应保持');
  const fan = restored.devices.find((d) => d.id === 'dev_fan')!;
  assert.equal(fan.power, true, '温度 31.5 应保持风扇开启');
  const fired = restored.rules.find((r) => r.id === 'rule_02_damp')!;
  assert.equal(fired.lastFiredAt, NOW, 'lastFiredAt 应被持久化，用于冷却判断');
});

test('边界：空字符串、空对象、非快照结构都返回 null 而不抛异常', () => {
  assert.equal(parseSnapshot(''), null);
  assert.equal(parseSnapshot('   '), null);
  assert.equal(parseSnapshot('{}'), null, '缺少 version 视为无效');
  assert.equal(parseSnapshot('[]'), null, '数组不是合法快照');
  assert.equal(parseSnapshot('null'), null);
});

test('异常：损坏的 JSON 不会导致崩溃，返回 null 由上层回退种子数据', () => {
  const broken = '{"version":2,"devices":[{"id":"dev_light"';
  assert.equal(parseSnapshot(broken), null);

  const garbage = 'not-a-json-at-all';
  assert.equal(parseSnapshot(garbage), null);
});

test('异常：版本号高于当前程序支持的版本时拒绝解析（防降级写坏数据）', () => {
  const future = JSON.stringify({ version: SNAPSHOT_VERSION + 1, devices: [], rules: [] });
  assert.equal(parseSnapshot(future), null);
});

test('边界：v1 旧快照缺少 cooldownSec / lastFiredAt 时按默认值补齐', () => {
  const v1 = JSON.stringify({
    version: 1,
    savedAt: NOW,
    env: { temperature: 22, humidity: 45, illuminance: 200 },
    devices: [{ id: 'dev_fan', kind: 'fan', name: '循环扇', room: '卧室', power: true, level: 30 }],
    rules: [
      {
        id: 'rule_legacy',
        name: '旧规则',
        enabled: true,
        logic: 'and',
        conditions: [{ metric: 'temperature', op: 'gt', value: 26 }],
        actions: [{ deviceId: 'dev_fan', power: true, level: 30 }],
        priority: 4,
        updatedAt: NOW
      }
    ]
  });

  const migrated = migrateSnapshot(v1);
  assert.ok(migrated, 'v1 快照应可迁移');
  assert.equal(migrated!.rules[0].cooldownSec, 0, '缺失字段补默认 0');
  assert.equal(migrated!.rules[0].lastFiredAt, 0);
  assert.equal(migrated!.devices[0].power, true, '设备状态保留');
});

test('边界：字段类型脏数据被清洗为合法值，不会污染引擎', () => {
  const dirty = JSON.stringify({
    version: 2,
    savedAt: NOW,
    env: { temperature: 'hot', humidity: 130, illuminance: -50 },
    devices: [{ id: '', kind: 'unknown', name: '', room: '', power: 'yes', level: 260 }],
    rules: [
      {
        id: '',
        name: '',
        enabled: 'true',
        logic: 'weird',
        conditions: [{ metric: 'bogus', op: 'bogus', value: 'x' }],
        actions: [{ deviceId: '', power: 'no', level: 999 }],
        priority: 99,
        cooldownSec: -5,
        updatedAt: NOW
      }
    ]
  });

  const parsed = parseSnapshot(dirty);
  assert.ok(parsed, '脏数据应被清洗而不是丢弃整个快照');
  assert.equal(parsed!.env.temperature, defaultEnv().temperature, '非数字回退默认值');
  assert.equal(parsed!.env.humidity, 100, '超上界裁剪到 100');
  assert.equal(parsed!.env.illuminance, 0, '负数裁剪到 0');
  assert.equal(parsed!.devices[0].level, 100, '设备档位裁剪到 100');
  assert.equal(parsed!.devices[0].power, false, '非布尔开关回退 false');
  assert.equal(parsed!.rules[0].priority, 10, '优先级裁剪到 10');
  assert.equal(parsed!.rules[0].cooldownSec, 0, '负冷却时间裁剪到 0');
  assert.equal(parsed!.rules[0].logic, 'and', '非法组合方式回退 and');
});

test('边界：规则列表为空时不回填种子数据（尊重用户删光规则的操作）', () => {
  const empty = JSON.stringify({
    version: 2,
    savedAt: NOW,
    env: defaultEnv(),
    devices: defaultDevices(),
    rules: []
  });
  const parsed = parseSnapshot(empty)!;
  assert.equal(parsed.rules.length, 0);
  assert.equal(parsed.devices.length, 4, '设备仍保留');
});

test('边界：快照体积与解析性能满足单机使用（12 条规则往返 < 50ms）', () => {
  const snapshot: Snapshot = defaultSnapshot(NOW);
  const start = process.hrtime.bigint();
  for (let i = 0; i < 200; i++) {
    const text = dumpSnapshot(snapshot);
    const parsed = parseSnapshot(text);
    assert.ok(parsed);
  }
  const costMs = Number(process.hrtime.bigint() - start) / 1_000_000;
  assert.ok(costMs < 50, `200 次往返应在 50ms 内，实际 ${costMs.toFixed(2)}ms`);
});
