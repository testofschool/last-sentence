import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

// Execute the real application functions against a tiny DOM adapter. All fetches
// are supplied here; no endpoint, provider credential, or actual inference is used.
const source = (await readFile(new URL('../web/app.js', import.meta.url), 'utf8')).replace(/^export /gmu, '');
class Element {
  constructor() { this.children = []; this.value = ''; this.textContent = ''; this.dataset = {}; this.hidden = false; this.disabled = false; this.style = { setProperty() {} }; this.listeners = new Map(); this.selected = new Map(); this.classList = { add() {}, remove() {}, toggle() {} }; }
  setAttribute() {}
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  querySelector(key) { if (!this.selected.has(key)) this.selected.set(key, new Element()); return this.selected.get(key); }
  querySelectorAll(key) { if (key !== 'button') return []; if (!this.buttons) this.buttons = [1, 4, 16].map(speed => { const e = new Element(); e.dataset.speed = String(speed); return e; }); return this.buttons; }
  addEventListener(event, callback) { this.listeners.set(event, callback); }
  close() {}
  showModal() {}
}
function setup(fetch) {
  const ids = new Map(), selectors = new Map(), documentListeners = new Map(), windowListeners = new Map();
  const node = key => { if (!ids.has(key)) ids.set(key, new Element()); return ids.get(key); };
  const document = {
    hidden: false, documentElement: new Element(),
    getElementById: node, createElement: () => new Element(), createTextNode: text => ({ textContent: text }),
    querySelector: key => { if (!selectors.has(key)) selectors.set(key, new Element()); return selectors.get(key); },
    querySelectorAll: () => [], addEventListener: (name, callback) => documentListeners.set(name, callback),
  };
  const spoken=[],cancels=[];class Utterance{constructor(text){this.text=text;}}
  const window = { SpeechSynthesisUtterance:Utterance,speechSynthesis: { cancel() {cancels.push(true);}, getVoices: () => [{lang:'en-US'}],speak(utterance){spoken.push(utterance);} }, addEventListener: (name, callback) => windowListeners.set(name, callback) };
  const context = vm.createContext({ fetch, Response, URL, AbortController, DOMException, performance, setTimeout, clearTimeout, requestAnimationFrame: () => 1, cancelAnimationFrame() {},SpeechSynthesisUtterance:Utterance, window, navigator: {} });
  // There is no document during evaluation, so normal application boot does not run.
  vm.runInContext(source, context, { filename: 'web/app.js' });
  context.document = document;
  const state = vm.runInContext('state', context);
  Object.assign(state, { journey: { line: '2호선', trainNo: 'mock' }, stations: [{ name: 'Start', offset_s: 0 }, { name: 'Middle', offset_s: 200 }, { name: 'Seongsu', offset_s: 400 }], lines: ['A remembered clue.', 'The remaining bridge.', 'The final stop is Seongsu'], apiBase: 'https://old.example', apiToken: 'mock-session', elapsed: 100, sentenceIndex: 0, stationIndex: 0 });
  state.schedule = context.makeSchedule(state.lines, 400);
  return { context, state, node, document, documentListeners, windowListeners,spoken,cancels };
}
const usage = { prompt_tokens: 100, completion_tokens: 20, total_tokens: 120 };
const status = (remaining = 20) => ({ inference_enabled: true, tavily_enabled: false, limits: { completion_calls_remaining: remaining, reservation_budget_usd: 3, reserved_usd: 0 } });
const plan = () => ({ model: 'nvidia/Nemotron-3_5-Lightning', usage, cost_usd: 0.0001, latency_ms: 30, plan: { budget_chars: 180, ops: [{ scene: 'remaining-story', op: 'compress', reason: 'Fit the remaining time.' }], log: 'Compress the remaining story.' } });
const story = () => ({ model: 'nvidia/nemotron-3-super-120b-a12b', usage, cost_usd: 0.0002, latency_ms: 40, sentences: ['The old clue opens a new door.', 'The final clue is Seongsu'] });
const response = (value, status = 200) => Response.json(value, { status });
const nextTurn = () => new Promise(resolve => setImmediate(resolve));

test('connected mode remains explicit and an incomplete cycle budget makes zero billable requests', async () => {
  const paths = [];
  const app = setup(async url => { paths.push(new URL(url).pathname); return response(status(3)); });
  assert.equal(paths.length, 0);
  await app.context.startConnected();
  assert.deepEqual(paths, ['/api/status']);
  assert.equal(app.state.modelRun, false);
  assert.match(app.node('notice').textContent, /four completion attempts/u);
});
test('rejected Writer response retains paid usage and cost without replacing the story', async () => {
  const app = setup(async url => {
    const path = new URL(url).pathname;
    if (path === '/api/status') return response(status());
    if (path === '/api/plan') return response(plan());
    if (path === '/api/write') return response({ model: 'nvidia/nemotron-3-super-120b-a12b', usage, cost_usd: 0.00025, latency_ms: 50, error: 'writer_constraint_failure' }, 502);
    throw Error('Unexpected mock route');
  });
  const before = [...app.state.lines];
  await app.context.startConnected();
  assert.equal(app.state.generated, false); assert.deepEqual([...app.state.lines], before);
  assert.ok(app.state.receipts.some(r => r.cost === 0.00025 && r.usage.total_tokens === 120));
  assert.equal(app.state.modelRun, false);
});
test('changing service invalidates a late plan, retains its cost and cannot call the new Writer', async () => {
  let release; const paths = [];
  const app = setup(async url => {
    paths.push(url);
    if (new URL(url).pathname === '/api/plan') return new Promise(resolve => { release = resolve; });
    throw Error('A stale plan must never trigger a Writer request');
  });
  app.state.modelRun = true; app.state.modelController = new AbortController();
  const pending = app.context.replanConnected(true);
  await nextTurn();
  app.node('api-url').value = 'https://new.example'; app.node('api-token').value = 'new-session';
  app.context.setConnection({ preventDefault() {} });
  release(response(plan())); await pending;
  assert.equal(paths.length, 1); assert.equal(app.state.apiBase, 'https://new.example'); assert.equal(app.state.modelRun, false); assert.equal(app.state.generated, false);
  assert.ok(app.state.receipts.some(r => r.cost === 0.0001));
});
test('network replanning keeps the known replay clock moving and carries actual story context', async () => {
  let release, writeInput;
  const app = setup(async (url, init) => {
    if (new URL(url).pathname === '/api/plan') return new Promise(resolve => { release = resolve; });
    if (new URL(url).pathname === '/api/write') { writeInput = JSON.parse(init.body); return response(story()); }
    throw Error('Unexpected mock route');
  });
  app.state.modelRun = true; app.state.playing = true; app.state.modelController = new AbortController();
  const pending = app.context.replanConnected(false); await nextTurn();
  assert.equal(app.state.playing, true); const elapsed = app.state.elapsed;
  app.context.tick(performance.now() + 60000); assert.ok(app.state.elapsed > elapsed); const advancedElapsed = app.state.elapsed;
  release(response(plan())); await pending;
  assert.equal(app.state.generated, true); assert.equal(app.state.playing, true);
  assert.match(writeInput.scene, /A remembered clue/u); assert.match(writeInput.scene, /compress:remaining-story/u);
  assert.ok(Array.from(writeInput.scene).length <= 500); assert.equal(app.state.elapsed, advancedElapsed);
  assert.ok(app.state.schedule.every(s => s.start >= advancedElapsed));
});
test('page hide cancels a pending cycle and prevents automatic playback or Writer continuation', async () => {
  let release; const paths = [];
  const app = setup(async url => { paths.push(new URL(url).pathname); return new Promise(resolve => { release = resolve; }); });
  app.context.bindEvents(); app.state.modelRun = true; app.state.playing = true; app.state.modelController = new AbortController();
  const pending = app.context.replanConnected(false); await nextTurn();
  app.windowListeners.get('pagehide')();
  release(response(plan())); await pending;
  assert.deepEqual(paths, ['/api/plan']); assert.equal(app.state.playing, false); assert.equal(app.state.modelRun, false); assert.equal(app.state.generated, false);
});
test('billable network failures report unknown cost while pre-dispatch cancellation costs no request', async () => {
  let fetched = 0;
  const app = setup(async () => { fetched++; throw new Error('Mock connection lost'); });
  await assert.rejects(app.context.requestApi('/api/write', { method: 'POST', body: { test: true } }), /cost are unknown/u);
  assert.equal(app.state.receipts[0].cost, null); assert.equal(app.state.receipts[0].mode, 'outcome-unknown');
  const controller = new AbortController(); controller.abort();
  await assert.rejects(app.context.requestApi('/api/write', { method: 'POST', signal: controller.signal }), /before dispatch/u);
  assert.equal(fetched, 1); assert.equal(app.state.receipts.length, 1);
});

test('connected Replay keeps actual 1x speech playing during RPC and swaps Writer output only at speech end',async()=>{
  const app=setup(async url=>response(new URL(url).pathname==='/api/plan'?plan():story()));Object.assign(app.state,{audio:true,speed:1,playing:true,speechMeasurementValid:true,modelRun:true,modelController:new AbortController()});app.context.speakCurrent();const original=app.spoken[0];await app.context.replanConnected(false);
  assert.equal(app.state.audio,true);assert.equal(app.state.playing,true);assert.equal(app.state.utterance,original);assert.equal(app.state.generated,false);assert.ok(app.state.pendingReplayText);assert.equal(app.cancels.length,0);original.onend();assert.equal(app.state.generated,true);assert.equal(app.spoken.length,2);assert.equal(app.spoken[1].text,'The old clue opens a new door.');assert.equal(app.state.speechMeasurementValid,true);original.onend();assert.equal(app.state.utterance,app.spoken[1]);app.state.playing=false;app.context.cancelReplayModelCycle();app.context.resetSpeech();
});
test('pausing connected Replay cancels a pending cycle without a Writer continuation and retains its late receipt',async()=>{
  let release;const paths=[];const app=setup(async url=>{paths.push(new URL(url).pathname);return new Promise(resolve=>{release=resolve;});});Object.assign(app.state,{playing:true,modelRun:true,modelController:new AbortController()});const pending=app.context.replanConnected(false);await nextTurn();app.context.setPlaying(false);release(response(plan()));await pending;assert.deepEqual(paths,['/api/plan']);assert.equal(app.state.playing,false);assert.equal(app.state.modelRun,false);assert.ok(app.state.receipts.some(receipt=>receipt.cost===.0001));
});
test('a single generated Replay exit line stays hidden until the known-clock final window and is spoken once',async()=>{
  let calls=0;const app=setup(async()=>{calls++;throw Error('No paid request after ending');});app.node('sentence').textContent='The previous body remains visible.';app.state.pendingReplayText={sentences:['The final stop is Seongsu'],model:'Mock Writer',epoch:app.state.modelEpoch,stationIndex:app.state.stationIndex};assert.equal(app.context.applyPendingReplayText(),true);assert.equal(app.state.replayHeldEnding,true);assert.equal(app.node('sentence').textContent,'The previous body remains visible.');Object.assign(app.state,{audio:true,speed:1,playing:true});app.context.speakCurrent();assert.equal(app.spoken.length,0);app.state.elapsed=app.state.schedule[0].start;app.context.speakCurrent();assert.equal(app.spoken.length,1);app.spoken[0].onend();assert.equal(app.state.replayEndingCompleted,true);app.state.modelRun=true;await app.context.replanConnected(false);app.context.speakCurrent();assert.equal(calls,0);assert.equal(app.spoken.length,1);app.state.playing=false;app.context.resetSpeech();
});
test('a newer Replay station supersedes an in-flight plan before any obsolete Writer call',async()=>{
  let release,plans=0,writes=0;const app=setup(async url=>{const path=new URL(url).pathname;if(path==='/api/plan'){plans++;if(plans===1)return new Promise(resolve=>{release=resolve;});return response(plan());}if(path==='/api/write'){writes++;return response(story());}throw Error('Unexpected route');});Object.assign(app.state,{modelRun:true,modelController:new AbortController()});const pending=app.context.replanConnected(false);await nextTurn();app.state.stationIndex=1;app.state.elapsed=220;app.state.pendingReplayStation=1;release(response(plan()));await pending;await nextTurn();assert.equal(plans,2);assert.equal(writes,1);assert.equal(app.state.generated,true);assert.ok(app.state.logs.some(log=>log.op==='STALE PLAN'));app.context.cancelReplayModelCycle();
});
test('connected Replay applies named drop, insert and compress at speech boundaries and retains untouched scenes',async()=>{
  const writes=[];const app=setup(async(url,init)=>{if(new URL(url).pathname==='/api/plan')return response({...plan(),plan:{...plan().plan,budget_chars:500,ops:[{op:'drop',scene:'scene-2'},{op:'insert',scene:'bridge'},{op:'compress',scene:'exit'}]}});const body=JSON.parse(init.body);writes.push(body);return response({...story(),sentences:body.is_last_scene?['Now Seongsu']:['An inserted bridge.']});});
  const initial=['A1','A2','A3','B1','B2','B3','Your exit is Seongsu'];Object.assign(app.state,{lines:initial,generated:true,replayScenes:app.context.partitionStoryScenes(initial),replayReadCount:1,replayWriterCalls:1,audio:true,speed:1,playing:true,modelRun:true,modelController:new AbortController()});app.state.schedule=app.context.makeSchedule(initial,400);app.context.speakCurrent();const first=app.spoken[0];await app.context.replanConnected(false);assert.deepEqual(Array.from(app.state.replayScenes,scene=>scene.id),['scene-1','scene-2','exit']);assert.equal(app.state.pendingReplayPatches.length,3);assert.equal(writes.length,2);assert.equal(writes[0].is_last_scene,false);assert.equal(writes[1].is_last_scene,true);assert.match(writes[0].scene,/insert only named scene bridge/u);assert.match(writes[1].scene,/compress only named scene exit/u);
  first.onend();assert.deepEqual(Array.from(app.state.replayScenes,scene=>scene.id),['scene-1','bridge','exit']);assert.deepEqual(Array.from(app.state.replayScenes[0].sentences),['A1','A2','A3']);assert.deepEqual(Array.from(app.state.replayScenes.at(-1).sentences),['Now Seongsu']);assert.equal(app.spoken[1].text,'A2');assert.equal(app.state.replayWriterCalls,3);app.state.playing=false;app.context.cancelReplayModelCycle();app.context.resetSpeech();
});
test('the four-Writer allowance skips paid revisions while valid named local drops still apply',async()=>{
  const paths=[];const app=setup(async url=>{paths.push(new URL(url).pathname);if(new URL(url).pathname!='/api/plan')throw Error('Writer cap forbids another paid revision');return response({...plan(),plan:{...plan().plan,budget_chars:500,ops:[{op:'compress',scene:'exit'},{op:'insert',scene:'bridge'},{op:'drop',scene:'scene-2'}]}});});const initial=['A1','A2','A3','B1','B2','B3','Your exit is Seongsu'];Object.assign(app.state,{lines:initial,generated:true,replayScenes:app.context.partitionStoryScenes(initial),replayReadCount:1,replayWriterCalls:4,modelRun:true,modelController:new AbortController()});app.state.schedule=app.context.makeSchedule(initial,400);await app.context.replanConnected(false);assert.deepEqual(paths,['/api/plan']);assert.deepEqual(Array.from(app.state.replayScenes,scene=>scene.id),['scene-1','exit']);assert.equal(app.state.replayWriterCalls,4);assert.equal(app.state.logs.filter(log=>log.op==='WRITER CAP').length,2);app.context.cancelReplayModelCycle();
});

test('a multi-sentence exit revision is rejected without losing its Writer receipt or truncating the exit',async()=>{
  const app=setup(async url=>new URL(url).pathname==='/api/plan'?response({...plan(),plan:{...plan().plan,ops:[{op:'compress',scene:'exit'}]}}):response({...story(),sentences:['A','Seongsu']}));const initial=['A1','A2','A3','B1','B2','B3','Your exit is Seongsu'];Object.assign(app.state,{lines:initial,generated:true,replayScenes:app.context.partitionStoryScenes(initial),replayReadCount:1,replayWriterCalls:1,modelRun:true,modelController:new AbortController()});app.state.schedule=app.context.makeSchedule(initial,400);await app.context.replanConnected(false);assert.deepEqual(Array.from(app.state.replayScenes.at(-1).sentences),['Your exit is Seongsu']);assert.equal(app.state.replayWriterCalls,2);assert.ok(app.state.receipts.some(receipt=>receipt.cost===.0002));assert.equal(app.state.modelRun,false);assert.match(app.node('notice').textContent,/exactly one sentence/u);
});
