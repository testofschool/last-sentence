import { DurableObject } from 'cloudflare:workers';
import { completionCap, budgetCeilingMicrousd } from './limits_config.js';

// One instance per application: its coordination atom is the shared provider quota.
// SQLite operations are synchronous and the whole reservation uses a transaction.
export class UsageLimits extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL)');
  }

  reserve(kind, amount, ceiling) {
    if (!['seoul', 'completion', 'search'].includes(kind) || !Number.isSafeInteger(amount) || amount < 0 || !Number.isSafeInteger(ceiling) || ceiling < 0) {
      throw new Error('Invalid quota reservation');
    }
    const day = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
    const key = kind === 'seoul' ? `seoul:${day}` : kind === 'search' ? 'search:calls' : 'completion:reserved-microusd';
    return this.ctx.storage.transactionSync(() => {
      const row = this.ctx.storage.sql.exec('SELECT value FROM counters WHERE name = ?', key).toArray()[0];
      const used = row?.value || 0;
      const calls = kind === 'completion' ? (this.ctx.storage.sql.exec('SELECT value FROM counters WHERE name = ?', 'completion:calls').toArray()[0]?.value || 0) : 0;
      const maxCalls = completionCap(this.env);
      if (used + amount > ceiling || (kind === 'completion' && calls >= maxCalls)) return { allowed: false, used, ceiling, calls };
      this.ctx.storage.sql.exec('INSERT INTO counters(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value', key, used + amount);
      if (kind === 'completion') this.ctx.storage.sql.exec('INSERT INTO counters(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value', 'completion:calls', calls + 1);
      return { allowed: true, used: used + amount, ceiling, calls: calls + (kind === 'completion' ? 1 : 0) };
    });
  }

  inspect() {
    const calls = this.ctx.storage.sql.exec('SELECT value FROM counters WHERE name = ?', 'completion:calls').toArray()[0]?.value || 0;
    const reserved = this.ctx.storage.sql.exec('SELECT value FROM counters WHERE name = ?', 'completion:reserved-microusd').toArray()[0]?.value || 0;
    const day = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' });
    const seoul = this.ctx.storage.sql.exec('SELECT value FROM counters WHERE name = ?', `seoul:${day}`).toArray()[0]?.value || 0;
    const searches = this.ctx.storage.sql.exec('SELECT value FROM counters WHERE name = ?', 'search:calls').toArray()[0]?.value || 0;
    return { completion_cap: completionCap(this.env), completion_calls_used: calls, completion_calls_remaining: Math.max(0, completionCap(this.env) - calls), reserved_usd: reserved / 1_000_000, reservation_budget_usd: budgetCeilingMicrousd(this.env) / 1_000_000, seoul_calls_used_today: seoul, seoul_daily_cap: 950, search_calls_used: searches, search_lifetime_cap: 100 };
  }
}
