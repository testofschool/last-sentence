import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
const source=(await readFile(new URL('../web/app.js',import.meta.url),'utf8')).replace(/^export /gmu,'');
class Element{
  constructor(){this.children=[];this.value='';this.textContent='';this.dataset={};this.hidden=false;this.disabled=false;this.style={setProperty(){}};this.selected=new Map();this.listeners=new Map();this.parentElement={hidden:false,parentElement:{hidden:false}};this.classList={add(){},remove(){},toggle(){}};}
  setAttribute(){} append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}querySelector(key){if(!this.selected.has(key))this.selected.set(key,new Element());return this.selected.get(key);}querySelectorAll(){return [];}addEventListener(name,cb){this.listeners.set(name,cb);}close(){}showModal(){}
}
function setup(fetch){
  let now=10000;const ids=new Map(),selectors=new Map(),spoken=[],cancels=[],documentListeners=new Map(),windowListeners=new Map();const node=id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);};
  const document={hidden:false,documentElement:new Element(),getElementById:node,createElement:()=>new Element(),createTextNode:text=>({textContent:text}),querySelector:key=>{if(!selectors.has(key))selectors.set(key,new Element());return selectors.get(key);},querySelectorAll:()=>[],addEventListener(name,handler){documentListeners.set(name,handler);}};
  const window={speechSynthesis:{cancel(){cancels.push(true);},getVoices:()=>[{lang:'en-US',name:'Mock English'}],speak(utterance){spoken.push(utterance);}},addEventListener(name,handler){windowListeners.set(name,handler);}};
  class Utterance{constructor(text){this.text=text;}}window.SpeechSynthesisUtterance=Utterance;
  const context=vm.createContext({fetch,Response,URL,URLSearchParams,AbortController,DOMException,performance:{now:()=>now},setTimeout,clearTimeout,requestAnimationFrame:()=>1,cancelAnimationFrame(){},SpeechSynthesisUtterance:Utterance,window,navigator:{}});
  vm.runInContext(source,context);context.document=document;const state=vm.runInContext('state',context);
  Object.assign(state,{mode:'live',journey:{line:'2호선'},stations:[{name:'Start',offset_s:0},{name:'Exit',offset_s:400}],lines:['Authored opening','Authored ending'],apiBase:'https://mock.example',apiToken:'mock-session'});state.schedule=context.makeSchedule(state.lines,400);
  Object.assign(state.live,{active:true,selectedKey:'123|0',to:'Exit',etaReceivedAt:now,eta:eta(),status:status()});
  return {context,state,node,document,spoken,cancels,documentListeners,windowListeners,advance(ms){now+=ms;}};
}
const usage={prompt_tokens:100,completion_tokens:20,total_tokens:120};
const response=(data,status=200)=>Response.json(data,{status});
function status(){return {position_enabled:true,inference_enabled:true,eta_model_configured:true,tavily_enabled:false,limits:{completion_calls_remaining:20,reservation_budget_usd:3,reserved_usd:0}};}
function eta(){return {eta_available:true,eta_source:'recorded-model',remaining_s:400,stations_left:3,horizon_supported:true,route:['Start','One','Two','Exit'],eligible_exits:[{station:'Exit',stations_left:3}],anchor:{verified:true,trainNo:'123',direction:'0',station:'Start',recptnDt:'2026-10-30 10:00:00',epoch_s:1000000000,trainSttus:'1'},anchor_age_s:1,evaluation:{n:12,median_relative_error:.1}};}
function plan(){return {model:'Mock Conductor',usage,cost_usd:.0001,latency_ms:50,plan:{budget_chars:300,log:'Compress the remaining scene.',ops:[{scene:'remaining-story',op:'compress',reason:'Budget'}]}};}
function writer(){return {model:'Mock Writer',usage,cost_usd:.0002,latency_ms:70,sentences:['The clue returns.','Your story ends at Exit']};}
const turn=()=>new Promise(resolve=>setImmediate(resolve));

test('Live never generates before an actual verified anchor and a 3–10-stop exit',async()=>{
  let calls=0;const app=setup(async()=>{calls++;throw Error('No request permitted');});app.state.live.eta={eta_available:false,reason:'no_arrival_anchor'};await app.context.startLiveStory();assert.equal(calls,0);assert.equal(app.state.live.storyActive,false);assert.match(app.node('notice').textContent,/verified train anchor/u);
});
test('Live clock advances during model requests and plans carry a server-verifiable train anchor',async()=>{
  let release,planInput;const app=setup(async(url,init)=>{const path=new URL(url).pathname;if(path==='/api/status')return response(status());if(path==='/api/plan'){planInput=JSON.parse(init.body);return new Promise(resolve=>{release=resolve;});}if(path==='/api/write')return response(writer());throw Error('Unexpected endpoint');});
  const pending=app.context.startLiveStory();await turn();assert.equal(app.state.live.modelBusy,true);assert.equal(app.state.live.storyActive,true);app.advance(5000);app.context.liveTick();assert.equal(app.context.currentLiveRemaining(),395);release(response(plan()));await pending;
  assert.equal(planInput.eta_source,'recorded-model');assert.equal(planInput.train_anchor.trainNo,'123');assert.equal(planInput.train_anchor.direction,'0');assert.equal(planInput.train_anchor.to,'Exit');assert.equal(app.state.live.sentences[0],'The clue returns.');assert.equal(app.state.live.modelBusy,false);assert.equal(app.state.live.storyActive,true);assert.ok(app.state.live.textEndAt>15000);app.context.stopLiveMonitoring();
});
test('Live Writer swaps at a sentence boundary without replacing text already in progress',async()=>{
  const app=setup(async url=>response(new URL(url).pathname==='/api/plan'?plan():writer()));Object.assign(app.state.live,{storyActive:true,startedAt:10000,sentences:['The old clue is being read.','Old ending'],sentenceIndex:0,textEndAt:16000,modelController:new AbortController()});
  await app.context.liveModelRound(false);assert.equal(app.state.live.sentences[0],'The old clue is being read.');assert.ok(app.state.live.pendingText);app.context.advanceLiveSentence('virtual-text-timing');assert.equal(app.state.live.sentences[0],'The clue returns.');assert.equal(app.state.live.pendingText,null);assert.equal(app.node('sentence').textContent,'The clue returns.');app.context.stopLiveMonitoring();
});
test('Canceling Live retains a late plan receipt and prevents any subsequent Writer request',async()=>{
  let release;const paths=[];const app=setup(async url=>{paths.push(new URL(url).pathname);return new Promise(resolve=>{release=resolve;});});Object.assign(app.state.live,{storyActive:true,startedAt:10000,modelController:new AbortController()});const pending=app.context.liveModelRound(true);await turn();app.context.stopLiveMonitoring('Stopped');release(response(plan()));await pending;assert.deepEqual(paths,['/api/plan']);assert.equal(app.state.live.storyActive,false);assert.ok(app.state.receipts.some(receipt=>receipt.cost===.0001));
});
test('Live speech queues changes after actual end and stale callbacks cannot clear the next utterance',()=>{
  const app=setup(async()=>{throw Error('No fetch');});app.state.audio=true;Object.assign(app.state.live,{storyActive:true,sentences:['Old sentence','Old ending'],sentenceIndex:0,continuousAudio:true});app.context.startLiveSentence();const first=app.spoken[0];app.state.live.pendingText={model:'Mock Writer',sentences:['New sentence','New ending'],anchorKey:app.context.liveAnchorKey(),storyEpoch:app.state.live.storyEpoch};first.onend();assert.equal(app.spoken.length,2);assert.equal(app.spoken[1].text,'New sentence');assert.equal(app.cancels.length,0);first.onend();assert.equal(app.state.live.utterance,app.spoken[1]);app.context.stopLiveMonitoring();
});
test('Live arrival error requires continuous actual browser speech; virtual text remains explicit',()=>{
  const app=setup(async()=>{throw Error('No fetch');});Object.assign(app.state.live,{arrival:{epoch_s:1000000000},lastSentenceEndWall:1000000004000,lastEndKind:'browser-speech-end',continuousAudio:true});app.context.showLiveLanding();assert.equal(app.node('landing-error').textContent,'+4.0 s');assert.match(app.node('landing-label').textContent,/SPEECH VS STATION OBSERVATION/u);app.state.live.continuousAudio=false;app.context.showLiveLanding();assert.equal(app.node('landing-error').textContent,'Audio unmeasured');
});
test('Live polling only exposes anchored forward exits and does not generate automatically',async()=>{
  const paths=[];const app=setup(async url=>{const path=new URL(url).pathname;paths.push(path);if(path==='/api/status')return response(status());if(path==='/api/position')return response({mode:'live',positions:[{trainNo:'123',statnNm:'Start',updnLine:'0',trainSttus:'1'}]});if(path==='/api/eta')return response({...eta(),eta_available:false,reason:'choose_exit',eligible_exits:[{station:'Too close',stations_left:2},{station:'Exit',stations_left:3},{station:'Too far',stations_left:11}]});throw Error('No model calls permitted');});app.state.live.to='';await app.context.refreshLive();assert.deepEqual(paths,['/api/status','/api/position','/api/eta']);assert.equal(app.node('live-start').disabled,true);assert.deepEqual(app.node('live-exit-select').children.map(option=>option.value),['','Exit']);app.context.stopLiveMonitoring();
});
test('Hiding the tab cancels a pending Live plan and cannot dispatch its Writer continuation',async()=>{
  let release;const paths=[];const app=setup(async url=>{paths.push(new URL(url).pathname);return new Promise(resolve=>{release=resolve;});});
  app.context.bindEvents();Object.assign(app.state.live,{storyActive:true,startedAt:10000,continuousAudio:true,modelController:new AbortController()});
  const pending=app.context.liveModelRound(true);await turn();app.document.hidden=true;app.documentListeners.get('visibilitychange')();release(response(plan()));await pending;
  assert.deepEqual(paths,['/api/plan']);assert.equal(app.state.live.storyActive,false);assert.equal(app.state.live.active,false);assert.equal(app.state.live.continuousAudio,false);assert.ok(app.state.receipts.some(r=>r.cost===.0001));
});
test('A queued Writer response is rechecked at the speech boundary after a newer station anchor',()=>{
  const app=setup(async()=>{throw Error('No fetch');});app.state.audio=true;Object.assign(app.state.live,{storyActive:true,sentences:['Current sentence','Existing ending'],sentenceIndex:0,continuousAudio:true});app.context.startLiveSentence();
  app.state.live.pendingText={model:'Mock Writer',sentences:['Stale replacement','Stale ending'],anchorKey:app.context.liveAnchorKey(),storyEpoch:app.state.live.storyEpoch};
  app.state.live.eta={...eta(),anchor:{...eta().anchor,station:'One',recptnDt:'2026-10-30 10:02:00'}};
  app.spoken[0].onend();assert.equal(app.state.live.pendingText,null);assert.equal(app.spoken.length,1);assert.equal(app.state.live.heldEnding,true);assert.equal(app.state.live.sentences[0],'Current sentence');assert.notEqual(app.node('sentence').textContent,'Stale replacement');app.context.stopLiveMonitoring();
});
test('Arrival before any Writer output ends the controller without inventing a speech end',async()=>{
  const app=setup(async url=>{const path=new URL(url).pathname;if(path==='/api/status')return response(status());if(path==='/api/position')return response({mode:'live',positions:[{trainNo:'123',statnNm:'Exit',updnLine:'0',trainSttus:'1'}]});if(path==='/api/eta')return response({...eta(),remaining_s:0,stations_left:0,route:['Exit'],anchor:{...eta().anchor,station:'Exit'}});throw Error('No model request permitted');});
  Object.assign(app.state.live,{storyActive:true,modelBusy:true,sentences:[],frame:1,modelController:new AbortController()});await app.context.refreshLive();
  assert.equal(app.state.live.storyActive,false);assert.equal(app.state.live.modelBusy,false);assert.equal(app.state.live.frame,0);assert.equal(app.state.live.lastSentenceEndWall,null);assert.equal(app.node('landing-error').textContent,'Unmeasured');
});
test('A train terminus before the selected exit stops Live without scheduling another model call',async()=>{
  const paths=[];const app=setup(async url=>{const path=new URL(url).pathname;paths.push(path);if(path==='/api/status')return response(status());if(path==='/api/position')return response({mode:'live',positions:[{trainNo:'123',statnNm:'Start',updnLine:'0',trainSttus:'1'}]});if(path==='/api/eta')return response({...eta(),eta_available:false,reason:'route_exceeds_train_terminus',eligible_exits:[],anchor:{...eta().anchor,terminus:{station:'Before exit'}}});throw Error('No model call permitted');});
  Object.assign(app.state.live,{storyActive:true,startedAt:10000,modelController:new AbortController()});await app.context.refreshLive();assert.equal(app.state.live.storyActive,false);assert.deepEqual(paths,['/api/status','/api/position','/api/eta']);app.context.stopLiveMonitoring();
});
test('A Writer response that consumes the remaining live window is billed but never installed',async()=>{
  let release;const app=setup(async url=>{const path=new URL(url).pathname;if(path==='/api/plan')return response(plan());if(path==='/api/write')return new Promise(resolve=>{release=resolve;});throw Error('Unexpected endpoint');});
  Object.assign(app.state.live,{storyActive:true,startedAt:10000,modelController:new AbortController()});const pending=app.context.liveModelRound(true);await turn();app.advance(500000);release(response(writer()));await pending;
  assert.equal(app.state.live.pendingText,null);assert.equal(app.state.live.sentences.length,0);assert.ok(app.state.receipts.some(r=>r.cost===.0002));app.context.stopLiveMonitoring();
});
test('A valid queued replacement is discarded if its anchor expires before the speech boundary',()=>{
  const app=setup(async()=>{throw Error('No fetch');});app.state.audio=true;Object.assign(app.state.live,{storyActive:true,sentences:['Current sentence','Existing ending'],sentenceIndex:0,continuousAudio:true});app.context.startLiveSentence();
  app.state.live.pendingText={model:'Mock Writer',sentences:['Expired replacement','Expired ending'],anchorKey:app.context.liveAnchorKey(),storyEpoch:app.state.live.storyEpoch};app.state.live.eta.valid_until=new Date(Date.now()-1000).toISOString();
  app.spoken[0].onend();assert.equal(app.state.live.pendingText,null);assert.equal(app.spoken.length,1);assert.equal(app.state.live.storyActive,false);assert.equal(app.node('landing-error').textContent,'Anchor expired');assert.equal(app.state.live.sentences[0],'Current sentence');app.context.stopLiveMonitoring();
});

test('The exit sentence stays hidden and unspoken while the train still has 300 seconds left',()=>{
  const app=setup(async()=>{throw Error('No model call');});app.state.audio=true;app.state.live.eta.remaining_s=300;Object.assign(app.state.live,{storyActive:true,sentences:['A clue glints in the window.','Your exit is Exit'],sentenceIndex:0});app.context.startLiveSentence();app.spoken[0].onend();
  assert.equal(app.spoken.length,1);assert.equal(app.state.live.heldEnding,true);assert.equal(app.state.live.endingStarted,false);assert.equal(app.node('sentence').textContent,'A clue glints in the window.');assert.notEqual(app.node('sentence').textContent,'Your exit is Exit');app.context.stopLiveMonitoring();
});
test('The held exit sentence releases near its timing window exactly once and closes further model rounds',async()=>{
  let calls=0;const app=setup(async()=>{calls++;throw Error('No request after ending');});app.state.audio=true;app.state.live.eta.remaining_s=300;Object.assign(app.state.live,{storyActive:true,sentences:['Prior line','Your exit is Exit'],sentenceIndex:1,hasReadSentence:true});app.node('sentence').textContent='Prior line';app.context.startLiveSentence();assert.equal(app.spoken.length,0);
  app.advance(295000);app.context.liveTick();assert.equal(app.spoken.length,1);assert.equal(app.spoken[0].text,'Your exit is Exit');app.spoken[0].onend();assert.equal(app.state.live.endingCompleted,true);
  app.state.live.eta={...eta(),remaining_s:100,anchor:{...eta().anchor,station:'One',recptnDt:'2026-10-30 10:03:00'}};app.state.live.etaReceivedAt=305000;await app.context.liveModelRound(false);app.context.startLiveSentence();assert.equal(calls,0);assert.equal(app.spoken.length,1);app.context.stopLiveMonitoring();
});
test('A new station Writer may replace a held ending at the boundary before any exit cue is committed',()=>{
  const app=setup(async()=>{throw Error('No fetch');});app.state.audio=true;Object.assign(app.state.live,{storyActive:true,sentences:['Old body','Old exit is Exit'],sentenceIndex:1,heldEnding:true,hasReadSentence:true});app.state.live.pendingText={model:'Mock Writer',sentences:['A new body fits the train.','New exit is Exit'],anchorKey:app.context.liveAnchorKey(),storyEpoch:app.state.live.storyEpoch};
  assert.equal(app.context.applyPendingLiveText(),true);assert.equal(app.spoken.length,1);assert.equal(app.spoken[0].text,'A new body fits the train.');assert.equal(app.state.live.endingStarted,false);app.spoken[0].onend();assert.equal(app.state.live.heldEnding,true);assert.equal(app.spoken.length,1);app.context.stopLiveMonitoring();
});
test('An expired validated live anchor stops the active story and its animation instead of waiting forever',()=>{
  const app=setup(async()=>{throw Error('No fetch');});Object.assign(app.state.live,{storyActive:true,frame:9,modelController:new AbortController(),sentences:['Waiting body','Exit'],sentenceIndex:1,heldEnding:true});app.state.live.eta.valid_until=new Date(Date.now()-1000).toISOString();app.context.liveTick();assert.equal(app.state.live.storyActive,false);assert.equal(app.state.live.frame,0);assert.equal(app.state.live.modelController,null);assert.equal(app.node('landing-error').textContent,'Anchor expired');app.context.stopLiveMonitoring();
});
test('A changed ETA after the completed exit cue is logged without another paid model round',async()=>{
  const paths=[];const app=setup(async url=>{const path=new URL(url).pathname;paths.push(path);if(path==='/api/status')return response(status());if(path==='/api/position')return response({mode:'live',positions:[{trainNo:'123',statnNm:'One',updnLine:'0',trainSttus:'1'}]});if(path==='/api/eta')return response({...eta(),anchor:{...eta().anchor,station:'One',recptnDt:'2026-10-30 10:03:00'}});throw Error('No second model round');});Object.assign(app.state.live,{storyActive:true,endingStarted:true,endingCompleted:true,lastSentenceEndWall:Date.now(),lastEndKind:'virtual-text-timing'});await app.context.refreshLive();assert.deepEqual(paths,['/api/status','/api/position','/api/eta']);assert.equal(app.state.live.endingForecastChanges.length,1);assert.ok(app.state.logs.some(log=>log.op==='EARLY END'));app.context.stopLiveMonitoring();
});
test('Live affected-scene revisions preserve speaking text and untouched scenes with one Writer per paid target',async()=>{
  const writes=[];const app=setup(async(url,init)=>{if(new URL(url).pathname==='/api/plan')return response({...plan(),plan:{...plan().plan,budget_chars:500,ops:[{op:'drop',scene:'scene-2'},{op:'insert',scene:'bridge'}]}});const body=JSON.parse(init.body);writes.push(body);return response({...writer(),sentences:['An inserted live bridge.']});});const initial=['A1','A2','A3','B1','B2','B3','Your exit is Exit'];app.state.audio=true;Object.assign(app.state.live,{storyActive:true,startedAt:10000,sentences:initial,scenes:app.context.partitionStoryScenes(initial),readCount:1,writerCalls:1,sentenceIndex:0,modelController:new AbortController()});app.context.startLiveSentence();await app.context.liveModelRound(false);assert.equal(app.state.live.pendingPatches.length,2);assert.equal(writes.length,1);assert.equal(writes[0].is_last_scene,false);app.spoken[0].onend();assert.deepEqual(Array.from(app.state.live.scenes,scene=>scene.id),['scene-1','bridge','exit']);assert.deepEqual(Array.from(app.state.live.scenes[0].sentences),['A1','A2','A3']);assert.equal(app.spoken[1].text,'A2');assert.equal(app.state.live.writerCalls,2);app.context.stopLiveMonitoring();
});
test('Live readiness uses the selected line quality instead of another line’s ready artifact',async()=>{
  const paths=[];const app=setup(async url=>{const parsed=new URL(url);paths.push(parsed.pathname);if(parsed.pathname==='/api/status')return response({...status(),eta_models:{'2호선':{valid:true},'5호선':{valid:false,reason:'recording_incomplete'},'7호선':{valid:false}}});if(parsed.pathname==='/api/position')return response({mode:'live',positions:[{trainNo:'123',statnNm:'Start',updnLine:'0',trainSttus:'1'}]});throw Error('No ETA or model call allowed for an unready selected line');});app.state.journey.line='5호선';Object.assign(app.state.live,{storyActive:true,modelController:new AbortController()});await app.context.refreshLive();assert.deepEqual(paths,['/api/status','/api/position']);assert.equal(app.state.live.storyActive,false);assert.equal(app.state.live.eta,null);assert.equal(app.node('live-start').disabled,true);app.context.stopLiveMonitoring();
});
