import { LINE2, ETA_LINES, topologyFor, stationName, canonicalTerminus, directedPath, circularContinuation } from './topology.js';
export { LINE2, ETA_LINES } from './topology.js';
export const MAX_ANCHOR_AGE_S = 300;
const finiteDuration = n => typeof n === 'number' && Number.isFinite(n) && n >= 10 && n <= 600;
const nowMs = deps => deps.now ? deps.now() : Date.now();

export function arrivalTimestamp(value) {
  if (typeof value !== 'string') return null;
  const normalized = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}$/u.test(value) ? value.replace(' ', 'T') + '+09:00' : value;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/u.test(normalized)) return null;
  const timestamp = Date.parse(normalized);
  return Number.isFinite(timestamp) ? timestamp : null;
}

export function validateEtaBundle(bundle, line = bundle?.line || '2호선') {
  const model = bundle?.model, evaluation = bundle?.evaluation;
  if (bundle?.schema !== 'last-sentence/eta-bundle-v1' || !/^[a-f0-9]{64}$/u.test(bundle.trace_sha256 || '') || !arrivalTimestamp(bundle.prepared_at)) return { valid: false, reason: 'eta_bundle_provenance_invalid' };
  if (bundle.recording_complete !== true) return { valid: false, reason: 'recording_not_complete' };
  if (!ETA_LINES.includes(line) || (bundle.line && bundle.line !== line)) return {valid:false,reason:'eta_line_mismatch'};
  const topology=topologyFor(bundle,line);if(!topology.valid)return {valid:false,reason:topology.reason};
  if (model?.schema !== 'last-sentence/eta-v1' || model.source !== 'recorded-station-arrival-proxy' || !Number.isInteger(model.segment_observations) || model.segment_observations < 2 || !model.segments || Array.isArray(model.segments) || !model.line_medians_s || !finiteDuration(model.line_medians_s[line])) return { valid: false, reason: 'recorded_eta_model_unavailable' };
  if (evaluation?.method !== 'leave-one-train-identity-out' || evaluation.status !== 'measured' || evaluation.gate_lte_15_percent !== true || evaluation.arrival_event !== 'station-arrival-proxy' || !Number.isInteger(evaluation.n) || evaluation.n < 10 || !Number.isInteger(evaluation.train_identities) || evaluation.train_identities < 2 || typeof evaluation.median_relative_error !== 'number' || !Number.isFinite(evaluation.median_relative_error) || evaluation.median_relative_error < 0 || evaluation.median_relative_error > 0.15 || evaluation.station_horizons?.[0] !== 3 || evaluation.station_horizons?.[1] !== 10) return { valid: false, reason: 'eta_held_out_gate_not_met' };
  for (const [key, segment] of Object.entries(model.segments)) {
    const [segmentLine, from, to] = key.split('|');
    if (segmentLine !== line) continue;
    if (!topology.undirected.get(from)?.has(to) || !finiteDuration(segment?.median_s) || !Number.isInteger(segment.n) || segment.n < 2) return { valid: false, reason: 'eta_segment_invalid' };
  }
  return { valid: true, reason: null, line, trace_sha256: bundle.trace_sha256, prepared_at: bundle.prepared_at, recording_complete: bundle.recording_complete === true, evaluation: { n: evaluation.n, train_identities: evaluation.train_identities, median_relative_error: evaluation.median_relative_error, station_horizons: [3, 10], method: evaluation.method }, topology:{stations:topology.nodes.size,edges:topology.edge_count,direction_steps:topology.direction_steps}, experimental: true };
}

export async function loadEtaBundle(env, deps = {}, line = '2호선') {
  try {
    if(!ETA_LINES.includes(line))return {bundle:null,quality:{valid:false,reason:'unsupported_line'}};
    const supplied=deps.etaBundles?.[line] || (deps.etaBundle && (deps.etaBundle.line || '2호선')===line ? deps.etaBundle : null);
    if (supplied) { const quality = validateEtaBundle(supplied,line); return { bundle: quality.valid ? supplied : null, quality }; }
    if (!env.ASSETS) return { bundle: null, quality: { valid: false, reason: 'eta_assets_unavailable' } };
    const path=line==='2호선'?'eta-bundle.json':`eta-bundle-${line.replace('호선','')}.json`;
    const response = await env.ASSETS.fetch(new Request('https://last-sentence-assets.invalid/replay/'+path));
    if (!response.ok || Number(response.headers.get('content-length') || 0) > 512000) return { bundle: null, quality: { valid: false, reason: 'eta_asset_unavailable' } };
    const reader = response.body?.getReader(); if (!reader) throw Error('No bundle body');
    const chunks = []; let length = 0;
    try { for (;;) { const { done, value } = await reader.read(); if (done) break; length += value.length; if (length > 512000) { await reader.cancel(); throw Error('Bundle too large'); } chunks.push(value); } } finally { reader.releaseLock(); }
    const bytes = new Uint8Array(length); let offset = 0; for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    const bundle = JSON.parse(new TextDecoder().decode(bytes)); const quality = validateEtaBundle(bundle,line);
    return { bundle: quality.valid ? bundle : null, quality };
  } catch { return { bundle: null, quality: { valid: false, reason: 'eta_asset_invalid' } }; }
}

export function anchorCacheKey(line, trainNo, direction) {
  return new Request(`https://last-sentence-cache.invalid/arrival-v2/${encodeURIComponent(line)}/${encodeURIComponent(trainNo)}/${encodeURIComponent(direction)}`);
}

export function normalizeTerminus(name, id, line='2호선', bundle=null) {
  return canonicalTerminus(topologyFor(bundle,line),name,id);
}

export function verifiedArrival(position, line, transport, deps = {}) {
  const timestamp = arrivalTimestamp(position?.recptnDt), age = timestamp === null ? Infinity : (nowMs(deps) - timestamp) / 1000;
  const topology=topologyFor(deps.etaBundle,line);
  const station = stationName(topology,position?.statnNm) || canonicalTerminus(topology,position?.statnNm,position?.statnId)?.station;
  if (!topology.valid || String(position?.trainSttus) !== '1' || !station || !['0', '1'].includes(String(position?.updnLine)) || typeof position?.trainNo !== 'string' || !/^\d{1,8}$/u.test(position.trainNo) || age < -5 || age > MAX_ANCHOR_AGE_S) return null;
  const row=topology.stations[station],stationID=position.statnId==null?'':String(position.statnId);
  if(![...(row.observed_api_station_ids||[]),...(row.observed_api_terminal_ids||[])].includes(stationID))return null;
  return { station, station_id:stationID, raw_station: position.statnNm, recptnDt: position.recptnDt, epoch_s: timestamp / 1000, trainSttus: '1', trainNo: position.trainNo, direction: String(position.updnLine), line, verified: true, terminus: canonicalTerminus(topology,position.statnTnm,position.statnTid), directAt: position.directAt ?? null, lstcarAt: position.lstcarAt ?? null, transport, cached_at: new Date(nowMs(deps)).toISOString() };
}

export function estimateEta(bundle, anchor, to, deps = {}) {
  const line=anchor?.line || bundle?.line || '2호선',quality = validateEtaBundle(bundle,line);
  const unavailable = reason => ({ mode: 'eta-unavailable', eta_available: false, reason, experimental: true });
  if (!quality.valid) return unavailable(quality.reason);
  const topology=topologyFor(bundle,line);
  if (!ETA_LINES.includes(anchor?.line)) return unavailable('unsupported_line');
  if (!topology.nodes.has(anchor.station) || !['0', '1'].includes(String(anchor.direction)) || anchor.trainSttus !== '1') return unavailable('invalid_arrival_anchor');
  const observed = arrivalTimestamp(anchor.recptnDt), now = nowMs(deps), age = observed === null ? Infinity : (now - observed) / 1000;
  if (age < -5 || age > MAX_ANCHOR_AGE_S) return unavailable('stale_arrival_anchor');
  const terminus = anchor.terminus && canonicalTerminus(topology,anchor.terminus.raw_name || anchor.terminus.station, anchor.terminus.id);
  if (anchor.verified && !terminus) return { ...unavailable('verified_terminus_unavailable'), anchor };
  let forward=terminus?directedPath(topology,anchor.station,terminus.station,anchor.direction):circularContinuation(topology,anchor.station,anchor.direction);
  if(!forward&&!anchor.verified&&to)forward=directedPath(topology,anchor.station,stationName(topology,to),anchor.direction);
  if(!forward)return {...unavailable(terminus?'terminus_direction_mismatch':'operator_terminus_required'),anchor};
  const terminusDistance = terminus ? forward.length-1 : null;
  const exits = forward.slice(1,11).map((station,i)=>({station,stations_left:i+1,within_evaluated_horizon:i+1>=3,horizon_supported:i+1>=3}));
  const base = { mode: 'experimental-eta', eta_source: anchor.verified ? 'recorded-model' : 'operator-estimate', anchor, terminus, stations_to_terminus: terminusDistance, anchor_age_s: Math.max(0, age), generated_at: new Date(now).toISOString(), valid_until: new Date(observed + MAX_ANCHOR_AGE_S * 1000).toISOString(), eligible_exits: exits, arrival_event: 'station-arrival-proxy', evaluation: quality.evaluation, model_prepared_at: quality.prepared_at, trace_sha256: quality.trace_sha256, recording_complete: quality.recording_complete, experimental: true, uncertainty: { poll_interval_s: 20, anchor_timestamp: 'provider-final-receipt-time-for-arrival-status', terminus: terminus ? 'verified-provider-terminus' : 'unverified-operator-route', provider_lag_s: null, door_open_offset_s: null }, notice: 'Experimental receipt-time proxy estimate. Median-error validation is not a confidence interval or a guarantee of narration landing accuracy.' };
  if (!to) return { ...base, eta_available: false, reason: 'choose_exit' };
  to=stationName(topology,to);if(!to)return {...base,...unavailable('unknown_exit_station')};
  if (to === anchor.station) return { ...base, eta_available: true, remaining_s: 0, stations_left: 0, route: [anchor.station], fallback_segments: [], within_evaluated_horizon: false, arrived: true };
  const exit = exits.find(v => v.station === to);
  if (!exit) {
    const path=directedPath(topology,anchor.station,to,anchor.direction);
    return { ...base, ...unavailable(!path?'route_direction_mismatch':terminusDistance!==null&&!forward.includes(to)?'route_exceeds_train_terminus':'route_exceeds_10_stations') };
  }
  const route = forward.slice(0,exit.stations_left+1);
  const fallback = []; let travel = 0;
  for (let i = 0; i < route.length - 1; i++) {
    const segment = bundle.model.segments[`${line}|${route[i]}|${route[i + 1]}`];
    if (segment) travel += segment.median_s;
    else { travel += bundle.model.line_medians_s[line]; fallback.push([route[i], route[i + 1]]); }
  }
  return { ...base, eta_available: true, remaining_s: Math.max(0, travel - Math.max(0, age)), stations_left: exit.stations_left, route, fallback_segments: fallback, within_evaluated_horizon: exit.within_evaluated_horizon, arrived: false };
}

export async function etaFromQuery(params, env, deps = {}) {
  const line=params.get('line')||'2호선';const { bundle, quality } = await loadEtaBundle(env, deps,line);
  if (!bundle) return { mode: 'eta-unavailable', eta_available: false, reason: quality.reason, experimental: true };
  const trainNo = params.get('trainNo'), direction = params.get('direction'), to = params.get('to') || params.get('exit');
  if (!ETA_LINES.includes(line)) return { mode: 'eta-unavailable', eta_available: false, reason: 'unsupported_line', experimental: true };
  if (!['0', '1'].includes(direction)) return { mode: 'eta-unavailable', eta_available: false, reason: 'direction_required', experimental: true };
  if (trainNo) {
    if (!/^\d{1,8}$/u.test(trainNo) || !deps.cache) return { mode: 'eta-unavailable', eta_available: false, reason: 'verified_arrival_anchor_unavailable', experimental: true };
    const cached = await deps.cache.match(anchorCacheKey(line, trainNo, direction));
    if (!cached) return { mode: 'eta-unavailable', eta_available: false, reason: 'verified_arrival_anchor_unavailable', experimental: true };
    const anchor = await cached.json();
    if (anchor.verified !== true || anchor.trainNo !== trainNo || anchor.direction !== direction || anchor.line !== line) return { mode: 'eta-unavailable', eta_available: false, reason: 'invalid_arrival_anchor', experimental: true };
    return estimateEta(bundle, anchor, to, deps);
  }
  const anchor = { line, station: params.get('from'), recptnDt: params.get('observed_at'), direction, trainSttus: params.get('train_status') || '1', verified: false };
  return estimateEta(bundle, anchor, to, deps);
}
