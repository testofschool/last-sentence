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
  const window = { speechSynthesis: { cancel() {}, getVoices: () => [] }, addEventListener: (name, callback) => windowListeners.set(name, callback) };
  const context = vm.createContext({ fetch, Response, URL, AbortController, DOMException, performance, setTimeout, clearTimeout, requestAnimationFrame: () => 1, cancelAnimationFrame() {}, window, navigator: {} });
  // There is no document during evaluation, so normal application boot does not run.
  vm.runInContext(source, context, { filename: 'web/app.js' });
  context.document = document;
  const state = vm.runInContext('state', context);
  Object.assign(state, { journey: { line: '2호선', trainNo: 'mock' }, stations: [{ name: 'Start', offset_s: 0 }, { name: 'Middle', offset_s: 200 }, { name: 'Seongsu', offset_s: 400 }], lines: ['A remembered clue.', 'The remaining bridge.', 'The final stop is Seongsu'], apiBase: 'https://old.example', apiToken: 'mock-session', elapsed: 100, sentenceIndex: 0, stationIndex: 0 });
  state.schedule = context.makeSchedule(state.lines, 400);
  return { context, state, node, document, documentListeners, windowListeners };
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
test('network replanning freezes the known replay clock and carries actual story context', async () => {
  let release, writeInput;
  const app = setup(async (url, init) => {
    if (new URL(url).pathname === '/api/plan') return new Promise(resolve => { release = resolve; });
    if (new URL(url).pathname === '/api/write') { writeInput = JSON.parse(init.body); return response(story()); }
    throw Error('Unexpected mock route');
  });
  app.state.modelRun = true; app.state.playing = true; app.state.modelController = new AbortController();
  const pending = app.context.replanConnected(false); await nextTurn();
  assert.equal(app.state.playing, false); const elapsed = app.state.elapsed;
  app.context.tick(performance.now() + 60000); assert.equal(app.state.elapsed, elapsed);
  release(response(plan())); await pending;
  assert.equal(app.state.generated, true); assert.equal(app.state.playing, true);
  assert.match(writeInput.scene, /A remembered clue/u); assert.match(writeInput.scene, /compress:remaining-story/u);
  assert.ok(Array.from(writeInput.scene).length <= 500); assert.equal(app.state.elapsed, elapsed);
  assert.ok(app.state.schedule.every(s => s.start >= elapsed));
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
