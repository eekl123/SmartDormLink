import { describe, it, expect } from '@ohos/hypium';
import {
  Condition,
  DeviceAction,
  Rule,
  canAddRule,
  defaultDevices,
  validateRule
} from '../main/ets/domain/DormLinkDomain';

const NOW: number = 1700000000000;
const DEVICE_IDS: string[] = defaultDevices().map((d) => d.id);

function makeRule(id: string, name: string, conditions: Condition[], actions: DeviceAction[],
  priority: number): Rule {
  return {
    id: id,
    name: name,
    enabled: true,
    logic: 'and',
    conditions: conditions,
    actions: actions,
    priority: priority,
    cooldownSec: 0,
    lastFiredAt: 0,
    updatedAt: NOW
  };
}

const OK_CONDITIONS: Condition[] = [{ metric: 'temperature', op: 'gte', value: 28 }];
const OK_ACTIONS: DeviceAction[] = [{ deviceId: 'dev_fan', power: true, level: 60 }];

export default function validatorTest() {
  describe('DormLinkRuleValidator', () => {
    it('normal_valid_rule_passes', 0, () => {
      const result = validateRule(makeRule('rule_new', '新风规则', OK_CONDITIONS, OK_ACTIONS, 5),
        [], DEVICE_IDS, 'rule_new');
      expect(result.ok).assertTrue();
      expect(result.issues.length).assertEqual(0);
    });

    it('exception_empty_name_rejected', 0, () => {
      const result = validateRule(makeRule('rule_new', '   ', OK_CONDITIONS, OK_ACTIONS, 5),
        [], DEVICE_IDS, 'rule_new');
      expect(result.ok).assertFalse();
      expect(result.issues[0].field).assertEqual('name');
    });

    it('exception_unknown_device_rejected', 0, () => {
      const badActions: DeviceAction[] = [{ deviceId: 'dev_ghost', power: true, level: 50 }];
      const result = validateRule(makeRule('rule_new', '幽灵设备', OK_CONDITIONS, badActions, 5),
        [], DEVICE_IDS, 'rule_new');
      expect(result.ok).assertFalse();
      expect(result.issues[0].message).assertContain('设备不存在');
    });

    it('boundary_threshold_out_of_metric_range', 0, () => {
      const okCond: Condition[] = [{ metric: 'humidity', op: 'gte', value: 100 }];
      const good = validateRule(makeRule('rule_new', '湿度上限', okCond, OK_ACTIONS, 5), [], DEVICE_IDS, 'rule_new');
      expect(good.ok).assertTrue();

      const badCond: Condition[] = [{ metric: 'humidity', op: 'gte', value: 101 }];
      const bad = validateRule(makeRule('rule_new', '湿度越界', badCond, OK_ACTIONS, 5), [], DEVICE_IDS, 'rule_new');
      expect(bad.ok).assertFalse();
    });

    it('boundary_priority_out_of_range', 0, () => {
      expect(validateRule(makeRule('rule_new', 'P1', OK_CONDITIONS, OK_ACTIONS, 1), [], DEVICE_IDS, 'rule_new').ok)
        .assertTrue();
      expect(validateRule(makeRule('rule_new', 'P10', OK_CONDITIONS, OK_ACTIONS, 10), [], DEVICE_IDS, 'rule_new').ok)
        .assertTrue();
      expect(validateRule(makeRule('rule_new', 'P11', OK_CONDITIONS, OK_ACTIONS, 11), [], DEVICE_IDS, 'rule_new').ok)
        .assertFalse();
      expect(validateRule(makeRule('rule_new', 'P0', OK_CONDITIONS, OK_ACTIONS, 0), [], DEVICE_IDS, 'rule_new').ok)
        .assertFalse();
    });

    it('boundary_rule_count_limit', 0, () => {
      const list: Rule[] = [];
      for (let i = 0; i < 12; i++) {
        list.push(makeRule(`rule_${i}`, `规则${i}`, OK_CONDITIONS, OK_ACTIONS, 5));
      }
      expect(canAddRule(list)).assertFalse();
      const eleven: Rule[] = [];
      for (let i = 0; i < 11; i++) {
        eleven.push(makeRule(`rule_${i}`, `规则${i}`, OK_CONDITIONS, OK_ACTIONS, 5));
      }
      expect(canAddRule(eleven)).assertTrue();
    });
  });
}
