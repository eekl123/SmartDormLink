import { describe, it, expect } from '@ohos/hypium';
import {
  Condition,
  DeviceAction,
  Rule,
  RuleLogic,
  defaultDevices,
  evaluateCondition,
  isCoolingDown,
  runEngine,
  seedRules
} from '../main/ets/domain/DormLinkDomain';

const NOW: number = 1700000000000;

function makeRule(id: string, name: string, conditions: Condition[], actions: DeviceAction[],
  priority: number, logic: RuleLogic): Rule {
  return {
    id: id,
    name: name,
    enabled: true,
    logic: logic,
    conditions: conditions,
    actions: actions,
    priority: priority,
    cooldownSec: 0,
    lastFiredAt: 0,
    updatedAt: NOW
  };
}

const FAN_RULE: Rule = makeRule(
  'rule_test',
  '测试规则',
  [{ metric: 'temperature', op: 'gte', value: 28 }],
  [{ deviceId: 'dev_fan', power: true, level: 60 }],
  5,
  'and'
);

export default function engineTest() {
  describe('DormLinkRuleEngine', () => {
    // ---------- 正常 ----------
    it('normal_high_temperature_fires_fan', 0, () => {
      const outcome = runEngine({
        rules: [FAN_RULE],
        devices: defaultDevices(),
        env: { temperature: 30, humidity: 50, illuminance: 300 },
        now: NOW,
        source: 'unit'
      });
      const fan = outcome.devices.find((d) => d.id === 'dev_fan');
      expect(fan!.power).assertTrue();
      expect(fan!.level).assertEqual(60);
      expect(outcome.firedCount).assertEqual(1);
      expect(outcome.logs[0].order).assertEqual(1);
    });

    it('normal_dual_condition_requires_both', 0, () => {
      const rule = makeRule(
        'rule_damp',
        '闷热联动除湿',
        [
          { metric: 'temperature', op: 'gte', value: 26 },
          { metric: 'humidity', op: 'gte', value: 75 }
        ],
        [{ deviceId: 'dev_humidifier', power: true, level: 70 }],
        8,
        'and'
      );
      const dry = runEngine({
        rules: [rule],
        devices: defaultDevices(),
        env: { temperature: 30, humidity: 60, illuminance: 300 },
        now: NOW,
        source: 'unit'
      });
      expect(dry.firedCount).assertEqual(0);

      const wet = runEngine({
        rules: [rule],
        devices: defaultDevices(),
        env: { temperature: 30, humidity: 80, illuminance: 300 },
        now: NOW,
        source: 'unit'
      });
      expect(wet.firedCount).assertEqual(1);
    });

    // ---------- 边界 ----------
    it('boundary_gte_equal_threshold', 0, () => {
      expect(evaluateCondition({ metric: 'temperature', op: 'gte', value: 28 }, {
        temperature: 28, humidity: 50, illuminance: 300
      })).assertTrue();
      expect(evaluateCondition({ metric: 'temperature', op: 'gt', value: 28 }, {
        temperature: 28, humidity: 50, illuminance: 300
      })).assertFalse();
    });

    it('boundary_level_clamped_to_range', 0, () => {
      const rule = makeRule(
        'rule_clamp',
        '越界裁剪',
        [{ metric: 'temperature', op: 'gte', value: 20 }],
        [{ deviceId: 'dev_fan', power: true, level: 180 }],
        5,
        'and'
      );
      const outcome = runEngine({
        rules: [rule],
        devices: defaultDevices(),
        env: { temperature: 30, humidity: 50, illuminance: 300 },
        now: NOW,
        source: 'unit'
      });
      expect(outcome.devices.find((d) => d.id === 'dev_fan')!.level).assertEqual(100);
    });

    it('boundary_cooldown_blocks_repeat_fire', 0, () => {
      const cooling: Rule = {
        id: 'rule_cool',
        name: '冷却规则',
        enabled: true,
        logic: 'and',
        conditions: [{ metric: 'temperature', op: 'gte', value: 28 }],
        actions: [{ deviceId: 'dev_fan', power: true, level: 60 }],
        priority: 5,
        cooldownSec: 60,
        lastFiredAt: NOW - 30000,
        updatedAt: NOW
      };
      expect(isCoolingDown(cooling, NOW)).assertTrue();
      const blocked = runEngine({
        rules: [cooling],
        devices: defaultDevices(),
        env: { temperature: 30, humidity: 50, illuminance: 300 },
        now: NOW,
        source: 'unit'
      });
      expect(blocked.firedCount).assertEqual(0);
      const expired = runEngine({
        rules: [cooling],
        devices: defaultDevices(),
        env: { temperature: 30, humidity: 50, illuminance: 300 },
        now: NOW + 31000,
        source: 'unit'
      });
      expect(expired.firedCount).assertEqual(1);
    });

    // ---------- 异常 ----------
    it('exception_missing_device_action_skipped', 0, () => {
      const rule = makeRule(
        'rule_bad',
        '无效动作',
        [{ metric: 'temperature', op: 'gte', value: 20 }],
        [{ deviceId: 'dev_missing', power: true, level: 50 }],
        5,
        'and'
      );
      const outcome = runEngine({
        rules: [rule],
        devices: defaultDevices(),
        env: { temperature: 30, humidity: 50, illuminance: 300 },
        now: NOW,
        source: 'unit'
      });
      expect(outcome.firedCount).assertEqual(0);
      expect(outcome.logs[0].conflictText).assertContain('动作目标不存在');
    });

    // ---------- 冲突 ----------
    it('conflict_higher_priority_wins', 0, () => {
      const low = makeRule(
        'rule_low',
        '基础补光',
        [{ metric: 'illuminance', op: 'lt', value: 400 }],
        [{ deviceId: 'dev_light', power: true, level: 40 }],
        3,
        'and'
      );
      const high = makeRule(
        'rule_high',
        '强补光',
        [{ metric: 'illuminance', op: 'lt', value: 400 }],
        [{ deviceId: 'dev_light', power: true, level: 90 }],
        6,
        'and'
      );
      const outcome = runEngine({
        rules: [low, high],
        devices: defaultDevices(),
        env: { temperature: 25, humidity: 50, illuminance: 100 },
        now: NOW,
        source: 'unit'
      });
      expect(outcome.devices.find((d) => d.id === 'dev_light')!.level).assertEqual(90);
      expect(outcome.conflicts.length).assertEqual(1);
      expect(outcome.conflicts[0].winnerRuleId).assertEqual('rule_high');
    });

    it('normal_seed_rules_cover_four_devices', 0, () => {
      const rules = seedRules(NOW);
      expect(rules.length).assertLarger(3);
      const kinds: string[] = [];
      for (let i = 0; i < rules.length; i++) {
        for (let a = 0; a < rules[i].actions.length; a++) {
          const id = rules[i].actions[a].deviceId;
          if (kinds.indexOf(id) < 0) {
            kinds.push(id);
          }
        }
      }
      expect(kinds.length).assertEqual(4);
    });
  });
}
