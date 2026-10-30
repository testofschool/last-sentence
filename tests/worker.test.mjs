import test from 'node:test';
import assert from 'node:assert/strict';
import { handleRequest, MODELS, budget } from '../worker/src/core.js';
import { completionCap, budgetCeilingMicrousd } from '../worker/src/limits_config.js';

const endpoint = 'https://example.test';
const usage = { prompt_tokens: 100, completion_tokens: 20, total_tokens: 120 };
const planBody = { current_station: '왕십리', exit_station: '성수', stations_left: 3, remaining_s: 300, eta_source: 'synthetic-fixture', remaining_scenes: [{ id: 'scene-1', chars: 1500 }] };
function request(path, body, extra = {}) {
  const method = body === undefined ? 'GET' : 'POST';
  return new Request(endpoint + path, { method, headers: { authorization: 'Bearer a-long-local-test-session-token', ...(body === undefined ? {} : { 'content-type': 'application/json' }), ...extra }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
}
function environment(overrides = {}) {
  return { ENABLE_LIVE: 'true', LIVE_ACCESS_TOKEN: 'a-long-local-test-session-token', NEBIUS_API_KEY: 'server-nebius-mock-key', SEOUL_RT_KEY: 'SAMPLE', TAVILY_API_KEY: 'server-tavily-mock-key', LIMITS: { getByName: () => ({ reserve: async () => ({ allowed: true }), inspect: async () => ({ completion_cap: 300, completion_calls_used: 0, completion_calls_remaining: 300, reserved_usd: 0, reservation_budget_usd: 3 }) }) }, ...overrides };
}
function mockFetch(messages = [], options = {}) {
  const seen = [];
  const fetch = async (url, init = {}) => {
    seen.push({ url, init });
    if (url.endsWith('/models_info')) return Response.json([{ status: 'active', flavors: Object.values(MODELS).map(model_id => ({ model_id, input_price_per_million_tokens: 0.1, output_price_per_million_tokens: 0.3 })) }]);
    if (url.endsWith('/chat/completions')) {
      const next = messages.shift(); if (next instanceof Response) return next;
      return Response.json({ choices: [{ message: next }], ...(options.missingUsage ? {} : { usage }) }, { headers: { 'x-ratelimit-remaining-requests': '58' } });
    }
    if (url.includes('/api/subway/')) return Response.json({ errorMessage: { code: 'INFO-000' }, realtimePositionList: [{ trainNo: '1234', statnNm: '성수', recptnDt: '2026-10-30 10:15:00', trainSttus: '1', secret_field: 'must disappear' }] });
    if (url.endsWith('/search')) return Response.json({ results: [{ url: 'https://official.example/park', content: options.searchContent ?? 'A park beside the station.' }] });
    throw new Error('Unexpected mock URL');
  };
  return { fetch, seen };
}
async function call(path, body, env = {}, deps = { fetch: () => { throw Error('Network forbidden'); } }, headers = {}) {
  const response = await handleRequest(request(path, body, headers), env, deps);
  return { status: response.status, body: await response.json(), response };
}

test('keyless status and position never call providers or invent model use', async () => {
  const status = await call('/api/status');
  assert.equal(status.status, 200); assert.equal(status.body.inference_enabled, false);
  assert.equal(status.body.mode, 'replay-only'); assert.equal(status.body.model, null);
  const pos = await call('/api/position?line=2%ED%98%B8%EC%84%A0');
  assert.equal(pos.status, 200); assert.equal(pos.body.mode, 'replay-forced'); assert.deepEqual(pos.body.positions, []);
  const plan = await call('/api/plan', planBody);
  assert.equal(plan.status, 503); assert.equal(plan.body.error, 'live_disabled'); assert.equal(plan.body.usage, null);
});
test('configured services require the session credential and reject other origins', async () => {
  const env = environment(), deps = mockFetch();
  assert.equal((await call('/api/plan', planBody, env, deps, { authorization: 'Bearer wrong' })).status, 401);
  assert.equal((await call('/api/plan', planBody, env, deps, { origin: 'https://attacker.example' })).status, 403);
  assert.equal(deps.seen.length, 0);
});
test('exact configured origin receives CORS without a wildcard', async () => {
  const result = await call('/api/status', undefined, environment({ ALLOWED_ORIGIN: 'https://ui.example' }), mockFetch(), { origin: 'https://ui.example' });
  assert.equal(result.response.headers.get('access-control-allow-origin'), 'https://ui.example');
});
test('missing accounting binding disables live mode', async () => {
  const result = await call('/api/status', undefined, environment({ LIMITS: null }));
  assert.equal(result.body.inference_enabled, false);
});
test('completion count configuration is explicit and cannot raise the three-dollar reservation cap', () => {
  assert.equal(completionCap({}), 300);
  assert.equal(completionCap({ LIVE_MAX_COMPLETIONS: '811' }), 811);
  assert.equal(completionCap({ LIVE_MAX_COMPLETIONS: '99999' }), 2048);
  assert.equal(completionCap({ LIVE_MAX_COMPLETIONS: 'garbage' }), 0);
  assert.equal(budgetCeilingMicrousd({ LIVE_BUDGET_USD: '90' }), 3000000);
  assert.equal(budgetCeilingMicrousd({ LIVE_BUDGET_USD: 'garbage' }), 0);
});
test('authorized status reports remaining account reservations and anonymous status hides usage', async () => {
  const result = await call('/api/status', undefined, environment(), mockFetch());
  assert.equal(result.body.limits.completion_calls_remaining, 300);
  const response = await handleRequest(new Request(endpoint + '/api/status'), environment(), mockFetch());
  const anonymous = await response.json();
  assert.equal(anonymous.limits.completion_calls_remaining, null);
  assert.equal(anonymous.limits.completion_cap, 300);
});
test('plan rejects invented/missing timing provenance before any inference', async () => {
  const deps = mockFetch();
  for (const eta_source of [undefined, 'gps-doors-open']) {
    const result = await call('/api/plan', { ...planBody, eta_source }, environment(), deps);
    assert.equal(result.status, 400); assert.equal(result.body.error, 'eta_source_required');
  }
  assert.equal(deps.seen.length, 0);
});
test('plan executes tools, gives their results back to the model and controls ETA server-side', async () => {
  const deps = mockFetch([
    { role: 'assistant', content: null, tool_calls: [
      { id: 'eta', type: 'function', function: { name: 'eta_to_station', arguments: '{}' } },
      { id: 'budget', type: 'function', function: { name: 'budget', arguments: '{}' } },
      { id: 'ops', type: 'function', function: { name: 'scene_ops', arguments: JSON.stringify({ ops: [{ scene: 'scene-1', op: 'compress', reason: 'Less travel time remains.' }] }) } },
    ] },
    { content: JSON.stringify({ remaining_s: 99999, budget_chars: 99999, ops: [{ scene: 'scene-1', op: 'compress', reason: 'Fit the time.' }], log: '3 stations left. Compressing scene 1.' }) },
  ]);
  const result = await call('/api/plan', planBody, environment(), deps);
  assert.equal(result.status, 200); assert.equal(result.body.plan.remaining_s, 300); assert.equal(result.body.plan.budget_chars, budget(300));
  assert.equal(result.body.required_tools_completed, true); assert.equal(result.body.tool_calls_supported, true);
  assert.equal(result.body.tool_executions.length, 3); assert.equal(result.body.calls.length, 2);
  assert.equal(result.body.usage.prompt_tokens, 200); assert.ok(result.body.cost_usd > 0);
  assert.equal(result.body.calls[0].pricing.input_price_per_million_tokens, 0.1);
  assert.equal(result.body.calls[0].pricing.output_price_per_million_tokens, 0.3);
  assert.ok(result.body.calls[0].pricing.observed_at);
  const bodies = deps.seen.filter(v => v.url.endsWith('/chat/completions')).map(v => JSON.parse(v.init.body));
  assert.equal(bodies[1].messages.filter(v => v.role === 'tool').length, 3);
  assert.equal(bodies[0].max_tokens, 400);
});
test('two no-tool attempts fall back to JSON and count every completion', async () => {
  const deps = mockFetch([{ content: '{}' }, { content: '{}' }, { content: '{"ops":[],"log":"Keep the remaining scene."}' }]);
  const result = await call('/api/plan', planBody, environment(), deps);
  assert.equal(result.status, 200); assert.equal(result.body.tool_calls_supported, false); assert.equal(result.body.required_tools_completed, false); assert.equal(result.body.calls.length, 3); assert.equal(result.body.usage.total_tokens, 360);
});
test('oversized echoed tool context cannot exceed the preregistered 32768-token input envelope', async () => {
  const deps = mockFetch([{ role: 'assistant', content: 'x'.repeat(33000), tool_calls: [{ id: 'eta', type: 'function', function: { name: 'eta_to_station', arguments: '{}' } }] }]);
  const result = await call('/api/plan', planBody, environment(), deps);
  assert.equal(result.status, 502); assert.equal(result.body.error, 'input_token_bound_exceeded');
  assert.equal(deps.seen.filter(v => v.url.endsWith('/chat/completions')).length, 1);
  assert.equal(deps.seen.filter(v => v.url.endsWith('/models_info')).length, 1);
  assert.equal(result.body.calls.length, 1); assert.ok(result.body.cost_usd > 0);
});
test('unknown tool or scene operations are rejected with attempted-call receipts', async () => {
  const deps = mockFetch([{ tool_calls: [{ id: 'bad', type: 'function', function: { name: 'shell', arguments: '{}' } }] }]);
  const result = await call('/api/plan', planBody, environment(), deps);
  assert.equal(result.status, 502); assert.equal(result.body.error, 'unsupported_tool'); assert.equal(result.body.calls.length, 1);
});
test('quota rejection occurs before provider completion', async () => {
  const deps = mockFetch();
  const env = environment({ LIMITS: { getByName: () => ({ reserve: async () => ({ allowed: false }) }) } });
  const result = await call('/api/plan', planBody, env, deps);
  assert.equal(result.status, 429); assert.equal(result.body.error, 'inference_quota');
  assert.equal(deps.seen.filter(v => v.url.endsWith('/chat/completions')).length, 0);
});
test('unknown model pricing fails closed before quota or completion', async () => {
  const deps = { fetch: async () => Response.json([]) };
  const result = await call('/api/plan', planBody, environment(), deps);
  assert.equal(result.status, 503); assert.equal(result.body.error, 'pricing_unavailable');
});
test('null, missing, empty, or textual catalog prices cannot silently become free inference', async () => {
  for (const price of [null, undefined, '', '0.1']) {
    let calls = 0;
    const deps = { fetch: async () => { calls++; return Response.json([{ flavors: [{ model_id: MODELS.conductor, input_price_per_million_tokens: price, output_price_per_million_tokens: 0.3 }] }]); } };
    const result = await call('/api/plan', planBody, environment(), deps);
    assert.equal(result.status, 503); assert.equal(result.body.error, 'pricing_unavailable'); assert.equal(calls, 1);
  }
});
test('writer chooses Ultra for Korean and rejects budget overflow', async () => {
  const deps = mockFetch([{ content: '문이 열리면 이야기는 성수' }]);
  const result = await call('/api/write', { lang: 'ko', exit_station: '성수', budget_chars: 40, is_last_scene: true }, environment(), deps);
  assert.equal(result.status, 200); assert.equal(result.body.model, MODELS.ko); assert.equal(result.body.sentence_cap, 40);
  const tooLong = await call('/api/write', { lang: 'ko', exit_station: '성수', budget_chars: 40, is_last_scene: true }, environment(), mockFetch([{ content: '가'.repeat(41) + '성수' }]));
  assert.equal(tooLong.status, 502); assert.equal(tooLong.body.error, 'writer_constraint_failure'); assert.ok(tooLong.body.cost_usd > 0);
});
test('writer rejects missing station ending instead of silently repairing model output', async () => {
  const result = await call('/api/write', { lang: 'en', exit_station: 'Seongsu', budget_chars: 90, is_last_scene: true }, environment(), mockFetch([{ content: 'The train arrives.' }]));
  assert.equal(result.status, 502); assert.equal(result.body.error, 'writer_constraint_failure');
});
test('missing provider usage remains unknown rather than reporting zero cost', async () => {
  const result = await call('/api/write', { lang: 'en', exit_station: 'Seongsu', budget_chars: 90, is_last_scene: true }, environment(), mockFetch([{ content: 'The final clue is Seongsu' }], { missingUsage: true }));
  assert.equal(result.status, 200); assert.equal(result.body.cost_usd, null); assert.equal(result.body.usage, null);
});
test('failed provider response does not expose keys and preserves unknown usage/cost', async () => {
  const result = await call('/api/write', { lang: 'en', exit_station: 'Seongsu', budget_chars: 90, is_last_scene: true }, environment(), mockFetch([new Response('sensitive-provider-error', { status: 401 })]));
  assert.equal(result.status, 502); assert.equal(result.body.cost_usd, null); assert.equal(result.body.usage, null);
  assert.ok(!JSON.stringify(result.body).includes('sensitive-provider-error')); assert.ok(!JSON.stringify(result.body).includes('server-nebius-mock-key'));
});
test('Seoul quota prevents all upstream calls and forces replay at 950', async () => {
  const deps = mockFetch();
  const result = await call('/api/position?line=2%ED%98%B8%EC%84%A0', undefined, environment({ LIMITS: { getByName: () => ({ reserve: async () => ({ allowed: false }) }) } }), deps);
  assert.equal(result.status, 200); assert.equal(result.body.reason, 'daily_quota_950'); assert.equal(deps.seen.length, 0);
});
test('position retains API receipt timestamps and strips unknown fields', async () => {
  const result = await call('/api/position?line=2%ED%98%B8%EC%84%A0', undefined, environment(), mockFetch());
  assert.equal(result.status, 200); assert.equal(result.body.mode, 'live'); assert.equal(result.body.positions[0].recptnDt, '2026-10-30 10:15:00');
  assert.equal(result.body.positions[0].secret_field, undefined); assert.equal(result.body.arrival_reference, 'station-position-proxy-not-doors-open');
});
test('search gives a source URL, no fabricated dollar cost, and missing key uses station-only', async () => {
  const result = await call('/api/fact?station=Seongsu', undefined, environment(), mockFetch());
  assert.equal(result.status, 200); assert.equal(result.body.tavily_ok, true); assert.equal(result.body.fact.url, 'https://official.example/park'); assert.equal(result.body.cost_usd, null);
  const missing = await call('/api/fact?station=Seongsu', undefined, environment({ TAVILY_API_KEY: '' }));
  assert.equal(missing.body.fact, null); assert.equal(missing.body.tavily_ok, false);
});
test('search snippets fit the Writer fact schema after Unicode truncation and control-character cleanup', async () => {
  const result = await call('/api/fact?station=Seongsu', undefined, environment(), mockFetch([], { searchContent: 'A park\tbeside\n the station.\u0000 ' + '한'.repeat(300) }));
  assert.equal(result.status, 200); assert.equal(result.body.tavily_ok, true);
  assert.equal(Array.from(result.body.fact.text).length, 240);
  assert.doesNotMatch(result.body.fact.text, /[\u0000-\u001f\u007f]/u);
  assert.match(result.body.fact.text, /^A park beside the station\./u);
});
test('invalid schemas and oversized bodies are rejected without inference', async () => {
  const deps = mockFetch();
  const invalid = await call('/api/plan', { ...planBody, remaining_s: -1 }, environment(), deps);
  assert.equal(invalid.status, 400);
  const oversized = await call('/api/write', { scene: 'x'.repeat(25000) }, environment(), deps);
  assert.equal(oversized.status, 413); assert.equal(deps.seen.length, 0);
});
