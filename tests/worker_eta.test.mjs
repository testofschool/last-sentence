import test from 'node:test';
import assert from 'node:assert/strict';
import { handleRequest, MODELS, budget } from '../worker/src/core.js';
import { validateEtaBundle, estimateEta, verifiedArrival, anchorCacheKey, etaFromQuery } from '../worker/src/eta.js';

const NOW = Date.parse('2026-10-30T01:20:00Z');
const bundle = () => ({ schema: 'last-sentence/eta-bundle-v1', trace_sha256: 'a'.repeat(64), prepared_at: '2026-10-30T01:19:00Z', recording_complete: true, model: { schema: 'last-sentence/eta-v1', source: 'recorded-station-arrival-proxy', segments: { '2호선|시청|을지로입구': { median_s: 100, n: 2 } }, line_medians_s: { '2호선': 120 }, segment_observations: 20 }, evaluation: { method: 'leave-one-train-identity-out', status: 'measured', gate_lte_15_percent: true, arrival_event: 'station-arrival-proxy', n: 20, train_identities: 3, median_relative_error: 0.1, station_horizons: [3, 10] } });
const anchor = () => ({ line: '2호선', station: '시청', recptnDt: '2026-10-30 10:19:20', epoch_s: (NOW - 40000) / 1000, trainSttus: '1', trainNo: '1234', direction: '0', verified: true, terminus: { station: '신도림', raw_name: '신도림', id: '1002000234' } });
function cache() {
  const entries = new Map();
  return { match: async request => entries.get(request.url)?.clone(), put: async (request, response) => entries.set(request.url, response.clone()), entries };
}
function env(overrides = {}) { return { ENABLE_LIVE: 'true', LIVE_ACCESS_TOKEN: 'eta-test-session-token', NEBIUS_API_KEY: 'mock-provider-key', SEOUL_RT_KEY: 'SAMPLE', LIMITS: { getByName: () => ({ reserve: async () => ({ allowed: true }), inspect: async () => ({ completion_cap: 300, completion_calls_remaining: 300, completion_calls_used: 0, reserved_usd: 0, reservation_budget_usd: 3 }) }) }, ...overrides }; }
function request(path, body) { return new Request('https://test.example' + path, { method: body ? 'POST' : 'GET', headers: { authorization: 'Bearer eta-test-session-token', ...(body ? { 'content-type': 'application/json' } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) }); }
const neverFetch = async () => { throw Error('No vendor call is allowed'); };

test('ETA readiness requires a completed provenance-bound recording and a real held-out gate', () => {
  assert.equal(validateEtaBundle(bundle()).valid, true);
  for (const change of [b => b.recording_complete = false, b => b.model.source = 'synthetic', b => b.evaluation.n = 0, b => b.evaluation.train_identities = 1, b => b.evaluation.median_relative_error = 0.16, b => b.trace_sha256 = 'unknown']) {
    const value = bundle(); change(value); assert.equal(validateEtaBundle(value).valid, false);
  }
});
test('ETA uses ordered loop topology, measured segments, disclosed line fallback and elapsed receipt time', () => {
  const forward = estimateEta(bundle(), anchor(), '을지로4가', { now: () => NOW });
  assert.equal(forward.remaining_s, 300); assert.equal(forward.stations_left, 3);
  assert.deepEqual(forward.route, ['시청', '을지로입구', '을지로3가', '을지로4가']);
  assert.equal(forward.fallback_segments.length, 2);
  assert.equal(forward.uncertainty.anchor_timestamp, 'provider-final-receipt-time-for-arrival-status');
  const reverse = estimateEta(bundle(), { ...anchor(), direction: '1' }, '이대', { now: () => NOW });
  assert.deepEqual(reverse.route, ['시청', '충정로', '아현', '이대']); assert.equal(reverse.remaining_s, 320);
  const wrap = estimateEta(bundle(), { ...anchor(), station: '충정로' }, '을지로3가', { now: () => NOW });
  assert.deepEqual(wrap.route, ['충정로', '시청', '을지로입구', '을지로3가']);
});
test('unknown topology, unsupported line, stale/future or non-arrival anchors never get uniform guesses', () => {
  for (const value of [{ ...anchor(), station: '성수종착' }, { ...anchor(), line: '5호선' }, { ...anchor(), trainSttus: '2' }, { ...anchor(), recptnDt: '2026-10-30 10:00:00' }, { ...anchor(), recptnDt: '2026-10-30 10:21:00' }, { ...anchor(), recptnDt: null }]) assert.equal(estimateEta(bundle(), value, '을지로4가', { now: () => NOW }).eta_available, false);
  assert.equal(estimateEta(bundle(), anchor(), '건대입구', { now: () => NOW }).reason, 'route_exceeds_10_stations');
  assert.equal(estimateEta(bundle(), anchor(), '알수없는역', { now: () => NOW }).eta_available, false);
});
test('verified anchor lookup is read-only and exit chooser exposes only known ordered candidates', async () => {
  const store = cache(); await store.put(anchorCacheKey('2호선', '1234', '0'), Response.json(anchor()));
  const deps = { etaBundle: bundle(), cache: store, now: () => NOW, fetch: neverFetch };
  const choose = await etaFromQuery(new URLSearchParams({ line: '2호선', trainNo: '1234', direction: '0' }), {}, deps);
  assert.equal(choose.reason, 'choose_exit'); assert.equal(choose.anchor.verified, true); assert.equal(choose.eligible_exits.length, 10);
  assert.equal(choose.eligible_exits.filter(v => v.horizon_supported).length, 8);
  const missing = await etaFromQuery(new URLSearchParams({ line: '2호선', trainNo: '9999', direction: '0', to: '을지로4가' }), {}, deps);
  assert.equal(missing.eta_available, false); assert.equal(missing.reason, 'verified_arrival_anchor_unavailable');
});
test('manual ETA is explicitly unverified operator input and current-station arrival is zero', async () => {
  const params = new URLSearchParams({ line: '2호선', from: '시청', to: '을지로4가', direction: '0', observed_at: anchor().recptnDt });
  const value = await etaFromQuery(params, {}, { etaBundle: bundle(), now: () => NOW });
  assert.equal(value.eta_source, 'operator-estimate'); assert.equal(value.anchor.verified, false);
  const arrival = estimateEta(bundle(), anchor(), '시청', { now: () => NOW });
  assert.equal(arrival.arrived, true); assert.equal(arrival.remaining_s, 0);
});
test('status derives ETA readiness from the asset without enabling inference or vendor calls', async () => {
  const assetEnv = { ASSETS: { fetch: async () => Response.json(bundle()) } };
  const response = await handleRequest(new Request('https://test.example/api/status'), assetEnv, { fetch: neverFetch });
  const data = await response.json(); assert.equal(data.eta_model_configured, true); assert.equal(data.inference_enabled, false); assert.equal(data.eta_model.experimental, true);
});
test('public sample HTTPS fallback reserves both attempts and never transmits a private key over HTTP', async () => {
  const seen = [], reserved = [];
  const store = cache();
  const deps = { etaBundle: bundle(), cache: store, now: () => NOW, fetch: async url => {
    seen.push(url); if (url.startsWith('https:')) throw Error('Mock HTTPS unavailable');
    return Response.json({ errorMessage: { code: 'INFO-000' }, realtimePositionList: [{ trainNo: '1234', statnNm: '시청', statnId:'1002000201',recptnDt: anchor().recptnDt, trainSttus: '1', updnLine: '0', statnTnm: '성수종착', statnTid: '1002000211', directAt: '0', lstcarAt: '0' }] });
  } };
  const sampleEnv = env({ LIMITS: { getByName: () => ({ reserve: async (kind, amount, ceiling) => { reserved.push({ kind, amount, ceiling }); return { allowed: true }; } }) } });
  const response = await handleRequest(request('/api/position?line=2%ED%98%B8%EC%84%A0'), sampleEnv, deps);
  const value = await response.json(); assert.equal(value.transport, 'http-public-sample'); assert.equal(value.transport_fallback, true); assert.equal(reserved.length, 2);
  assert.equal(value.positions[0].statnTnm, '성수종착'); assert.equal(value.positions[0].statnTid, '1002000211'); assert.equal(value.positions[0].directAt, '0');
  assert.ok(await store.match(anchorCacheKey('2호선', '1234', '0')));
  const privateSeen = [];
  const failed = await handleRequest(request('/api/position?line=2%ED%98%B8%EC%84%A0'), env({ SEOUL_RT_KEY: 'private-test-key' }), { fetch: async url => { privateSeen.push(url); throw Error('Mock transport failure'); } });
  assert.equal(failed.status, 502); assert.equal(privateSeen.length, 1); assert.ok(privateSeen[0].startsWith('https:'));
});
test('departed observations retain the last verified arrival until freshness expires', async () => {
  const store = cache(); await store.put(anchorCacheKey('2호선', '1234', '0'), Response.json(anchor()));
  const departure = verifiedArrival({ trainNo: '1234', statnNm: '시청', recptnDt: '2026-10-30 10:20:00', trainSttus: '2', updnLine: '0' }, '2호선', 'https', { now: () => NOW });
  assert.equal(departure, null);
  const params = new URLSearchParams({ line: '2호선', trainNo: '1234', direction: '0', to: '을지로4가' });
  const live = await etaFromQuery(params, {}, { etaBundle: bundle(), cache: store, now: () => NOW }); assert.equal(live.eta_available, true);
  const stale = await etaFromQuery(params, {}, { etaBundle: bundle(), cache: store, now: () => NOW + 301000 }); assert.equal(stale.eta_available, false); assert.equal(stale.reason, 'stale_arrival_anchor');
});
test('Conductor executes ETA tool against verified server estimates and ignores client timing', async () => {
  const store = cache(); await store.put(anchorCacheKey('2호선', '1234', '0'), Response.json(anchor()));
  const bodies = []; let completions = 0;
  const deps = { etaBundle: bundle(), cache: store, now: () => NOW, fetch: async (url, init) => {
    if (url.endsWith('/models_info')) return Response.json([{ flavors: [{ model_id: MODELS.conductor, input_price_per_million_tokens: 0.06, output_price_per_million_tokens: 0.24 }] }]);
    assert.ok(url.endsWith('/chat/completions')); const body = JSON.parse(init.body); bodies.push(body); completions++;
    const message = completions === 1 ? { role: 'assistant', tool_calls: ['eta_to_station', 'budget', 'scene_ops'].map((name, i) => ({ id: String(i), type: 'function', function: { name, arguments: name === 'scene_ops' ? '{"ops":[]}' : '{}' } })) } : { content: '{"ops":[],"log":"Use the verified observed estimate."}' };
    return Response.json({ choices: [{ message }], usage: { prompt_tokens: 100, completion_tokens: 20 } });
  } };
  const response = await handleRequest(request('/api/plan', { current_station: 'fake', exit_station: 'fake', stations_left: 60, remaining_s: 999, eta_source: 'recorded-model', remaining_scenes: [], train_anchor: { line: '2호선', trainNo: '1234', direction: '0', to: '을지로4가' } }), env(), deps);
  const value = await response.json(); assert.equal(response.status, 200); assert.equal(value.plan.remaining_s, 300); assert.equal(value.plan.stations_left, 3); assert.equal(value.plan.budget_chars, budget(300));
  const tool = value.tool_executions.find(v => v.tool === 'eta_to_station'); assert.equal(tool.result.anchor.verified, true); assert.equal(tool.result.remaining_s, 300); assert.equal(value.eta.eta_source, 'recorded-model');
  assert.equal(bodies[1].messages.filter(v => v.role === 'tool').length, 3);
});
test('a client cannot label arbitrary timing as a recorded-model forecast', async () => {
  const response = await handleRequest(request('/api/plan', { current_station: '시청', exit_station: '을지로4가', stations_left: 3, remaining_s: 300, eta_source: 'recorded-model', remaining_scenes: [] }), env(), { fetch: neverFetch });
  assert.equal(response.status, 400); assert.equal((await response.json()).error, 'train_anchor_required');
});
test('an observed target arrival prevents a late paid Conductor call', async () => {
  const store = cache(); await store.put(anchorCacheKey('2호선', '1234', '0'), Response.json(anchor()));
  const response = await handleRequest(request('/api/plan', { remaining_scenes: [], train_anchor: { line: '2호선', trainNo: '1234', direction: '0', to: '시청' } }), env(), { etaBundle: bundle(), cache: store, now: () => NOW, fetch: neverFetch });
  assert.equal(response.status, 400); assert.equal((await response.json()).error, 'eta_window_exhausted');
});
test('verified forecasts stop at a short-turn terminus and never assume a full circular trip', () => {
  const short = { ...anchor(), station: '구로디지털단지', terminus: { station: '신도림', raw_name: '신도림', id: '1002000234' } };
  const choose = estimateEta(bundle(), short, null, { now: () => NOW });
  assert.deepEqual(choose.eligible_exits.map(v => v.station), ['대림', '신도림']); assert.equal(choose.stations_to_terminus, 2);
  assert.equal(estimateEta(bundle(), short, '문래', { now: () => NOW }).reason, 'route_exceeds_train_terminus');
  const terminal = estimateEta(bundle(), { ...short, station: '신도림' }, null, { now: () => NOW }); assert.deepEqual(terminal.eligible_exits, []);
  for (const terminus of [null, { station: '신설동', raw_name: '신설동', id: '1002000250' }, { station: '성수', raw_name: '성수종착', id: '1002000234' }]) assert.equal(estimateEta(bundle(), { ...anchor(), terminus }, '을지로4가', { now: () => NOW }).reason, 'verified_terminus_unavailable');
});
test('an arrival with a terminal suffix is canonicalized only when its station ID agrees', () => {
  const raw = { trainNo: '1234', statnNm: '성수종착', statnId: '1002000211', recptnDt: anchor().recptnDt, trainSttus: '1', updnLine: '0', statnTnm: '성수종착', statnTid: '1002000211' };
  const verified = verifiedArrival(raw, '2호선', 'https', { now: () => NOW }); assert.equal(verified.station, '성수'); assert.equal(verified.terminus.station, '성수');
  assert.equal(verifiedArrival({ ...raw, statnId: '1002000234' }, '2호선', 'https', { now: () => NOW }), null);
});
test('a known arrival name still requires its exact canonical realtime station ID',()=>{
  const raw={trainNo:'1234',statnNm:'시청',statnId:'1002000201',recptnDt:anchor().recptnDt,trainSttus:'1',updnLine:'0',statnTnm:'성수종착',statnTid:'1002000211'};
  assert.equal(verifiedArrival(raw,'2호선','https',{now:()=>NOW}).station_id,'1002000201');
  for(const statnId of [undefined,null,'','1002000211','1005000201','0201'])assert.equal(verifiedArrival({...raw,statnId},'2호선','https',{now:()=>NOW}),null);
});
