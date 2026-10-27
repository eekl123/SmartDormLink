import { common } from '@kit.AbilityKit';
import { preferences } from '@kit.ArkData';
import { relationalStore } from '@kit.ArkData';
import { hilog } from '@kit.PerformanceAnalysisKit';
import {
  LogEntry,
  Snapshot,
  defaultSnapshot,
  dumpSnapshot,
  migrateSnapshot
} from '../domain/DormLinkDomain';

const DOMAIN: number = 0x0001;
const TAG: string = 'DormLink';
const PREF_NAME: string = 'dormlink_prefs';
const PREF_KEY: string = 'snapshot_v2';
const DB_NAME: string = 'dormlink.db';
const LOG_TABLE: string = 'trigger_log';

const SQL_CREATE_LOG: string = `CREATE TABLE IF NOT EXISTS ${LOG_TABLE} (
  id TEXT PRIMARY KEY NOT NULL,
  fired_at INTEGER NOT NULL,
  source TEXT NOT NULL,
  ord INTEGER NOT NULL,
  rule_id TEXT NOT NULL,
  rule_name TEXT NOT NULL,
  priority INTEGER NOT NULL,
  conditions_text TEXT NOT NULL,
  changes_text TEXT NOT NULL,
  conflict_text TEXT NOT NULL,
  fired INTEGER NOT NULL
)`;

/**
 * 数据访问层：Preferences 存整份业务快照，RDB 存执行日志。
 *
 * 设计要点：
 *  - 快照读取失败（首次启动 / 数据损坏 / 版本过新）一律回退默认种子数据，
 *    并在 UI 上给出提示，绝不白屏；
 *  - 写库全部 try/catch，失败只降级为内存态并记录 hilog，不阻断用户操作；
 *  - 日志表按 fired_at 倒序查询，仅保留最近 N 条，避免无限膨胀。
 */
export class DormLinkRepository {
  private static instance: DormLinkRepository | null = null;

  private prefs: preferences.Preferences | null = null;
  private rdb: relationalStore.RdbStore | null = null;
  private ready: boolean = false;
  private storageReady: boolean = false;
  private lastError: string = '';

  static getInstance(): DormLinkRepository {
    if (DormLinkRepository.instance === null) {
      DormLinkRepository.instance = new DormLinkRepository();
    }
    return DormLinkRepository.instance;
  }

  isStorageReady(): boolean {
    return this.storageReady;
  }

  getLastError(): string {
    return this.lastError;
  }

  async init(context: common.UIAbilityContext): Promise<void> {
    if (this.ready) {
      return;
    }
    try {
      const options: preferences.Options = { name: PREF_NAME };
      this.prefs = await preferences.getPreferences(context, options);
    } catch (err) {
      this.lastError = `Preferences 初始化失败：${JSON.stringify(err)}`;
      hilog.error(DOMAIN, TAG, '%{public}s', this.lastError);
    }
    try {
      const config: relationalStore.StoreConfig = {
        name: DB_NAME,
        securityLevel: relationalStore.SecurityLevel.S1
      };
      this.rdb = await relationalStore.getRdbStore(context, config);
      await this.rdb.executeSql(SQL_CREATE_LOG);
    } catch (err) {
      this.lastError = `RDB 初始化失败：${JSON.stringify(err)}`;
      hilog.error(DOMAIN, TAG, '%{public}s', this.lastError);
    }
    this.storageReady = this.prefs !== null;
    this.ready = true;
  }

  /** 读取快照：失败返回默认种子数据，保证冷启动可用 */
  async loadSnapshot(now: number): Promise<Snapshot> {
    if (this.prefs === null) {
      return defaultSnapshot(now);
    }
    try {
      const raw: string = await this.prefs.get(PREF_KEY, '') as string;
      if (raw === undefined || raw === null || raw.length === 0) {
        const fresh = defaultSnapshot(now);
        await this.saveSnapshot(fresh);
        return fresh;
      }
      const snapshot = migrateSnapshot(raw);
      if (snapshot === null) {
        this.lastError = '本地数据损坏或版本不兼容，已回退到默认配置';
        hilog.warn(DOMAIN, TAG, '%{public}s', this.lastError);
        return defaultSnapshot(now);
      }
      return snapshot;
    } catch (err) {
      this.lastError = `读取快照失败：${JSON.stringify(err)}`;
      hilog.error(DOMAIN, TAG, '%{public}s', this.lastError);
      return defaultSnapshot(now);
    }
  }

  async saveSnapshot(snapshot: Snapshot): Promise<boolean> {
    if (this.prefs === null) {
      return false;
    }
    try {
      const text: string = dumpSnapshot(snapshot);
      await this.prefs.put(PREF_KEY, text);
      await this.prefs.flush();
      return true;
    } catch (err) {
      this.lastError = `保存快照失败：${JSON.stringify(err)}`;
      hilog.error(DOMAIN, TAG, '%{public}s', this.lastError);
      return false;
    }
  }

  async clearSnapshot(): Promise<boolean> {
    if (this.prefs === null) {
      return false;
    }
    try {
      await this.prefs.delete(PREF_KEY);
      await this.prefs.flush();
      return true;
    } catch (err) {
      this.lastError = `清空快照失败：${JSON.stringify(err)}`;
      return false;
    }
  }

  async appendLogs(logs: LogEntry[]): Promise<number> {
    if (this.rdb === null || logs.length === 0) {
      return 0;
    }
    let inserted: number = 0;
    try {
      for (let i = 0; i < logs.length; i++) {
        const log = logs[i];
        const values: relationalStore.ValuesBucket = {
          'id': log.id,
          'fired_at': log.at,
          'source': log.source,
          'ord': log.order,
          'rule_id': log.ruleId,
          'rule_name': log.ruleName,
          'priority': log.priority,
          'conditions_text': log.conditionsText,
          'changes_text': log.changesText,
          'conflict_text': log.conflictText,
          'fired': log.fired ? 1 : 0
        };
        await this.rdb.insert(LOG_TABLE, values);
        inserted++;
      }
    } catch (err) {
      this.lastError = `写入执行日志失败：${JSON.stringify(err)}`;
      hilog.error(DOMAIN, TAG, '%{public}s', this.lastError);
    }
    return inserted;
  }

  async queryLogs(limit: number): Promise<LogEntry[]> {
    const result: LogEntry[] = [];
    if (this.rdb === null) {
      return result;
    }
    try {
      const predicates = new relationalStore.RdbPredicates(LOG_TABLE);
      predicates.orderByDesc('fired_at');
      predicates.orderByDesc('ord');
      predicates.limitAs(limit);
      const columns: string[] = ['id', 'fired_at', 'source', 'ord', 'rule_id', 'rule_name',
        'priority', 'conditions_text', 'changes_text', 'conflict_text', 'fired'];
      const rs = await this.rdb.query(predicates, columns);
      while (rs.goToNextRow()) {
        result.push({
          id: rs.getString(rs.getColumnIndex('id')),
          at: rs.getLong(rs.getColumnIndex('fired_at')),
          source: rs.getString(rs.getColumnIndex('source')),
          order: rs.getLong(rs.getColumnIndex('ord')),
          ruleId: rs.getString(rs.getColumnIndex('rule_id')),
          ruleName: rs.getString(rs.getColumnIndex('rule_name')),
          priority: rs.getLong(rs.getColumnIndex('priority')),
          conditionsText: rs.getString(rs.getColumnIndex('conditions_text')),
          changesText: rs.getString(rs.getColumnIndex('changes_text')),
          conflictText: rs.getString(rs.getColumnIndex('conflict_text')),
          fired: rs.getLong(rs.getColumnIndex('fired')) === 1
        });
      }
      rs.close();
    } catch (err) {
      this.lastError = `查询执行日志失败：${JSON.stringify(err)}`;
      hilog.error(DOMAIN, TAG, '%{public}s', this.lastError);
    }
    return result;
  }

  async clearLogs(): Promise<boolean> {
    if (this.rdb === null) {
      return false;
    }
    try {
      const predicates = new relationalStore.RdbPredicates(LOG_TABLE);
      await this.rdb.delete(predicates);
      return true;
    } catch (err) {
      this.lastError = `清空执行日志失败：${JSON.stringify(err)}`;
      return false;
    }
  }

  /** 恢复出厂：清空快照与日志，返回新的种子数据 */
  async resetAll(now: number): Promise<Snapshot> {
    await this.clearSnapshot();
    await this.clearLogs();
    const fresh = defaultSnapshot(now);
    await this.saveSnapshot(fresh);
    return fresh;
  }
}
