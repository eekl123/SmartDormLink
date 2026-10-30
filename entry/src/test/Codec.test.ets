import { describe, it, expect } from '@ohos/hypium';
import {
  Condition,
  DeviceAction,
  DeviceState,
  EnvState,
  Rule,
  SNAPSHOT_VERSION,
  defaultSnapshot,
  dumpSnapshot,
  migrateSnapshot,
  parseSnapshot,
  runEngine
} from '../main/ets/domain/DormLinkDomain';

const NOW: number = 1700000000000;

/** 用于构造「历史版本」快照的宽松类型，便于测试脏数据兼容性 */
interface LegacyRule {
  id: string;
  name: string;
  enabled: boolean;
  logic: string;
  conditions: Condition[];
  actions: DeviceAction[];
  priority: number;
  updatedAt: number;
}

interface LegacySnapshot {
  version: number;
  savedAt: number;
  env: EnvState;
  devices: DeviceState[];
  rules: LegacyRule[];
}

interface DirtyEnv {
  temperature: string;
  humidity: number;
  illuminance: number;
}

interface DirtyDevice {
  id: string;
  kind: string;
  name: string;
  room: string;
  power: string;
  level: number;
}

interface DirtySnapshot {
  version: number;
  savedAt: number;
  env: DirtyEnv;
  devices: DirtyDevice[];
  rules: LegacyRule[];
}

export default function codecTest() {
  describe('DormLinkPersistenceCodec', () => {
    it('normal_snapshot_round_trip', 0, () => {
      const snapshot = defaultSnapshot(NOW);
      const restored = parseSnapshot(dumpSnapshot(snapshot));
      expect(restored !== null).assertTrue();
      expect(restored!.version).assertEqual(SNAPSHOT_VERSION);
      expect(restored!.rules.length).assertEqual(snapshot.rules.length);
      expect(restored!.devices.length).assertEqual(snapshot.devices.length);
    });

    it('normal_restart_restores_device_state', 0, () => {
      const snapshot = defaultSnapshot(NOW);
      snapshot.env = { temperature: 31.5, humidity: 88, illuminance: 900 };
      const outcome = runEngine({
        rules: snapshot.rules,
        devices: snapshot.devices,
        env: snapshot.env,
        now: NOW,
        source: 'unit'
      });
      snapshot.devices = outcome.devices;
      const restored = parseSnapshot(dumpSnapshot(snapshot))!;
      expect(restored.devices.find((d) => d.id === 'dev_humidifier')!.power).assertTrue();
      expect(restored.env.humidity).assertEqual(88);
    });

    it('exception_corrupted_json_returns_null', 0, () => {
      expect(parseSnapshot('{"version":2,"devices":[') === null).assertTrue();
      expect(parseSnapshot('not-a-json') === null).assertTrue();
      expect(parseSnapshot('') === null).assertTrue();
    });

    it('exception_future_version_rejected', 0, () => {
      const future = `{"version":${SNAPSHOT_VERSION + 1},"devices":[],"rules":[]}`;
      expect(parseSnapshot(future) === null).assertTrue();
    });

    it('boundary_v1_snapshot_migrated', 0, () => {
      const legacyRule: LegacyRule = {
        id: 'rule_legacy',
        name: '旧规则',
        enabled: true,
        logic: 'and',
        conditions: [{ metric: 'temperature', op: 'gt', value: 26 }],
        actions: [{ deviceId: 'dev_fan', power: true, level: 30 }],
        priority: 4,
        updatedAt: NOW
      };
      const legacyDevice: DeviceState = {
        id: 'dev_fan',
        kind: 'fan',
        name: '循环扇',
        room: '卧室',
        power: true,
        level: 30
      };
      const v1: LegacySnapshot = {
        version: 1,
        savedAt: NOW,
        env: { temperature: 22, humidity: 45, illuminance: 200 },
        devices: [legacyDevice],
        rules: [legacyRule]
      };
      const migrated = migrateSnapshot(JSON.stringify(v1));
      expect(migrated !== null).assertTrue();
      expect(migrated!.rules[0].cooldownSec).assertEqual(0);
      expect(migrated!.devices[0].power).assertTrue();
    });

    it('boundary_dirty_fields_sanitized', 0, () => {
      const dirtyDevice: DirtyDevice = {
        id: '',
        kind: 'unknown',
        name: '',
        room: '',
        power: 'yes',
        level: 260
      };
      const dirty: DirtySnapshot = {
        version: 2,
        savedAt: NOW,
        env: { temperature: 'hot', humidity: 130, illuminance: -50 },
        devices: [dirtyDevice],
        rules: []
      };
      const parsed = parseSnapshot(JSON.stringify(dirty))!;
      expect(parsed.env.humidity).assertEqual(100);
      expect(parsed.env.illuminance).assertEqual(0);
      expect(parsed.devices[0].level).assertEqual(100);
    });
  });
}
