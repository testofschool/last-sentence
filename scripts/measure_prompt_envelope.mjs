// Stress every controlled prompt/history shape with mocked provider responses.
// No network, credentials, real tokens, model execution or paid requests occur.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { handleRequest, MODELS, MAX_INPUT_TOKEN_BOUND, PROMPT_LIMITS } from '../worker/src/core.js';
import { anchorCacheKey } from '../worker/src/eta.js';
import {topologyFor,directedPath} from '../worker/src/topology.js';

const repeat = (pattern, n) => Array.from({length:n}, () => pattern).join('');
function memoryCache() { const values = new Map(); return { match: async request => values.get(request.url)?.clone(), put: async (request,response) => values.set(request.url,response.clone()) }; }

export async function measureEnvelope() {
  const results = [];
  const template = JSON.parse(await readFile(new URL('../evidence/eta_bundle.json', import.meta.url), 'utf8'));
  const officialTopology=JSON.parse(await readFile(new URL('../web/replay/topology.json',import.meta.url),'utf8'));
  for (const pattern of ['😀', '\\', '"']) {
    const ids = Array.from({length:12}, (_,i) => repeat(pattern,38) + String(i).padStart(2,'0'));
    const ops = ids.slice(0,4).map(scene => ({scene,op:'compress',reason:repeat(pattern,96)}));
    for (const kind of ['all-tools', 'split-tools', 'json-fallback', 'live-split-tools', 'live-split-tools-5', 'live-split-tools-7', 'writer-en', 'writer-ko']) {
      const bodies = []; let call = 0;
      const store = memoryCache();
      const bundle = structuredClone(template); bundle.model.segments = {}; // Payload stress fixture: force all fallback data into the tool result.
      const now = Date.now();
      let line='2호선',direction='0',from='시청',target='성수',terminal={station:'성수',raw_name:'성수종착',id:'1002000211'};
      if(kind==='live-split-tools-5'||kind==='live-split-tools-7'){
        line=kind.endsWith('-5')?'5호선':'7호선';direction='1';terminal=line==='5호선'?{station:'하남검단산',raw_name:'하남검단산',id:'1005000558'}:{station:'석남',raw_name:'석남(거북시장)',id:'1007000761'};
        bundle.line=line;bundle.topology_sha256='e'.repeat(64);bundle.topology={schema:officialTopology.schema,line,...structuredClone(officialTopology.lines[line]),sources:officialTopology.sources};bundle.trace_sha256=bundle.topology.direction_confirmation.trace_sha256;bundle.model.line_medians_s={[line]:120};
        const graph=topologyFor(bundle,line);const candidates=[...graph.nodes].map(station=>directedPath(graph,station,terminal.station,direction)).filter(path=>path?.length>=11).sort((a,b)=>Buffer.byteLength(b[0])-Buffer.byteLength(a[0]));
        from=candidates[0][0];target=candidates[0][10];
      }
      const anchor = {line,station:from,recptnDt:new Date(now).toISOString(),epoch_s:now/1000,trainSttus:'1',trainNo:'12345678',direction,verified:true,terminus:terminal};
      await store.put(anchorCacheKey(line,'12345678',direction),Response.json(anchor));
      const env = {ENABLE_LIVE:'true',LIVE_ACCESS_TOKEN:'mock-session',NEBIUS_API_KEY:'mock-key',LIMITS:{getByName:()=>({reserve:async()=>({allowed:true})})}};
      const tool = (name,index) => ({id:repeat('x',62)+String(index).padStart(2,'0'),type:'function',function:{name,arguments:JSON.stringify(name==='scene_ops'?{ops}:{})}});
      const deps = {cache:store,etaBundle:bundle,now:()=>now,fetch:async(url,init)=>{
        if(url.endsWith('/models_info'))return Response.json([{flavors:Object.values(MODELS).map(model_id=>({model_id,input_price_per_million_tokens:.1,output_price_per_million_tokens:.3}))}]);
        if(!url.endsWith('/chat/completions'))throw Error('Network is forbidden in the envelope probe');
        const body=JSON.parse(init.body);bodies.push({model:body.model,serialized_utf8_bytes:Buffer.byteLength(init.body),input_bound:Buffer.byteLength(init.body)+PROMPT_LIMITS.framing_tokens});call++;
        let message;
        if(kind.startsWith('writer-'))message={content:'성수'};
        else if(kind==='json-fallback'&&call<=2)message={content:repeat(pattern,Math.floor(PROMPT_LIMITS.no_tool_content_bytes/Buffer.byteLength(pattern)))};
        else if(kind==='all-tools'&&call===1)message={role:'assistant',content:repeat(pattern,Math.floor(PROMPT_LIMITS.tool_turn_content_bytes/Buffer.byteLength(pattern))),tool_calls:['eta_to_station','budget','scene_ops'].map(tool)};
        else if(kind.includes('split-tools')&&call===1)message={role:'assistant',content:repeat(pattern,Math.floor(PROMPT_LIMITS.tool_turn_content_bytes/Buffer.byteLength(pattern))),tool_calls:[tool('scene_ops',0)]};
        else if(kind.includes('split-tools')&&call===2)message={role:'assistant',content:repeat(pattern,Math.floor(PROMPT_LIMITS.tool_turn_content_bytes/Buffer.byteLength(pattern))),tool_calls:[tool('eta_to_station',1),tool('budget',2)]};
        else message={content:JSON.stringify({ops,log:'Fit the explicitly bounded remaining story.'})};
        return Response.json({model:body.model,choices:[{message}],usage:{prompt_tokens:100,completion_tokens:20}});
      }};
      let payload, path;
      if(kind.startsWith('writer-')){path='/api/write';payload={lang:kind.endsWith('-ko')?'ko':'en',exit_station:'성수',budget_chars:4000,is_last_scene:true,scene:repeat(pattern,500),fact:{text:repeat(pattern,240),url:'https://example.org/source'}};}
      else {path='/api/plan';payload={current_station:repeat(pattern,40),exit_station:repeat(pattern,40),stations_left:60,remaining_s:7200,elapsed_story_s:7200,eta_source:'synthetic-fixture',remaining_scenes:ids.map(id=>({id,chars:10000})),...(kind.startsWith('live-split-tools')?{train_anchor:{line,trainNo:'12345678',direction,to:target}}:{})};}
      const response=await handleRequest(new Request('https://mock.example'+path,{method:'POST',headers:{authorization:'Bearer mock-session','content-type':'application/json'},body:JSON.stringify(payload)}),env,deps);
      const data=await response.json();
      results.push({pattern:pattern==='😀'?'four-byte Unicode':pattern==='\\'?'JSON backslash escaping':'JSON quote escaping',case:kind,status:response.status,error:data.error||null,completion_dispatches_mocked:call,requests:bodies});
    }
  }
  const maximum=Math.max(...results.flatMap(r=>r.requests.map(q=>q.input_bound)));
  return {schema:'last-sentence/prompt-envelope-v1',evidence_kind:'controlled-boundary-payloads-with-mocked-provider',checked_at:new Date().toISOString(),actual_provider_requests:0,max_input_token_bound:MAX_INPUT_TOKEN_BOUND,framing_allowance:PROMPT_LIMITS.framing_tokens,prompt_limits:PROMPT_LIMITS,maximum_observed_input_bound:maximum,all_boundary_cases_accepted:results.every(r=>r.status===200),passed:maximum<=MAX_INPUT_TOKEN_BOUND&&results.every(r=>r.status===200),cases:results};
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const result=await measureEnvelope();await mkdir(new URL('../evidence/worker/',import.meta.url),{recursive:true});await writeFile(new URL('../evidence/worker/prompt_envelope.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({passed:result.passed,maximum_observed_input_bound:result.maximum_observed_input_bound,max_input_token_bound:result.max_input_token_bound,boundary_cases:result.cases.length,failures:result.cases.filter(r=>r.status!==200).map(r=>({case:r.case,pattern:r.pattern,error:r.error,status:r.status}))},null,2));if(!result.passed)process.exitCode=1;
}
