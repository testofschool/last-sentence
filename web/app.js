/* Keyless replay: authored fixtures, local planning rules, no generated model receipts. */
const $ = (id) => document.getElementById(id);
const routeColors = {'2호선':'#727d58','5호선':'#8b7897','7호선':'#8c8951'};
const state = {source:'fixture',fixtureJourneys:[],recordedJourneys:[],recordedInfo:{},journeys:[],journey:null,stations:[],lang:'en',mode:'replay',speed:4,elapsed:0,playing:false,audio:false,audioEpoch:0,utterance:null,lastSpoken:-1,lastSentenceEnd:null,sentenceIndex:0,stationIndex:-1,lastTick:0,frame:0,schedule:[],lines:[],logs:[],receipts:[],apiBase:'',apiToken:'',requestEpoch:0,livePositions:[],wakeLock:null,finished:false,arrivalReached:false,speechMeasurementValid:false,speechMeasurementReason:'A full uninterrupted audio replay has not run.',modelRun:false,modelBusy:false,modelEpoch:0,modelController:null,modelFact:null,generated:false,pendingModelResume:false,live:{active:false,epoch:0,timer:0,polling:false,controller:null,status:null,positions:[],selectedKey:'',to:'',eta:null,etaReceivedAt:0,storyActive:false,storyEpoch:0,modelController:null,modelBusy:false,pendingAnchor:null,lastPlannedAnchor:'',fact:null,startedAt:0,startedWall:0,frame:0,sentences:[],sentenceIndex:0,utterance:null,speechEpoch:0,textEndAt:0,pendingText:null,lastSentenceEndWall:null,lastEndKind:null,continuousAudio:false,arrival:null,heldEnding:false,endingStarted:false,endingCompleted:false,hasReadSentence:false,endingForecastChanges:[]}};

export function formatTime(seconds){const s=Math.max(0,Math.floor(Number.isFinite(seconds)?seconds:0));return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;}
export function storyBudget(seconds,cps=4.51,margin=20){return Math.floor(Math.max(0,seconds-margin)*cps);}
export function makeSchedule(lines,duration){
  if(!lines.length||!Number.isFinite(duration)||duration<=0)return [];
  const finish=Math.max(.2,duration-3);
  if(lines.length===1)return [{text:lines[0],start:Math.max(0,finish-Math.max(2,[...lines[0]].length/4.51)),end:finish,index:0}];
  const natural=lines.map(text=>Math.max(2,[...text].length/4.51));
  const sum=natural.reduce((a,b)=>a+b,0);
  const scale=Math.min(1,finish*.84/sum);
  const gap=lines.length>1?Math.max(0,(finish-sum*scale)/(lines.length-1)):0;
  let t=0;return lines.map((text,index)=>{const start=t,end=start+natural[index]*scale;t=end+gap;return {text,start,end,index};});
}
export function sampleSchedule(schedule,elapsed){if(!schedule.length)return 0;let i=0;for(let j=0;j<schedule.length;j++){if(schedule[j].start<=elapsed)i=j;else break;}return i;}

function authoredStory(lang,exit){
  if(lang==='ko')return [
    '옆자리에는 노란 봉투 하나가 놓여 있었다.',
    '겉면에는 ‘돌아가는 길에 열어 볼 것’이라고 쓰여 있었다.',
    '봉투 안에는 서울을 그린 작은 지도가 있었다.',
    '누군가 다리와 골목마다 별을 그려 두었다.',
    '별 하나는 창밖 어둠을 따라 천천히 움직였다.',
    '이상하게도 열차가 멈추면 그 별도 멈췄다.',
    '지도를 뒤집자 손글씨 한 줄이 나타났다.',
    '‘오늘 놓친 것보다, 아직 만날 것이 더 많아.’',
    '당신은 봉투를 접어 주머니에 넣었다.',
    '열차가 마지막 굽이를 지나며 빛 속으로 들어섰다.',
    '지도의 빈칸은 당신이 걸어갈 길이었다.',
    `이제 이 이야기의 밖으로 걸어갈 시간, ${exit}`
  ];
  return [
    'Someone had left a yellow envelope on the seat beside you.',
    'On its cover, in small letters: “Open on the way home.”',
    'Inside was a map of Seoul, drawn entirely from memory.',
    'Tiny stars marked the bridges, the alleys, the places someone had loved.',
    'One star seemed to move with the lights beyond the window.',
    'Whenever the train stopped, the little star stopped, too.',
    'You turned the map over. There was one more handwritten line.',
    '“There is still more waiting for you than you have left behind.”',
    'You folded the envelope and slipped it into your coat.',
    'The train rounded its last bend, carrying the city back into the light.',
    'The map’s blank space was a path you would have to draw yourself.',
    `Your next chapter is waiting just outside, at ${exit}`
  ];
}
function isRecorded(){return state.source==='recorded';}
function duration(){return state.stations.at(-1)?.offset_s||1;}
function exitName(){return state.stations.at(-1)?.name||'';}
function notice(text){$('notice').textContent=text;$('notice').hidden=!text;}
function appendLog(text,op='',time=state.elapsed){
  state.logs.unshift({text,op,time});state.logs=state.logs.slice(0,20);renderLogs();
}
function renderLogs(){
  $('conductor-log').replaceChildren(...state.logs.map(log=>{
    const row=document.createElement('div');row.className='log-entry';const time=document.createElement('time');time.textContent=formatTime(log.time);
    const p=document.createElement('p');p.textContent=log.text;if(log.op){const tag=document.createElement('span');tag.className='log-operation';tag.textContent=log.op;p.append(tag);}row.append(time,p);return row;
  }));
}
function resetSpeech(){state.audioEpoch++;state.utterance=null;if('speechSynthesis'in window)window.speechSynthesis.cancel();state.lastSpoken=-1;}
function invalidateSpeech(reason){state.speechMeasurementValid=false;state.speechMeasurementReason=reason;}
function stopAnimation(){if(state.frame)cancelAnimationFrame(state.frame);state.frame=0;state.lastTick=0;}
function setPlaying(playing){
  if(state.mode!=='replay')return;
  if(playing&&state.elapsed>=duration()&&state.finished)resetReplay();
  state.playing=playing;state.lastTick=performance.now();
  if(playing){if(state.audio&&state.speed===1){state.lastSpoken=state.sentenceIndex-1;speakCurrent();}state.frame=requestAnimationFrame(tick);}else{if(state.audio&&state.elapsed>0)invalidateSpeech('Playback was paused or interrupted. Restart at 1× with sound for a continuous measurement.');stopAnimation();resetSpeech();}
  renderPlayback();
}
function resetReplay(){
  stopModelRun();stopAnimation();resetSpeech();state.playing=false;state.elapsed=0;state.finished=false;state.arrivalReached=false;state.lastSentenceEnd=null;state.stationIndex=-1;state.sentenceIndex=0;state.logs=[];state.generated=false;state.speechMeasurementValid=state.audio&&state.speed===1;state.speechMeasurementReason=state.speechMeasurementValid?'':'A full uninterrupted audio replay has not run.';
  const exit=exitName();state.lines=authoredStory(state.lang,exit);state.schedule=makeSchedule(state.lines,duration());
  $('landing-result').hidden=true;$('scrubber').max=String(duration());
  appendLog(`${state.stations.length-1} stops · ${formatTime(duration())} · preparing an authored story.`, 'READY',0);
  appendLog(isRecorded()?'Known observation timeline supplied. This is a replay, not an arrival forecast.':'Fixture clock supplied; no live ETA or model has been measured.',isRecorded()?'RECORDED':'FIXTURE',0);
  updateProvenance();
  renderTimeline();renderSentence();renderPosition();renderPlayback();
}
function selectJourney(line,exit,journeyId){
  if(state.mode==='live'){stopLiveMonitoring('Route changed.');state.live.arrival=null;state.live.selectedKey='';state.live.to='';state.live.eta=null;}
  const journey=(journeyId?state.journeys.find(j=>j.id===journeyId):null)||state.journeys.find(j=>j.line===line)||state.journeys[0];if(!journey)return;state.journey=journey;
  const candidates=state.journeys.filter(j=>j.line===journey.line);$('journey-select').replaceChildren(...candidates.map(j=>{const option=document.createElement('option');option.value=j.id;option.textContent=isRecorded()?`Train ${j.trainNo} · ${j.stations[0].name} → ${j.stations.at(-1).name}`:`${j.stations[0].name} → ${j.stations.at(-1).name}`;option.selected=j.id===journey.id;return option;}));$('journey-select').disabled=candidates.length<2;
  const previous=exit||journey.stations.at(-1).name;
  $('exit-select').replaceChildren(...journey.stations.slice(1).map(station=>{const option=document.createElement('option');option.value=station.name;option.textContent=station.name;option.selected=station.name===previous;return option;}));
  if(!$('exit-select').value)$('exit-select').value=journey.stations.at(-1).name;
  let stop=journey.stations.findIndex(s=>s.name===$('exit-select').value);if(stop<1)stop=journey.stations.length-1;
  state.stations=journey.stations.slice(0,stop+1);document.documentElement.style.setProperty('--route',routeColors[journey.line]||'#727d58');
  resetReplay();if(state.mode==='live')refreshLive();
}
function renderTimeline(){
  const total=duration();$('line-roundel').textContent=state.journey.line.replace('호선','');$('route-title').replaceChildren(document.createTextNode(state.stations[0].name+' '));
  const arrow=document.createElement('span');arrow.textContent='→';$('route-title').append(arrow,document.createTextNode(' '+exitName()));$('arrival-kind').textContent=isRecorded()?'RECORDED DURATION':'FIXTURE ARRIVAL';$('arrival-time').textContent=formatTime(total);$('duration-time').textContent=formatTime(total);
  $('station-dots').replaceChildren(...state.stations.map((station,index)=>{const el=document.createElement('div');el.className='station'+(index===state.stations.length-1?' exit':'');el.dataset.offset=station.offset_s;
    const dot=document.createElement('span');dot.className='dot';const label=document.createElement('span');label.className='station-name';label.textContent=station.name;
    if(index===state.stations.length-1){const cap=document.createElement('span');cap.className='exit-caption';cap.textContent='YOUR LAST SENTENCE';label.append(cap);}el.append(dot,label);return el;
  }));
}
function renderSentence(){
  const i=state.sentenceIndex;$('sentence').textContent=state.lines[i]||'';$('sentence').lang=state.lang;$('sentence-counter').textContent=`${String(i+1).padStart(2,'0')} / ${String(state.lines.length).padStart(2,'0')}`;
  const scene=i<4?0:i<9?1:2;$('chapter-label').textContent=[state.lang==='ko'?'프롤로그 / 누군가 남긴 편지':'PROLOGUE / A NOTE LEFT BEHIND',state.lang==='ko'?'두 번째 장 / 바뀌는 계획':'CHAPTER TWO / A CHANGE OF PLAN',state.lang==='ko'?'마지막 장 / 당신의 다음 이야기':'FINAL CHAPTER / YOUR NEXT STORY'][scene];
  $('story-title').textContent=state.generated?(state.lang==='ko'?'연결된 모델이 쓴 이야기':'A CONNECTED STORY'):(state.lang==='ko'?'노란 봉투':'THE YELLOW ENVELOPE');
  $('text-provenance').textContent=state.generated?`Nemotron ${state.lang==='ko'?'Ultra':'Super'} · ${isRecorded()?'recorded':'synthetic'} replay clock`:(state.lang==='ko'?'사람이 쓴 예시 · Writer: Ultra (미실행)':'Authored story · Writer: Super (not run)');
  const progress=(i+1)/state.lines.length;document.querySelectorAll('.sentence-rule span').forEach((span,n)=>span.style.background=n/5<progress?'var(--accent)':'#e6e5dc');
}
function renderPosition(){
  const total=duration(),fraction=Math.min(1,state.elapsed/total);$('time-remaining').textContent=formatTime(Math.max(0,total-state.elapsed));
  $('budget-count').replaceChildren(document.createTextNode(storyBudget(total-state.elapsed).toLocaleString()+' '));const unit=document.createElement('small');unit.textContent='chars';$('budget-count').append(unit);
  $('elapsed-time').textContent=formatTime(Math.min(state.elapsed,total));$('scrubber').value=String(Math.min(state.elapsed,total));
  // The track dots are equally spaced; interpolate the train between observed fixture stations.
  let leg=0;while(leg<state.stations.length-2&&state.elapsed>state.stations[leg+1].offset_s)leg++;
  const from=state.stations[leg].offset_s,to=state.stations[leg+1].offset_s,legFraction=Math.max(0,Math.min(1,(state.elapsed-from)/(to-from)));
  const railFraction=(leg+legFraction)/(state.stations.length-1);$('train-marker').style.left=`${railFraction*100}%`;$('rail-progress').style.width=`${railFraction*100}%`;
  document.querySelectorAll('.station').forEach(el=>el.classList.toggle('visited',state.elapsed>=Number(el.dataset.offset)));
  if(state.mode==='replay'&&fraction>=1&&!state.arrivalReached){state.arrivalReached=true;finishReplay();}else if(state.mode==='replay'&&fraction>=1&&!state.audio&&!state.finished)finishReplay();
}
function renderPlayback(){
  const playing=state.playing;$('play-button').disabled=state.mode!=='replay'||state.modelBusy;$('scrubber').disabled=state.mode!=='replay';$('restart-button').disabled=state.mode!=='replay';
  $('play-button').querySelector('span').textContent=state.modelBusy?'Planning…':playing?'Pause':state.finished?'Play again':state.elapsed>0?'Continue':'Start story';
  $('play-button').querySelector('svg').innerHTML=playing?'<path d="M4 3h3v10H4zm5 0h3v10H9z"/>':'<path d="m5 3 8 5-8 5z"/>';
  $('reading-indicator').classList.toggle('running',playing);const dot=document.createElement('i');$('reading-indicator').replaceChildren(dot,document.createTextNode(state.mode==='live'?'LIVE INSPECTION':playing?'THE STORY IS UNFOLDING':state.finished?'YOU HAVE ARRIVED':'READY WHEN YOU ARE'));
  $('audio-button').setAttribute('aria-pressed',String(state.audio));$('audio-button').querySelector('span').textContent=state.audio?'Sound on':'Sound off';
  $('audio-button').querySelector('svg').innerHTML=state.audio?'<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>':'<path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="m16 9 5 6m0-6-5 6"/>';
  $('timing-label').textContent=state.audio?'Browser speech · actual end event':'Virtual speech clock · text only';
  $('speed-control').querySelectorAll('button').forEach(button=>{const selected=Number(button.dataset.speed)===state.speed;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));button.disabled=state.mode!=='replay';});
}
function stationPlan(index){
  if(index===state.stationIndex)return;state.stationIndex=index;
  if(state.modelRun&&index<state.stations.length-1&&!state.modelBusy){replanConnected(false);return;}
  const left=state.stations.length-1-index,remaining=Math.max(0,duration()-state.elapsed);const budget=storyBudget(remaining);
  if(left===0){appendLog(isRecorded()?'Recorded station event reached. Comparing the scheduler with this known clock.':'Fixture station event reached. Comparing sentence end with this clock.','ARRIVE');return;}
  const op=index===0?'KEEP':index===1?'PROPOSE COMPRESS':index===2?'PROPOSE DROP':'KEEP';
  const description=op==='PROPOSE COMPRESS'?'propose a shorter bridge scene':op==='PROPOSE DROP'?'propose dropping an aside':'keep the ending in view';
  appendLog(`${left} ${left===1?'stop':'stops'} · ${formatTime(remaining)} · ${budget.toLocaleString()} chars; ${description}.`,op);
}
function tick(now){
  if(!state.playing)return;const dt=Math.max(0,Math.min(2,(now-state.lastTick)/1000));state.lastTick=now;state.elapsed+=dt*state.speed;
  if(state.audio){
    speakCurrent();
    if(state.elapsed>duration()+180&&state.lastSentenceEnd===null){invalidateSpeech('The browser did not complete the sentence stream within the speech timeout.');state.finished=true;state.playing=false;resetSpeech();showLanding();renderPlayback();}
  }else{
    const nextIndex=sampleSchedule(state.schedule,state.elapsed);
    if(nextIndex!==state.sentenceIndex){state.sentenceIndex=nextIndex;renderSentence();}
    if(state.elapsed>=state.schedule.at(-1).end&&state.lastSentenceEnd===null)state.lastSentenceEnd=state.schedule.at(-1).end;
  }
  let station=0;state.stations.forEach((s,i)=>{if(s.offset_s<=state.elapsed)station=i;});stationPlan(station);renderPosition();
  if(state.playing)state.frame=requestAnimationFrame(tick);
}
function finishReplay(){
  if(state.audio&&state.lastSentenceEnd===null){
    $('landing-result').hidden=false;$('landing-error').textContent='Pending';$('landing-label').textContent='SPEECH END NOT YET OBSERVED';$('landing-description').textContent=`The ${isRecorded()?'recorded':'synthetic'} station event has arrived. The speech clock continues until the browser completes the final sentence.`;
    return;
  }
  state.finished=true;state.playing=false;stopAnimation();showLanding();renderPlayback();
}
function showLanding(){
  $('landing-result').hidden=false;
  if(state.audio&&(!state.speechMeasurementValid||state.lastSentenceEnd===null)){$('landing-label').textContent='AUDIO LANDING ERROR';$('landing-error').textContent='Unavailable';$('landing-description').textContent=state.speechMeasurementReason||'No final speech-end event was observed. The virtual schedule is not substituted for an audio measurement.';return;}
  const end=state.lastSentenceEnd??state.schedule.at(-1).end;const error=end-duration();$('landing-label').textContent=state.audio?(isRecorded()?'SPEECH VS OBSERVATION':'BROWSER SPEECH VS FIXTURE'):(isRecorded()?'REPLAY SCHEDULE ERROR':'FIXTURE SCHEDULE ERROR');$('landing-error').textContent=`${error>=0?'+':'−'}${Math.abs(error).toFixed(1)} s`;
  $('landing-description').textContent=state.audio?`Uninterrupted browser speech-end timing vs a ${isRecorded()?'recorded observation':'synthetic event'}. The provider timestamp is not a door sensor; prospective arrival accuracy remains unmeasured.`:`By construction, the text scheduler targets three seconds before this ${isRecorded()?'known recorded observation':'synthetic event'}. This is not prospective ETA or real speech performance.`;
}
function speakCurrent(){
  if(!state.audio||state.speed!==1||!state.playing||state.utterance||!('speechSynthesis'in window))return;
  const index=state.lastSpoken+1;if(index>=state.lines.length||state.elapsed<state.schedule[index].start)return;
  const voices=window.speechSynthesis.getVoices(),lang=state.lang==='ko'?'ko':'en';const voice=voices.find(v=>v.lang.toLowerCase().startsWith(lang));
  if(!voice){invalidateSpeech('No matching language voice is available.');state.audio=false;resetSpeech();notice(`No ${state.lang==='ko'?'Korean':'English'} browser voice is available. Continuing with text only; audio is unmeasured.`);renderPlayback();return;}
  const epoch=state.audioEpoch,utterance=new SpeechSynthesisUtterance(state.lines[index]);
  utterance.voice=voice;utterance.lang=state.lang==='ko'?'ko-KR':'en-US';utterance.rate=1;state.utterance=utterance;state.lastSpoken=index;state.sentenceIndex=index;renderSentence();
  const startVirtual=state.elapsed,startActual=performance.now();
  const isCurrent=()=>epoch===state.audioEpoch&&state.utterance===utterance&&state.audio;
  utterance.onend=()=>{if(!isCurrent())return;state.utterance=null;if(index===state.lines.length-1){state.lastSentenceEnd=startVirtual+(performance.now()-startActual)/1000;if(state.arrivalReached){state.finished=true;state.playing=false;stopAnimation();showLanding();renderPlayback();}}else if(state.playing)speakCurrent();};
  utterance.onerror=(event)=>{if(!isCurrent())return;state.utterance=null;invalidateSpeech(`Browser speech failed (${event.error||'unknown'}). Restart for a continuous measurement.`);appendLog(`Browser speech failed (${event.error||'unknown'}). Audio landing error unavailable.`,'TTS');notice('The browser could not complete speech. Text replay remains available; audio timing is unmeasured.');if(state.arrivalReached){state.finished=true;state.playing=false;stopAnimation();showLanding();renderPlayback();}};
  window.speechSynthesis.speak(utterance);
}
function seek(seconds){
  if(state.modelRun||state.modelBusy){stopModelRun();state.generated=false;state.lines=authoredStory(state.lang,exitName());state.schedule=makeSchedule(state.lines,duration());notice('Scrubbing returned to the authored story. Existing API receipts are retained.');}
  const wasPlaying=state.playing;stopAnimation();resetSpeech();state.playing=false;state.elapsed=Math.max(0,Math.min(duration(),Number(seconds)||0));state.finished=false;state.arrivalReached=false;state.lastSentenceEnd=null;invalidateSpeech('The replay was scrubbed. Restart at 1× with sound for a continuous measurement.');state.stationIndex=-1;state.sentenceIndex=sampleSchedule(state.schedule,state.elapsed);$('landing-result').hidden=true;
  appendLog(`Replay moved to ${formatTime(state.elapsed)}. Speech callbacks reset.`,'SEEK');renderSentence();renderPosition();renderPlayback();if(wasPlaying&&!state.finished)setPlaying(true);
}
function toggleAudio(){
  if(state.mode==='live'){toggleLiveAudio();return;}
  if(state.modelRun||state.modelBusy){notice('Connected-model replay currently uses text and a virtual speech clock. Return to the authored story for browser speech.');return;}
  if(!('speechSynthesis'in window)||!('SpeechSynthesisUtterance'in window)){notice('No browser speech engine is available. Text-only replay uses a virtual clock.');appendLog('tts=none · browser speech is unavailable.','TTS');return;}
  if(!state.audio){const prefix=state.lang==='ko'?'ko':'en';if(!window.speechSynthesis.getVoices().some(v=>v.lang.toLowerCase().startsWith(prefix))){notice(`No ${state.lang==='ko'?'Korean':'English'} browser voice is available. Text-only replay remains enabled; audio is unmeasured.`);appendLog('tts=none · no matching language voice.','TTS');return;}}
  state.audio=!state.audio;resetSpeech();state.lastSentenceEnd=null;
  if(state.audio){state.speed=1;state.speechMeasurementValid=state.elapsed===0;state.speechMeasurementReason=state.speechMeasurementValid?'':'Sound began partway through the story. Restart at 1× with sound for a continuous measurement.';notice('Sound uses normal speed. Restart the story for an uninterrupted speech measurement; replay arrival is known in advance.');if(state.playing){state.lastSpoken=state.sentenceIndex-1;speakCurrent();}}else{invalidateSpeech('Audio was turned off before a continuous measurement completed.');notice('');}renderPlayback();
}
function setLanguage(lang){if(state.lang===lang)return;if(state.mode==='live')stopLiveStory('Language changed. Start a new live story when ready.');state.lang=lang;if(state.audio&&!window.speechSynthesis.getVoices().some(v=>v.lang.toLowerCase().startsWith(lang))){state.audio=false;notice('No matching browser voice. Text-only replay remains available.');}$('lang-en').classList.toggle('selected',lang==='en');$('lang-ko').classList.toggle('selected',lang==='ko');$('lang-en').setAttribute('aria-pressed',String(lang==='en'));$('lang-ko').setAttribute('aria-pressed',String(lang==='ko'));document.documentElement.lang=lang;resetReplay();notice(lang==='ko'?'한국어 대본은 사람이 쓴 예시입니다. 실제 한국어 모델 실행은 아직 측정하지 않았습니다.':'English text is an authored fixture. No Writer model was run.');}

function apiUrl(path){return `${state.apiBase}${path}`;}
async function requestApi(path,{method='GET',body,signal,timeoutMs}={}){
  const controller=new AbortController();if(signal?.aborted)controller.abort();const timeout=timeoutMs??(path.startsWith('/api/plan')?90000:path.startsWith('/api/write')?45000:25000);const timer=setTimeout(()=>controller.abort(),timeout);const abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});const started=performance.now();let sent=false;
  try{const headers={'Accept':'application/json'};if(body)headers['Content-Type']='application/json';if(state.apiToken)headers.Authorization=`Bearer ${state.apiToken}`;
    if(controller.signal.aborted)throw new DOMException('Request canceled before dispatch','AbortError');sent=true;
    const response=await fetch(apiUrl(path),{method,headers,body:body?JSON.stringify(body):undefined,signal:controller.signal,credentials:'omit',cache:'no-store'});
    if(!(response.headers.get('content-type')||'').includes('application/json'))throw Error('No Worker JSON service is available at this address.');
    const data=await response.json();if(!response.ok){addReceipt(data,`${path} · HTTP ${response.status}`);const error=Error(data.reason||data.message||data.error?.message||data.error||`Service returned HTTP ${response.status}`);error.apiData=data;error.receiptRecorded=true;throw error;}return data;
  }catch(error){
    if(sent&&!error.receiptRecorded&&/^\/api\/(plan|write|fact)/.test(path)){addReceipt({model:null,usage:null,cost_usd:null,latency_ms:performance.now()-started,mode:'outcome-unknown'},`${path} · ${error.name==='AbortError'?'canceled/timeout':'network error'}`);error.message=`${error.message} Provider execution and cost are unknown; check the Worker reservation ledger before retrying.`;}
    throw error;
  }finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
}
function addReceipt(data,label){
  if(!data||typeof data!=='object')return;state.receipts.unshift({label,model:data.model,usage:data.usage,cost:data.cost_usd,latency:data.latency_ms,mode:data.mode,fact:data.fact});state.receipts=state.receipts.slice(0,50);$('call-count').textContent=`${state.receipts.length} SERVICE ${state.receipts.length===1?'EVENT':'EVENTS'}`;
  $('receipt-list').replaceChildren(...state.receipts.map(item=>{const row=document.createElement('div');row.className='receipt';const title=document.createElement('strong');title.textContent=item.model?`${item.label} · ${item.model}`:`${item.label} · ${item.mode||'service'}`;const metrics=document.createElement('small');
    const tokens=item.usage?.total_tokens??(Number.isFinite(item.usage?.prompt_tokens)&&Number.isFinite(item.usage?.completion_tokens)?item.usage.prompt_tokens+item.usage.completion_tokens:null);
    for(const value of [tokens===null?'tokens: n/a':`${tokens} tokens`,Number.isFinite(item.cost)?`$${item.cost.toFixed(6)}`:'cost: unreported',Number.isFinite(item.latency)?`${Math.round(item.latency)} ms`:'latency: unreported']){const part=document.createElement('span');part.textContent=value;metrics.append(part);}row.append(title,metrics);if(item.fact?.text&&item.fact?.url){try{const url=new URL(item.fact.url);if(url.protocol==='https:'){const factText=document.createElement('p');factText.textContent=Array.from(item.fact.text).slice(0,140).join('');const link=document.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Source fact ↗';row.append(factText,link);}}catch{}}return row;}));
}
async function refreshLive(){
  if(state.mode!=='live')return;if(!state.live.active){state.live.active=true;state.live.epoch++;}await pollLive();
}
async function setMode(mode){
  if(state.mode===mode)return;cancelConnected();state.requestEpoch++;if(state.playing)setPlaying(false);else resetSpeech();state.mode=mode;
  $('replay-mode').classList.toggle('selected',mode==='replay');$('replay-mode').setAttribute('aria-pressed',String(mode==='replay'));$('live-mode').classList.toggle('selected',mode==='live');$('live-mode').setAttribute('aria-pressed',String(mode==='live'));$('live-panel').hidden=mode!=='live';
  if(state.wakeLock){try{await state.wakeLock.release();}catch{}state.wakeLock=null;}
  $('source-select').parentElement.parentElement.hidden=mode==='live';$('exit-select').parentElement.hidden=mode==='live';document.querySelector('.control-arrow').hidden=mode==='live';$('generate-button').hidden=mode==='live';
  if(mode==='live'){notice('Choose your actual train and direction. Live forecasts require a fresh arrival anchor; live model execution remains unmeasured.');refreshLive();}else{notice('');resetReplay();$('model-state').textContent='Authored story active · model replanning off';}renderPlayback();
}
function openSettings(){$('api-url').value=state.apiBase;$('api-token').value=state.apiToken;$('connection-dialog').showModal();}
function setConnection(event){event.preventDefault();const raw=$('api-url').value.trim();let base='';if(raw){try{const u=new URL(raw);if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash)throw Error();if(u.protocol==='http:'&&!['localhost','127.0.0.1','[::1]'].includes(u.hostname))throw Error();base=u.origin+u.pathname.replace(/\/+$/,'');}catch{notice('Use an HTTPS Worker URL, or localhost for local development, without credentials or query parameters.');return;}}
  cancelConnected();state.requestEpoch++;state.apiBase=base;state.apiToken=$('api-token').value.trim();$('api-token').value='';$('connection-dialog').close();notice('Connection saved in this tab’s memory. Replay still makes no inference calls.');if(state.mode==='live')refreshLive();
}

function liveTrainKey(train){const direction=String(train.updnLine??'');return ['0','1'].includes(direction)&&train.trainNo!=null?`${train.trainNo}|${direction}`:'';}
function liveAnchorKey(eta=state.live.eta){const a=eta?.anchor;return a?.verified?`${a.trainNo}|${a.direction}|${a.station}|${a.recptnDt}`:'';}
function invalidateLivePoll(){const live=state.live;live.epoch++;live.controller?.abort();live.controller=null;live.polling=false;clearTimeout(live.timer);live.timer=0;}
function stopLiveMonitoring(reason='Live monitoring stopped.'){
  const live=state.live;if(!live)return;live.active=false;invalidateLivePoll();if(live.storyActive||live.modelBusy)stopLiveStory(reason);
}
function stopLiveSpeech(){const live=state.live;live.speechEpoch++;live.utterance=null;if('speechSynthesis'in window)window.speechSynthesis.cancel();live.textEndAt=0;}
function stopLiveStory(reason='Live story stopped.'){
  const live=state.live;live.storyEpoch++;live.modelController?.abort();live.modelController=null;live.modelBusy=false;live.storyActive=false;live.pendingAnchor=null;live.pendingText=null;live.heldEnding=false;live.continuousAudio=false;stopLiveSpeech();if(live.frame)cancelAnimationFrame(live.frame);live.frame=0;
  if(state.mode==='live'){if(reason)$('live-status').textContent=reason;renderLiveControls();$('reading-indicator').classList.remove('running');$('reading-indicator').textContent='LIVE STORY STOPPED';}
}
function currentLiveRemaining(){
  const live=state.live,eta=live.eta;if(!eta?.eta_available||!Number.isFinite(eta.remaining_s))return null;
  if(eta.valid_until&&Number.isFinite(Date.parse(eta.valid_until))&&Date.now()>Date.parse(eta.valid_until))return null;
  return Math.max(0,eta.remaining_s-(live.etaResponseLagS||0)-(performance.now()-live.etaReceivedAt)/1000);
}
function renderLiveControls(){
  const live=state.live,remaining=currentLiveRemaining();const supported=live.eta?.horizon_supported!==false&&live.eta?.within_evaluated_horizon!==false&&Number(live.eta?.stations_left)>=3&&Number(live.eta?.stations_left)<=10;
  $('live-start').disabled=live.storyActive||live.modelBusy||!live.status?.inference_enabled||!live.status?.eta_model_configured||!live.eta?.anchor?.verified||!live.to||remaining===null||remaining<25||!supported;
  $('live-stop').hidden=!live.storyActive&&!live.modelBusy;
}
function renderLiveForecast(){
  const live=state.live,eta=live.eta,remaining=currentLiveRemaining();
  if(remaining===null){$('live-forecast').textContent=eta?.reason?`Forecast unavailable: ${eta.reason.replaceAll('_',' ')}.`:'A fresh observed arrival anchor and a validated route model are required.';renderLiveControls();return;}
  const age=Math.max(0,Number(eta.anchor_age_s||0)+(live.etaResponseLagS||0)+(performance.now()-live.etaReceivedAt)/1000);const fallback=Array.isArray(eta.fallback_segments)?eta.fallback_segments.length:0;
  $('live-forecast').textContent=live.arrival?`Arrival observed at ${live.to}. Door-opening time is unmeasured.`:`${formatTime(remaining)} estimated · ${eta.stations_left} stops · anchor ${Math.round(age)} s old${fallback?` · ${fallback} fallback segments`:''}${Number(eta.stations_left)<3?' · outside the evaluated 3–10-stop horizon':''}`;
  $('live-disclosure').textContent=`Experimental ETA from recorded station observations. Model evaluation: ${eta.evaluation?.n??'unreported'} holdout predictions; median relative error ${Number.isFinite(eta.evaluation?.median_relative_error)?(eta.evaluation.median_relative_error*100).toFixed(1)+'%':'unreported'}. Poll interval 20 s; provider lag and door-opening offset are unmeasured. Live wall-clock time continues during generation. Prospective live narration accuracy has not been validated.`;
  if(live.storyActive){$('time-remaining').textContent=formatTime(remaining);$('budget-count').replaceChildren(document.createTextNode(storyBudget(remaining).toLocaleString()+' '));const unit=document.createElement('small');unit.textContent='chars';$('budget-count').append(unit);$('arrival-time').textContent=formatTime(remaining);$('elapsed-time').textContent=formatTime((performance.now()-live.startedAt)/1000);$('timing-label').textContent=state.audio?'Live wall clock · browser speech':'Live wall clock · virtual text timing';}
  renderLiveControls();
}
function renderLiveRoute(){
  const live=state.live,route=live.eta?.route;if(live.arrival){$('route-title').textContent=`${live.to} · arrival observed`;$('rail-progress').style.width='100%';$('train-marker').style.left='100%';return;}if(!Array.isArray(route)||route.length<2)return;
  $('line-roundel').textContent=state.journey.line.replace('호선','');$('route-title').textContent=`${live.eta.anchor.station} → ${live.to}`;$('arrival-kind').textContent='EXPERIMENTAL ETA';$('duration-time').textContent='LIVE';$('scrubber').value='0';$('rail-progress').style.width='0%';$('train-marker').style.left='0%';
  const shown=route.length<=5?route:[route[0],route[Math.floor((route.length-1)/3)],route[Math.floor(2*(route.length-1)/3)],route.at(-1)];
  $('station-dots').replaceChildren(...shown.map((name,i)=>{const el=document.createElement('div');el.className='station'+(i===0?' visited':'')+(i===shown.length-1?' exit':'');const dot=document.createElement('span');dot.className='dot';const label=document.createElement('span');label.className='station-name';label.textContent=name;if(i===0){const cap=document.createElement('span');cap.className='exit-caption';cap.textContent='OBSERVED ANCHOR';label.append(cap);}el.append(dot,label);return el;}));
}
async function pollLive(){
  const live=state.live;if(state.mode!=='live'||!live.active||document.hidden)return;if(live.polling){live.refreshPending=true;return;}clearTimeout(live.timer);live.polling=true;const epoch=live.epoch;live.controller=new AbortController();const signal=live.controller.signal;$('refresh-live').disabled=true;
  const valid=()=>epoch===live.epoch&&live.active&&state.mode==='live';
  try{
    const status=await requestApi('/api/status',{signal});if(!valid())return;live.status=status;
    if(!status.position_enabled){$('live-status').textContent='Live positions are disabled. Configure the Seoul service and access token in the Worker; replay remains available.';live.eta=null;renderLiveForecast();return;}
    const data=await requestApi(`/api/position?line=${encodeURIComponent(state.journey.line)}`,{signal});if(!valid())return;addReceipt(data,'Live Seoul positions');
    if(data.mode!=='live'){const reason=data.reason||data.mode;live.eta=null;if(data.mode==='replay-forced'){await setMode('replay');notice(`Live service requires replay (${reason}). Switched to the recorded/authored replay; no live timing was inferred.`);}else{$('live-status').textContent=`Live positions unavailable: ${reason}.`;if(live.storyActive||live.modelBusy)stopLiveStory('Live positions unavailable; story stopped.');renderLiveForecast();}return;}
    live.positions=Array.isArray(data.positions)?data.positions.filter(train=>liveTrainKey(train)):[];
    const select=$('train-select');const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Choose your actual train and direction';select.replaceChildren(placeholder,...live.positions.map(train=>{const option=document.createElement('option');option.value=liveTrainKey(train);option.textContent=`Train ${train.trainNo} · ${train.statnNm||'station unknown'} · direction ${train.updnLine}`;return option;}));
    if(live.selectedKey&&!live.positions.some(train=>liveTrainKey(train)===live.selectedKey)){const option=document.createElement('option');option.value=live.selectedKey;option.textContent=`Train ${live.selectedKey.replace('|',' · direction ')} · absent from latest sample`;select.append(option);}select.value=live.selectedKey;select.disabled=!live.positions.length&&!live.selectedKey;
    if(!live.selectedKey){$('live-status').textContent=`${live.positions.length} sampled trains. Confirm your actual train and direction; no train is selected automatically.`;live.eta=null;renderLiveForecast();return;}
    if(!status.eta_model_configured){if(live.storyActive||live.modelBusy)stopLiveStory('The validated ETA artifact is unavailable; story stopped.');$('live-status').textContent='Train positions are available; the validated, completed ETA artifact is not ready. A live story cannot start.';live.eta=null;renderLiveForecast();return;}
    const [trainNo,direction]=live.selectedKey.split('|');const query=new URLSearchParams({line:state.journey.line,trainNo,direction});if(live.to)query.set('to',live.to);
    const eta=await requestApi(`/api/eta?${query}`,{signal});if(!valid())return;live.eta=eta;live.etaReceivedAt=performance.now();const generatedAt=Date.parse(eta.generated_at);live.etaResponseLagS=Number.isFinite(generatedAt)?Math.max(0,(Date.now()-generatedAt)/1000):0;
    const choices=Array.isArray(eta.eligible_exits)?eta.eligible_exits.filter(exit=>typeof exit.station==='string'&&Number.isInteger(exit.stations_left)&&exit.stations_left>=3&&exit.stations_left<=10&&exit.horizon_supported!==false):[];
    const exits=$('live-exit-select');const choose=document.createElement('option');choose.value='';choose.textContent='Choose 3–10 stops ahead';exits.replaceChildren(choose,...choices.map(exit=>{const option=document.createElement('option');option.value=exit.station;option.textContent=`${exit.station} · ${exit.stations_left} stops`;return option;}));
    if(live.to&&!choices.some(exit=>exit.station===live.to)){const option=document.createElement('option');option.value=live.to;option.textContent=`${live.to} · active destination`;exits.append(option);}exits.value=live.to;exits.disabled=!eta.anchor?.verified||(!choices.length&&!live.to);
    if(!eta.eta_available){if(eta.reason!=='choose_exit'&&(live.storyActive||live.modelBusy))stopLiveStory(`Live story stopped: ${String(eta.reason||'forecast unavailable').replaceAll('_',' ')}.`);$('live-status').textContent=eta.reason==='choose_exit'?`Arrival anchor verified at ${eta.anchor?.station}. Choose your exit from the forward route.`:`Forecast unavailable: ${String(eta.reason||'unverified anchor').replaceAll('_',' ')}. No uniform or synthetic ETA is substituted.`;renderLiveForecast();return;}
    $('live-status').textContent=`Train ${trainNo} · direction ${direction}${eta.anchor.terminus?.station?` · terminates at ${eta.anchor.terminus.station}`:''} · observed ${eta.anchor.station} at ${eta.anchor.recptnDt}. ${live.storyActive?'Live story active; model requests follow new arrival anchors.':'Ready for an experimental live story when model access is configured.'}`;
    const arrived=eta.anchor?.verified&&eta.anchor.trainSttus==='1'&&eta.anchor.station===live.to&&eta.remaining_s===0;
    if(arrived){live.arrival={...eta.anchor};live.arrivalReceivedAt=Date.now();live.active=false;clearTimeout(live.timer);live.modelController?.abort();live.pendingAnchor=null;if(!live.sentences.length&&!live.utterance&&!live.textEndAt)endLiveWithoutOutput();notice(`Arrival observed at ${live.to}. This station event is a position proxy, not a door-opening measurement.`);showLiveLanding();}
    if(live.storyActive){renderLiveRoute();const anchorKey=liveAnchorKey(eta);if(live.endingCompleted&&!arrived&&anchorKey&&anchorKey!==live.endingAnchorKey&&anchorKey!==live.endingForecastChanges.at(-1)?.anchorKey){const remaining=currentLiveRemaining();live.endingForecastChanges.push({anchorKey,remaining_s:remaining,observed_at:Date.now()});live.endingForecastChanges=live.endingForecastChanges.slice(-20);appendLog(`The exit sentence is already complete. Updated ETA is ${remaining===null?'unavailable':formatTime(remaining)}; a second exit cue will not be read.`,remaining!==null&&remaining>30?'EARLY END':'ETA CHANGED');}if(!arrived&&!live.endingStarted&&!live.endingCompleted&&anchorKey&&anchorKey!==live.lastPlannedAnchor){if(live.modelBusy)live.pendingAnchor=anchorKey;else void liveModelRound(false);}}
    renderLiveForecast();
    if(live.storyActive&&'wakeLock'in navigator&&!state.wakeLock){try{state.wakeLock=await navigator.wakeLock.request('screen');}catch{notice('Screen Wake Lock is unavailable. Keep this page visible for the live controller.');}}
  }catch(error){if(!valid())return;$('live-status').textContent=`Position/ETA refresh failed: ${error.message} No fresh arrival event was inferred.`;renderLiveForecast();}
  finally{if(epoch===live.epoch){live.polling=false;$('refresh-live').disabled=false;if(live.active&&state.mode==='live'&&!document.hidden){const delay=live.refreshPending?0:20000;live.refreshPending=false;live.timer=setTimeout(()=>void pollLive(),delay);}}}
}
function validLiveStory(epoch){return epoch===state.live.storyEpoch&&state.live.storyActive&&state.mode==='live';}
async function startLiveStory(){
  const live=state.live,remaining=currentLiveRemaining();if(live.storyActive||live.modelBusy)return;
  if(!live.eta?.anchor?.verified||live.eta?.horizon_supported===false||live.eta?.within_evaluated_horizon===false||remaining===null||remaining<25||!live.to||Number(live.eta.stations_left)<3||Number(live.eta.stations_left)>10){notice('Choose a fresh, verified train anchor and an exit 3–10 stops ahead before starting.');return;}
  const epoch=++live.storyEpoch;live.modelController?.abort();live.modelController=new AbortController();live.modelBusy=true;renderLiveControls();
  try{
    const status=await requestApi('/api/status',{signal:live.modelController.signal});if(epoch!==live.storyEpoch||state.mode!=='live')return;live.status=status;
    if(!status.inference_enabled||!status.eta_model_configured||!Number.isFinite(status.limits?.completion_calls_remaining)||status.limits.completion_calls_remaining<4||!Number.isFinite(status.limits?.reserved_usd)||!Number.isFinite(status.limits?.reservation_budget_usd)||status.limits.reservation_budget_usd>3||status.limits.reserved_usd>=status.limits.reservation_budget_usd)throw Error('Authenticated model access, a completed ETA artifact, and budget for up to four completion attempts are required.');
    live.storyActive=true;live.startedAt=performance.now();live.startedWall=Date.now();live.sentences=[];live.sentenceIndex=0;live.pendingText=null;live.arrival=null;live.lastSentenceEndWall=null;live.lastEndKind=null;live.lastPlannedAnchor='';live.pendingAnchor=null;live.heldEnding=false;live.endingStarted=false;live.endingCompleted=false;live.hasReadSentence=false;live.endingForecastChanges=[];live.endingAnchorKey='';live.continuousAudio=state.audio&&matchingVoice()!=null;
    if(state.audio&&!matchingVoice()){state.audio=false;notice('No matching browser voice. Live text uses virtual sentence timing; speech performance is unavailable.');}
    $('story-title').textContent='LIVE STORY · WAITING FOR WRITER';$('sentence').textContent='Preparing a story from the verified train anchor…';$('sentence').lang=state.lang;$('text-provenance').textContent='Waiting for actual model output · no story fabricated';$('chapter-label').textContent='LIVE / WALL CLOCK CONTINUES';$('landing-result').hidden=true;renderLiveRoute();live.frame=requestAnimationFrame(liveTick);
    if(status.tavily_enabled){const fact=await requestApi(`/api/fact?station=${encodeURIComponent(live.to)}`,{signal:live.modelController.signal});addReceipt(fact,epoch===live.storyEpoch?'Live Tavily fact':'Live Tavily fact · late response');if(!validLiveStory(epoch))return;live.fact=fact.fact||null;}else live.fact=null;
    live.modelBusy=false;await liveModelRound(true);
  }catch(error){if(epoch!==live.storyEpoch)return;stopLiveStory(`Live story could not start: ${error.message}`);notice('Live generation did not complete. No success or model output was substituted. Existing receipts remain visible.');}
  finally{if(epoch===live.storyEpoch){live.modelBusy=false;renderLiveControls();}}
}
async function liveModelRound(initial=false){
  const live=state.live;if(!live.storyActive||live.modelBusy||live.arrival||live.endingStarted||live.endingCompleted)return;const remaining=currentLiveRemaining();if(remaining===null||!live.eta?.anchor?.verified){appendLog('Live model planning waits for a fresh validated ETA anchor.','WAIT');return;}
  const epoch=live.storyEpoch,anchorKey=liveAnchorKey(),[trainNo,direction]=live.selectedKey.split('|');live.modelBusy=true;live.lastPlannedAnchor=anchorKey;live.pendingAnchor=null;renderLiveControls();const signal=live.modelController?.signal;
  try{
    const planResult=await requestApi('/api/plan',{method:'POST',signal,body:{current_station:live.eta.anchor.station,exit_station:live.to,stations_left:live.eta.stations_left,remaining_s:remaining,elapsed_story_s:(performance.now()-live.startedAt)/1000,eta_source:'recorded-model',train_anchor:{line:state.journey.line,trainNo,direction,to:live.to},remaining_scenes:[{id:'remaining-story',chars:live.sentences.slice(live.sentenceIndex).join('').length}]}});addReceipt(planResult,validLiveStory(epoch)?'Live Conductor':'Live Conductor · late response');if(!validLiveStory(epoch)||live.arrival||live.endingStarted||live.endingCompleted)return;
    if(anchorKey!==liveAnchorKey()){live.pendingAnchor=liveAnchorKey();appendLog('A new station anchor arrived during planning. Keeping its clock and requesting a fresh plan.','STALE PLAN');return;}
    const plan=planResult.plan;if(!plan||!Number.isFinite(plan.budget_chars)||typeof plan.log!=='string')throw Error('The live Conductor returned an invalid plan.');appendLog(plan.log,'LIVE NEMOTRON',(performance.now()-live.startedAt)/1000);
    if(!initial&&!plan.ops?.length)return;const nowRemaining=currentLiveRemaining();if(nowRemaining===null||nowRemaining<15)return;const budget=Math.min(1800,Math.floor(plan.budget_chars),storyBudget(nowRemaining));if(budget<40)return;
    const context=Array.from(`Continue the live Seoul train story without repeating spoken lines. Read: ${live.sentences.slice(0,live.sentenceIndex+(live.heldEnding?0:1)).join(' ').slice(-140)}. Remaining: ${live.sentences.slice(live.sentenceIndex+1).join(' ').slice(0,100)}. Proposals: ${(plan.ops||[]).map(op=>`${op.op}:${op.scene}`).join('; ').slice(0,120)}. Rewrite the remaining envelope story and end at the exit.`).slice(0,500).join('');
    const written=await requestApi('/api/write',{method:'POST',signal,body:{lang:state.lang,exit_station:live.to,budget_chars:budget,is_last_scene:true,fact:live.fact,scene:context}});addReceipt(written,validLiveStory(epoch)?'Live Writer':'Live Writer · late response');if(!validLiveStory(epoch)||live.arrival||live.endingStarted||live.endingCompleted)return;
    if(anchorKey!==liveAnchorKey()){live.pendingAnchor=liveAnchorKey();appendLog('Writer completed for an older station anchor. Output was not applied.','STALE TEXT');return;}
    if(!Array.isArray(written.sentences)||!written.sentences.length||!written.sentences.every(text=>typeof text==='string'))throw Error('The live Writer returned no valid sentence stream.');
    const usableRemaining=currentLiveRemaining();if(usableRemaining===null||usableRemaining<5){appendLog('Writer completed after the validated live timing window. Output was discarded; usage remains in Receipts.','EXPIRED TEXT');return;}
    live.pendingText={sentences:written.sentences,model:written.model,anchorKey,storyEpoch:epoch};if(!live.utterance&&!live.textEndAt)applyPendingLiveText();else appendLog('New Writer text queued for the next sentence boundary. The live clock keeps moving.','QUEUED');
  }catch(error){if(!validLiveStory(epoch)||live.endingStarted||live.endingCompleted)return;appendLog(`Live model request stopped: ${error.message}`,'FAILED');$('live-status').textContent='A live model request failed. Last successful text is retained; receipts include reported or unknown usage.';}
  finally{if(epoch===live.storyEpoch){live.modelBusy=false;renderLiveControls();if(live.storyActive&&!live.arrival&&!live.endingStarted&&!live.endingCompleted&&live.pendingAnchor&&live.pendingAnchor!==live.lastPlannedAnchor)void liveModelRound(false);}}
}
function matchingVoice(){if(!('speechSynthesis'in window))return null;return window.speechSynthesis.getVoices().find(voice=>voice.lang.toLowerCase().startsWith(state.lang==='ko'?'ko':'en'))||null;}
function applyPendingLiveText(){
  const live=state.live;if(!live.pendingText||!live.storyActive||live.arrival)return false;if(live.endingStarted||live.endingCompleted){live.pendingText=null;appendLog('The exit sentence is committed; later Writer text was discarded. Usage remains in Receipts.','ENDING CLOSED');return false;}const next=live.pendingText;live.pendingText=null;if(next.anchorKey!==liveAnchorKey()||next.storyEpoch!==live.storyEpoch){appendLog('Queued Writer text belongs to an older station or story; it was discarded at the sentence boundary.','STALE QUEUE');return false;}const usableRemaining=currentLiveRemaining();if(usableRemaining===null||usableRemaining<5){appendLog('Queued Writer text expired before the sentence boundary. Existing text is retained; usage remains in Receipts.','EXPIRED QUEUE');return false;}live.sentences=next.sentences;live.sentenceIndex=0;live.currentModel=next.model;live.heldEnding=false;live.lastSentenceEndWall=null;live.lastEndKind=null;$('text-provenance').textContent=`${next.model||'Connected Writer'} · actual response · experimental live ETA`;$('story-title').textContent=state.lang==='ko'?'실시간 열차 이야기':'LIVE TRAIN STORY';$('model-state').textContent='Connected Live Conductor · actual responses in Receipts';document.querySelector('.outline-badge').textContent='LIVE MODEL';document.querySelector('.conductor-explainer').textContent='New arrival anchors trigger model plans. Writer changes wait for the current sentence to finish; wall-clock time keeps moving.';startLiveSentence();return true;
}
function renderLiveSentence(){const live=state.live;$('text-provenance').textContent=`${live.currentModel||'Connected Writer'} · actual response · experimental live ETA`;$('sentence').textContent=live.sentences[live.sentenceIndex]||'';$('sentence').lang=state.lang;$('sentence-counter').textContent=`${String(live.sentenceIndex+1).padStart(2,'0')} / ${String(live.sentences.length).padStart(2,'0')}`;$('chapter-label').textContent='LIVE / WALL CLOCK CONTINUES';}
function startLiveSentence(){
  const live=state.live;if(!live.storyActive||live.utterance||live.textEndAt||live.endingCompleted||live.sentenceIndex>=live.sentences.length)return;const text=live.sentences[live.sentenceIndex];if(live.sentenceIndex===live.sentences.length-1&&!live.endingStarted){const remaining=currentLiveRemaining();if(remaining===null){stopLiveForExpiredAnchor();return;}const finalDuration=Math.max(1.5,Array.from(text).length/4.51);if(!live.arrival&&remaining>finalDuration+3){live.heldEnding=true;$('chapter-label').textContent='LIVE / ENDING HELD FOR YOUR EXIT';if(!live.hasReadSentence){$('sentence').textContent=state.lang==='ko'?'마지막 문장은 내릴 때까지 기다립니다.':'The last line is waiting for your stop.';$('text-provenance').textContent='System timing status · exit sentence not shown or spoken';}return;}live.heldEnding=false;live.endingStarted=true;live.pendingText=null;live.pendingAnchor=null;}live.hasReadSentence=true;renderLiveSentence();const voice=state.audio?matchingVoice():null;
  if(state.audio&&voice&&'SpeechSynthesisUtterance'in window){const epoch=live.speechEpoch,utterance=new SpeechSynthesisUtterance(text);utterance.voice=voice;utterance.lang=state.lang==='ko'?'ko-KR':'en-US';live.utterance=utterance;const current=()=>epoch===live.speechEpoch&&live.utterance===utterance&&live.storyActive;
    utterance.onend=()=>{if(!current())return;live.utterance=null;advanceLiveSentence('browser-speech-end');};
    utterance.onerror=(event)=>{if(!current())return;live.utterance=null;live.continuousAudio=false;state.audio=false;appendLog(`Live speech failed (${event.error||'unknown'}). Continuing with explicit text timing.`,'TTS');notice('Live speech failed. Audio arrival error is unavailable; text timing is virtual.');live.textEndAt=performance.now()+Math.max(1.5,Array.from(text).length/4.51)*1000;renderPlayback();};
    window.speechSynthesis.speak(utterance);
  }else{if(state.audio){state.audio=false;live.continuousAudio=false;notice('No matching language voice. The live story uses virtual text timing; speech performance is unavailable.');}live.textEndAt=performance.now()+Math.max(1.5,Array.from(text).length/4.51)*1000;}
}
function advanceLiveSentence(kind){
  const live=state.live;live.textEndAt=0;if(!live.storyActive)return;
  if(live.sentenceIndex===live.sentences.length-1){live.lastSentenceEndWall=Date.now();live.lastEndKind=kind;live.endingStarted=true;live.endingCompleted=true;live.endingAnchorKey=liveAnchorKey();live.heldEnding=false;live.sentenceIndex=live.sentences.length;live.pendingText=null;live.pendingAnchor=null;live.modelController?.abort();appendLog('The exit sentence is complete. Waiting for the observed target arrival; no second exit cue or model round will run.','ENDING COMPLETE');if(live.arrival)showLiveLanding();return;}
  if(live.pendingText&&!live.arrival&&applyPendingLiveText())return;
  live.sentenceIndex++;startLiveSentence();
}
function stopLiveForExpiredAnchor(){
  stopLiveStory('The validated live ETA anchor expired. Story and model requests stopped; refresh positions before starting again.');$('landing-result').hidden=false;$('landing-label').textContent='LIVE TIMING';$('landing-error').textContent='Anchor expired';$('landing-description').textContent='No fresh validated arrival forecast remains. Narration stopped, and no arrival error or substitute ending was invented.';
}
function liveTick(){
  const live=state.live;if(!live.storyActive||state.mode!=='live')return;if(currentLiveRemaining()===null){stopLiveForExpiredAnchor();return;}renderLiveForecast();if(live.heldEnding&&!live.utterance&&!live.textEndAt){if(!live.pendingText||!applyPendingLiveText())startLiveSentence();}if(live.textEndAt&&performance.now()>=live.textEndAt)advanceLiveSentence('virtual-text-timing');
  const indicator=$('reading-indicator');indicator.classList.add('running');indicator.textContent=live.endingCompleted?'ENDING COMPLETE · WAITING FOR ARRIVAL':live.heldEnding?'LIVE · ENDING HELD FOR YOUR EXIT':live.modelBusy?'LIVE · GENERATING':live.utterance?'LIVE · SPEAKING':live.textEndAt?'LIVE · TEXT CLOCK':'LIVE · WAITING FOR STATION';
  if(live.arrival&&live.lastSentenceEndWall===null&&Date.now()-(live.arrivalReceivedAt||Date.now())>180000){stopLiveStory('No final speech event was observed within the post-arrival timeout.');$('landing-result').hidden=false;$('landing-label').textContent='LIVE TIMING';$('landing-error').textContent='Unavailable';$('landing-description').textContent='The sentence stream did not complete after the station event. No substitute end time was invented.';return;}
  if(live.arrival&&live.lastSentenceEndWall!==null){showLiveLanding();live.storyActive=false;renderLiveControls();return;}
  live.frame=requestAnimationFrame(liveTick);
}
function endLiveWithoutOutput(){
  const live=state.live;live.storyEpoch++;live.modelController?.abort();live.modelBusy=false;live.storyActive=false;live.pendingText=null;live.pendingAnchor=null;live.continuousAudio=false;if(live.frame)cancelAnimationFrame(live.frame);live.frame=0;renderLiveControls();
}
function showLiveLanding(){
  const live=state.live;if(!live.arrival)return;$('landing-result').hidden=false;const epoch=Number(live.arrival.epoch_s);const validTime=Number.isFinite(epoch)&&epoch>0;
  if(live.lastSentenceEndWall===null){$('landing-label').textContent='STATION ARRIVAL OBSERVED';const noOutput=!live.sentences.length&&!live.utterance&&!live.textEndAt;$('landing-error').textContent=noOutput?'Unmeasured':'Speech pending';$('landing-description').textContent=noOutput?'The station event arrived before any Writer sentence stream was available. No speech end or substitute timing result exists.':'The provider station event arrived before the sentence stream completed. Door-opening time and prospective accuracy remain unmeasured.';return;}
  if(!validTime){$('landing-label').textContent='LIVE TIMING';$('landing-error').textContent='Unavailable';$('landing-description').textContent='No unambiguous provider event epoch was returned; no arrival error was calculated.';return;}
  const error=(live.lastSentenceEndWall-epoch*1000)/1000;
  if(live.continuousAudio&&live.lastEndKind==='browser-speech-end'){$('landing-label').textContent='SPEECH VS STATION OBSERVATION';$('landing-error').textContent=`${error>=0?'+':'−'}${Math.abs(error).toFixed(1)} s`;$('landing-description').textContent='Actual browser final-speech end compared with the provider’s station-arrival timestamp. Polling, provider lag and the door-opening offset remain uncertain.';}
  else{$('landing-label').textContent='LIVE TEXT TIMING';$('landing-error').textContent='Audio unmeasured';$('landing-description').textContent=`${live.lastEndKind==='virtual-text-timing'?`Virtual text ended ${error>=0?'+':'−'}${Math.abs(error).toFixed(1)} s from the provider station event. `:'Audio was interrupted or enabled partway through. '}This is not a continuous speech or door-opening accuracy measurement.`;}
}
function toggleLiveAudio(){
  const live=state.live;if(!('speechSynthesis'in window)||(!state.audio&&!matchingVoice())){notice('No matching browser language voice is available. Live text timing remains explicit; audio is unmeasured.');return;}
  state.audio=!state.audio;if(live.storyActive){live.continuousAudio=false;if(!state.audio&&live.utterance){stopLiveSpeech();const text=live.sentences[live.sentenceIndex]||'';live.textEndAt=performance.now()+Math.max(1.5,Array.from(text).length/4.51)*1000;}notice('Live sound changed partway through the story. Continuous audio timing is unavailable for this run.');}renderPlayback();if(live.storyActive)renderLiveForecast();
}

function bindEvents(){
  $('play-button').addEventListener('click',()=>setPlaying(!state.playing));$('restart-button').addEventListener('click',()=>{resetReplay();notice('');});
  $('line-select').addEventListener('change',e=>selectJourney(e.target.value));$('exit-select').addEventListener('change',e=>selectJourney(state.journey.line,e.target.value,state.journey.id));
  $('source-select').addEventListener('change',e=>setSource(e.target.value));$('journey-select').addEventListener('change',e=>selectJourney(state.journey.line,undefined,e.target.value));
  $('generate-button').addEventListener('click',()=>startConnected());$('authored-button').addEventListener('click',()=>{resetReplay();notice('Returned to the authored story. All real service receipts remain visible.');});
  $('scrubber').addEventListener('input',e=>seek(e.target.value));$('audio-button').addEventListener('click',toggleAudio);
  $('lang-en').addEventListener('click',()=>setLanguage('en'));$('lang-ko').addEventListener('click',()=>setLanguage('ko'));
  $('speed-control').querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>{state.speed=Number(button.dataset.speed);invalidateSpeech('Replay speed changed. Restart at 1× with sound for a continuous measurement.');if(state.audio&&state.speed!==1){state.audio=false;resetSpeech();state.lastSentenceEnd=null;notice('Accelerated replay uses text and a virtual speech clock. Sound is available at 1×.');}state.lastTick=performance.now();renderPlayback();}));
  $('replay-mode').addEventListener('click',()=>setMode('replay'));$('live-mode').addEventListener('click',()=>setMode('live'));$('refresh-live').addEventListener('click',refreshLive);
  $('train-select').addEventListener('change',()=>{stopLiveStory('Train selection changed.');state.live.arrival=null;invalidateLivePoll();state.live.selectedKey=$('train-select').value;state.live.to='';state.live.eta=null;refreshLive();});
  $('live-exit-select').addEventListener('change',()=>{stopLiveStory('Exit changed.');state.live.arrival=null;invalidateLivePoll();state.live.to=$('live-exit-select').value;state.live.eta=null;refreshLive();});$('live-start').addEventListener('click',startLiveStory);$('live-stop').addEventListener('click',()=>stopLiveStory('Live story stopped. No further model calls will be made until you start again.'));
  $('connection-button').addEventListener('click',openSettings);$('close-dialog').addEventListener('click',()=>$('connection-dialog').close());$('connection-form').addEventListener('submit',setConnection);$('clear-connection').addEventListener('click',()=>{cancelConnected();state.requestEpoch++;state.apiBase='';state.apiToken='';$('api-url').value='';$('api-token').value='';});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&(state.modelRun||state.modelBusy||state.live.active||state.live.storyActive||state.live.modelBusy)){const wasLive=state.mode==='live';cancelConnected();if(wasLive)notice('Live monitoring and model requests stopped because this tab was hidden. Refresh positions and explicitly start again to resume.');}if(document.hidden&&state.playing){setPlaying(false);notice('Replay paused because this tab was hidden. Continue when you return.');}});
  window.addEventListener('pagehide',()=>{cancelConnected();stopAnimation();resetSpeech();state.requestEpoch++;if(state.wakeLock)state.wakeLock.release().catch(()=>{});});
}
export function validatedJourneys(manifest,provenance,source){
  if(manifest?.schema!=='last-sentence/replay-v1'||manifest.provenance!==provenance||!Array.isArray(manifest.journeys))return [];
  return manifest.journeys.filter(j=>typeof j.id==='string'&&typeof j.line==='string'&&j.source===source&&Array.isArray(j.stations)&&j.stations.length>=2&&j.stations[0].offset_s===0&&j.stations.every((s,i)=>typeof s.name==='string'&&Number.isFinite(s.offset_s)&&(i===0||s.offset_s>j.stations[i-1].offset_s)));
}
function setSource(source){
  if(source==='recorded'&&!state.recordedJourneys.length){notice('No validated recorded journey is available. Authored timing fixtures remain available.');$('source-select').value='fixture';return;}
  state.source=source;state.journeys=source==='recorded'?state.recordedJourneys:state.fixtureJourneys;
  const lines=[...new Set(state.journeys.map(j=>j.line))];$('line-select').replaceChildren(...lines.map(line=>{const option=document.createElement('option');option.value=line;option.textContent=`Line ${line.replace('호선','')} · ${line}`;return option;}));
  selectJourney(lines[0]);notice(source==='recorded'?'Recorded provider observations, authored story. Replay knows the event times in advance; its schedule error is not predictive or door-opening accuracy.':'Authored timing fixtures selected. No real train or model measurement is implied.');
}
function updateProvenance(){
  $('source-description').textContent=isRecorded()?`Train ${state.journey.trainNo} · ${state.recordedInfo.partial?'partial recording · ':''}known timeline · ${state.generated?'model output':'authored story'}`:`Synthetic timing · ${state.generated?'connected model output':'authored story · no model calls'}`;
  const copy=$('provenance-copy');copy.replaceChildren();const strong=document.createElement('strong');strong.textContent=isRecorded()?'Recorded observations. ':'An honest replay. ';copy.append(strong,document.createTextNode(isRecorded()?`Provider station observations are replayed on their known timeline. ${state.recordedInfo.partial?'This recording is partial. ':''}${state.recordedInfo.pollInterval?`Polling interval: ${state.recordedInfo.pollInterval} s. `:''}The story is authored unless connected models are explicitly used. Provider lag and door-opening offsets are unmeasured. `:'The three routes and stories are authored fixtures. Arrival means a simulated station event; door opening and real-world accuracy have not been measured. '));
  const link=document.createElement('a');link.href='../docs/LIMITATIONS.md';link.target='_blank';link.rel='noopener';link.textContent='Read the limitations ↗';copy.append(link);
}
function stopModelRun(){
  state.modelEpoch++;state.modelController?.abort();state.modelController=null;state.modelBusy=false;state.modelRun=false;state.generated=false;
  $('generate-button').disabled=false;$('generate-button').textContent='Generate with connected models';$('authored-button').hidden=true;$('generation-status').textContent='Optional billable requests · inference reservation cap ≤ $3; Tavily separate. Account billing may differ.';
  document.querySelector('.conductor-card').classList.remove('model-active');document.querySelector('.outline-badge').textContent='LOCAL PROPOSALS';document.querySelector('.conductor-explainer').textContent='A local rule proposes scene changes as the known replay clock advances. The authored story stays fixed.';$('model-state').textContent='Not connected · no model calls in replay';
}
function cancelConnected(){
  stopLiveMonitoring('Live connection paused. Refresh positions to reconnect.');state.live.arrival=null;state.live.eta=null;
  const restore=state.generated;const hadRun=state.modelRun||state.modelBusy;if(hadRun&&state.playing)setPlaying(false);stopModelRun();if(restore){state.lines=authoredStory(state.lang,exitName());state.schedule=makeSchedule(state.lines,duration());state.sentenceIndex=sampleSchedule(state.schedule,state.elapsed);state.lastSentenceEnd=null;renderSentence();updateProvenance();}renderPlayback();
}
function modelPayload(){
  const current=state.stations[Math.max(0,state.stationIndex)]||state.stations[0];return {current_station:current.name,exit_station:exitName(),stations_left:state.stations.length-1-Math.max(0,state.stationIndex),remaining_s:Math.max(0,duration()-state.elapsed),elapsed_story_s:state.elapsed,eta_source:isRecorded()?'recorded-replay':'synthetic-fixture',remaining_scenes:[{id:'remaining-story',chars:state.lines.slice(state.sentenceIndex).join('').length}]};
}
async function startConnected(){
  if(state.mode!=='replay'){notice('Connected story generation is available only for explicitly labeled replays.');return;}if(state.modelBusy)return;
  if(state.playing)setPlaying(false);resetSpeech();if(state.audio){state.audio=false;renderPlayback();}
  if(duration()-state.elapsed<25){notice('Restart the replay before generating a connected story. At least 25 seconds of replay time is required.');return;}
  const epoch=++state.modelEpoch;state.modelController?.abort();state.modelController=new AbortController();state.modelBusy=true;renderPlayback();$('generate-button').disabled=true;$('generation-status').textContent='Checking model access and the Worker reservation budget…';
  try{
    const status=await requestApi('/api/status',{signal:state.modelController.signal});if(epoch!==state.modelEpoch)return;
    if(!status.inference_enabled)throw Error('Connected model inference is disabled. Configure the Worker and session access token in connection settings.');
    if(!Number.isFinite(status.limits?.reservation_budget_usd)||status.limits.reservation_budget_usd>3||!Number.isFinite(status.limits?.completion_calls_remaining)||status.limits.completion_calls_remaining<4||!Number.isFinite(status.limits.reserved_usd)||status.limits.reservation_budget_usd-status.limits.reserved_usd<=0)throw Error('No authenticated Worker budget for a complete plan/write cycle is available (up to four completion attempts). No model request was sent.');
    $('generation-status').textContent=`Connected · reservation ceiling $${status.limits.reservation_budget_usd.toFixed(2)} · ${status.limits.completion_calls_remaining} completion attempts remain. Billing may differ.`;
    if(status.tavily_enabled){const fact=await requestApi(`/api/fact?station=${encodeURIComponent(exitName())}`,{signal:state.modelController.signal});addReceipt(fact,epoch===state.modelEpoch?'Tavily fact':'Tavily fact · late response');if(epoch!==state.modelEpoch)return;state.modelFact=fact.fact||null;}else state.modelFact=null;
    state.stationIndex=0;state.stations.forEach((station,index)=>{if(station.offset_s<=state.elapsed)state.stationIndex=index;});state.modelRun=true;state.modelBusy=false;await replanConnected(true,epoch);
  }catch(error){if(epoch!==state.modelEpoch)return;state.modelRun=false;state.modelBusy=false;notice(`Connected generation stopped: ${error.message} ${state.generated?'The last successful generated text is retained.':'The authored story remains available.'}`);$('generation-status').textContent='No connected story is active. Existing receipts are retained.';}finally{if(epoch===state.modelEpoch){state.modelBusy=false;$('generate-button').disabled=false;renderPlayback();}}
}
async function replanConnected(initial=false,givenEpoch=state.modelEpoch){
  if(state.modelBusy||!state.modelRun)return;const epoch=givenEpoch,wasPlaying=!initial&&state.playing;state.modelBusy=true;if(wasPlaying){state.playing=false;stopAnimation();appendLog('Replay clock paused while connected models prepare the next text. Network time is excluded from replay timing.','NETWORK PAUSE');}renderPlayback();$('generate-button').disabled=true;
  const signal=state.modelController?.signal;
  try{
    const planResult=await requestApi('/api/plan',{method:'POST',body:modelPayload(),signal});addReceipt(planResult,epoch===state.modelEpoch?'Conductor':'Conductor · late response');if(epoch!==state.modelEpoch)return;
    const plan=planResult.plan;if(!plan||typeof plan.log!=='string'||!Number.isFinite(plan.budget_chars))throw Error('The Conductor returned an invalid plan.');
    appendLog(plan.log,'NEMOTRON');
    if(!initial&&!plan.ops?.length)return;
    const budget=Math.min(1800,Math.max(0,Math.floor(plan.budget_chars)));if(budget<40||duration()-state.elapsed<15){appendLog('The response arrived too late to rewrite the remaining story.','NOT APPLIED');return;}
    const result=await requestApi('/api/write',{method:'POST',body:{lang:state.lang,exit_station:exitName(),budget_chars:budget,is_last_scene:true,fact:state.modelFact,scene:Array.from(`Rewrite the remaining envelope story, preserving continuity. Already read: ${state.lines.slice(0,state.sentenceIndex+1).join(' ').slice(-140)}. Remaining outline: ${state.lines.slice(state.sentenceIndex+1).join(' ').slice(0,100)}. Proposals: ${(plan.ops||[]).map(op=>`${op.op}:${op.scene}`).join('; ').slice(0,120)}. End at the exit.`).slice(0,500).join('')},signal});addReceipt(result,epoch===state.modelEpoch?'Writer':'Writer · late response');if(epoch!==state.modelEpoch)return;
    if(!Array.isArray(result.sentences)||!result.sentences.length||!result.sentences.every(s=>typeof s==='string'))throw Error('The Writer returned no valid sentence stream.');
    const remaining=duration()-state.elapsed;if(remaining<5){appendLog('Writer completed after the usable replay window; output was not applied.','NOT APPLIED');return;}
    state.generated=true;state.lines=result.sentences;state.schedule=makeSchedule(state.lines,remaining).map(s=>({...s,start:s.start+state.elapsed,end:s.end+state.elapsed}));state.sentenceIndex=0;state.lastSentenceEnd=null;state.lastSpoken=-1;invalidateSpeech('Connected generation currently uses a virtual text clock.');
    document.querySelector('.conductor-card').classList.add('model-active');document.querySelector('.outline-badge').textContent='CONNECTED MODEL';document.querySelector('.conductor-explainer').textContent='The connected Conductor plans the remaining story. Successful Writer output replaces the remaining text; actual API receipts appear below.';$('model-state').textContent=`${result.model||'Writer'} · real response, replay clock`;$('authored-button').hidden=false;$('generate-button').textContent='Regenerate connected story';
    $('generation-status').textContent='Connected story ready. Replay uses known event times; this is not an ETA accuracy measurement.';
    renderSentence();updateProvenance();notice('Connected model output is active. Real usage is listed in Receipts. The text schedule uses known replay event times and does not measure real-world arrival accuracy.');
  }catch(error){if(epoch!==state.modelEpoch)return;state.modelRun=false;notice(`Model replanning stopped: ${error.message} ${state.generated?'The last successful generated text is retained.':'The authored story is retained.'}`);appendLog('Model request failed; no substitute model receipt or success was invented.','STOPPED');$('generation-status').textContent='Automatic model replanning stopped. Existing output and receipts are retained.';}
  finally{if(epoch===state.modelEpoch){state.modelBusy=false;$('generate-button').disabled=false;renderPlayback();if(wasPlaying&&state.modelRun&&!document.hidden&&!state.finished)setPlaying(true);}}
}
async function boot(){
  bindEvents();try{
    const response=await fetch('./replay/manifest.json',{cache:'no-store'});if(!response.ok)throw Error(`HTTP ${response.status}`);const manifest=await response.json();state.fixtureJourneys=validatedJourneys(manifest,'synthetic-fixture','synthetic-fixture');if(!state.fixtureJourneys.length)throw Error('No valid fixture journeys');
    try{const recordedResponse=await fetch('./replay/recorded-manifest.json',{cache:'no-store'});if(recordedResponse.ok){const recorded=await recordedResponse.json();state.recordedJourneys=validatedJourneys(recorded,'recorded-observations','seoul-sample');state.recordedInfo={partial:recorded.partial===true,pollInterval:Number.isFinite(recorded.timing_uncertainty?.poll_interval_s)?recorded.timing_uncertainty.poll_interval_s:null};}}catch{}
    const option=$('source-select').querySelector('[value=recorded]');option.disabled=!state.recordedJourneys.length;option.textContent=state.recordedJourneys.length?'Recorded train observations':'Recorded train observations (unavailable)';
    state.source=state.recordedJourneys.length?'recorded':'fixture';$('source-select').value=state.source;state.journeys=state.source==='recorded'?state.recordedJourneys:state.fixtureJourneys;const lines=[...new Set(state.journeys.map(j=>j.line))];$('line-select').replaceChildren(...lines.map(line=>{const option=document.createElement('option');option.value=line;option.textContent=`Line ${line.replace('호선','')} · ${line}`;return option;}));selectJourney(lines[0]);
  }catch(error){notice(`Replay fixtures could not load: ${error.message}. Serve the repository over HTTP, then reload.`);$('play-button').disabled=true;$('line-select').disabled=true;$('exit-select').disabled=true;}
}
if(typeof document!=='undefined')boot();
