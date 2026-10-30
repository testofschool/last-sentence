import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const require = createRequire(new URL('../worker/package.json', import.meta.url));
let Miniflare, convertV4MiniflareOptions;
try { ({ Miniflare, convertV4MiniflareOptions } = require('miniflare')); } catch { /* npm ci --prefix worker enables the runtime integration test. */ }

test('actual Durable Object serializes concurrent Seoul, search and cost reservations', { skip: !Miniflare && 'Run npm ci --prefix worker for the local workerd integration test' }, async () => {
  const source = await readFile(new URL('../worker/src/limits.js', import.meta.url), 'utf8');
  const config = await readFile(new URL('../worker/src/limits_config.js', import.meta.url), 'utf8');
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules: true, compatibilityDate: '2026-10-30',
    script: config.replaceAll('export function', 'function') + '\n' + source.replace("import { completionCap, budgetCeilingMicrousd } from './limits_config.js';", '') + `\nexport default { async fetch(request,env) { const p = new URL(request.url).searchParams; const stub = env.LIMITS.getByName('test'); const result = p.has('inspect') ? await stub.inspect() : await stub.reserve(p.get('kind'), Number(p.get('amount')), Number(p.get('ceiling'))); return Response.json(result); } };`,
    durableObjects: { LIMITS: { className: 'UsageLimits', useSQLite: true } },
    bindings: { LIVE_MAX_COMPLETIONS: '3' },
  }));
  try {
    const results = await Promise.all(Array.from({ length: 1000 }, async () => (await mf.dispatchFetch('http://localhost/?kind=seoul&amount=1&ceiling=950')).json()));
    assert.equal(results.filter(v => v.allowed).length, 950);
    assert.equal(Math.max(...results.map(v => v.used)), 950);
    const completions = await Promise.all(Array.from({ length: 5 }, async () => (await mf.dispatchFetch('http://localhost/?kind=completion&amount=10&ceiling=100')).json()));
    assert.equal(completions.filter(v => v.allowed).length, 3);
    assert.equal(Math.max(...completions.map(v => v.used)), 30);
    const inspected = await (await mf.dispatchFetch('http://localhost/?inspect')).json();
    assert.equal(inspected.completion_calls_used, 3);
    assert.equal(inspected.completion_calls_remaining, 0);
    assert.equal(inspected.reserved_usd, 0.00003);
    const searches = await Promise.all(Array.from({ length: 101 }, async () => (await mf.dispatchFetch('http://localhost/?kind=search&amount=1&ceiling=100')).json()));
    assert.equal(searches.filter(v => v.allowed).length, 100);
  } finally { await mf.dispose(); }
});

test('the actual Worker entrypoint calls native fetch with its required global receiver', { skip: !Miniflare && 'Run npm ci --prefix worker for the local workerd integration test' }, async () => {
  const { build } = require('esbuild');
  const { fileURLToPath } = await import('node:url');
  const built = await build({ entryPoints: [fileURLToPath(new URL('../worker/src/index.js', import.meta.url))], bundle: true, write: false, format: 'esm', platform: 'browser', external: ['cloudflare:workers', 'node:crypto'] });
  const etaFixture = { schema: 'last-sentence/eta-bundle-v1', trace_sha256: 'b'.repeat(64), prepared_at: new Date().toISOString(), recording_complete: true, model: { schema: 'last-sentence/eta-v1', source: 'recorded-station-arrival-proxy', segments: {}, line_medians_s: { '2호선': 120 }, segment_observations: 20 }, evaluation: { method: 'leave-one-train-identity-out', status: 'measured', gate_lte_15_percent: true, arrival_event: 'station-arrival-proxy', n: 20, train_identities: 3, median_relative_error: 0.1, station_horizons: [3, 10] } };
  let outbound = 0;
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules: true, compatibilityDate: '2026-10-30', compatibilityFlags: ['nodejs_compat'], script: built.outputFiles[0].text,
    durableObjects: { LIMITS: { className: 'UsageLimits', useSQLite: true } },
    bindings: { ENABLE_LIVE: 'true', LIVE_ACCESS_TOKEN: 'mock-local-session', SEOUL_RT_KEY: 'SAMPLE', LIVE_MAX_COMPLETIONS: '300', LIVE_BUDGET_USD: '3' },
    serviceBindings: { ASSETS: async () => Response.json(etaFixture) },
    outboundService: async request => {
      outbound++; assert.equal(new URL(request.url).hostname, 'swopenapi.seoul.go.kr'); assert.match(request.url, /\/sample\//u);
      return Response.json({ errorMessage: { code: 'INFO-000' }, realtimePositionList: [{ trainNo: '1234', statnNm: '시청',statnId:'1002000201',updnLine: '0', trainSttus: '1', recptnDt: new Date().toISOString(), statnTnm: '성수종착', statnTid: '1002000211' }] });
    },
  }));
  try {
    const headers = { authorization: 'Bearer mock-local-session' };
    const response = await mf.dispatchFetch('http://localhost/api/position?line=2%ED%98%B8%EC%84%A0', { headers });
    assert.equal(response.status, 200); const data = await response.json(); assert.equal(data.mode, 'live'); assert.equal(data.transport, 'https'); assert.equal(data.positions[0].statnTnm, '성수종착');
    assert.equal(outbound, 1);
    const status = await (await mf.dispatchFetch('http://localhost/api/status', { headers })).json();
    assert.equal(status.limits.seoul_calls_used_today, 1); assert.equal(status.limits.completion_calls_used, 0); assert.equal(status.inference_enabled, false);
    const eta = await (await mf.dispatchFetch('http://localhost/api/eta?line=2%ED%98%B8%EC%84%A0&trainNo=1234&direction=0&to=%EC%9D%84%EC%A7%80%EB%A1%9C4%EA%B0%80')).json();
    assert.equal(eta.eta_available, true); assert.equal(eta.anchor.verified, true); assert.equal(eta.anchor.terminus.station, '성수'); assert.equal(eta.stations_left, 3); assert.ok(eta.remaining_s <= 360 && eta.remaining_s > 350); assert.equal(outbound, 1);
  } finally { await mf.dispose(); }
});

test('actual workerd supports fresh acknowledged-price checks and blocks drift before a completion', {skip:!Miniflare&&'Run npm ci --prefix worker for the local workerd integration test'},async()=>{
  const {build}=require('esbuild');const {fileURLToPath}=await import('node:url');
  const built=await build({entryPoints:[fileURLToPath(new URL('../worker/src/index.js',import.meta.url))],bundle:true,write:false,format:'esm',platform:'browser',external:['cloudflare:workers','node:crypto']});
  let catalogs=0,completions=0;
  const mf=new Miniflare(convertV4MiniflareOptions({modules:true,compatibilityDate:'2026-10-30',compatibilityFlags:['nodejs_compat'],script:built.outputFiles[0].text,
    durableObjects:{LIMITS:{className:'UsageLimits',useSQLite:true}},bindings:{ENABLE_LIVE:'true',LIVE_ACCESS_TOKEN:'mock-session',NEBIUS_API_KEY:'mock-key-no-external-network'},
    outboundService:async request=>{
      if(request.url==='https://tokenfactory.nebius.com/api/public/models_info'){
        catalogs++;assert.equal(request.headers.get('cache-control'),'no-cache');
        return Response.json([{model_id:'nvidia/nemotron-3-super-120b-a12b',input_price_per_million_tokens:.2,output_price_per_million_tokens:.3}]);
      }
      completions++;throw Error('No provider completion may be dispatched');
    }}));
  try{
    const headers={authorization:'Bearer mock-session','content-type':'application/json'};
    const response=await mf.dispatchFetch('http://localhost/api/write',{method:'POST',headers,body:JSON.stringify({lang:'en',exit_station:'성수',budget_chars:100,is_last_scene:true,expected_pricing:{model:'nvidia/nemotron-3-super-120b-a12b',input_price_per_million_tokens:.1,output_price_per_million_tokens:.3}})});
    const result=await response.json();assert.equal(response.status,409);assert.equal(result.error,'pricing_changed');assert.equal(catalogs,1);assert.equal(completions,0);
    const status=await(await mf.dispatchFetch('http://localhost/api/status',{headers})).json();assert.equal(status.limits.completion_calls_used,0);assert.equal(status.limits.reserved_usd,0);assert.equal(status.expected_pricing_supported,true);
  }finally{await mf.dispose();}
});
