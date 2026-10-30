export function completionCap(env) {
  const value = Number(env.LIVE_MAX_COMPLETIONS || 300);
  return Number.isFinite(value) ? Math.min(2048, Math.max(0, Math.floor(value))) : 0;
}
export function budgetCeilingMicrousd(env) {
  const value = Number(env.LIVE_BUDGET_USD || 3);
  return Number.isFinite(value) ? Math.min(3_000_000, Math.max(0, Math.floor(value * 1_000_000))) : 0;
}
