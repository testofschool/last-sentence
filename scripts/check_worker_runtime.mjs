// Explicit, loopback-only smoke check. Uses the published Seoul SAMPLE feed;
// never loads or supplies a Nemotron/Tavily credential.
import {spawn} from 'node:child_process';
import {randomUUID,createHash} from 'node:crypto';
import {readFile,writeFile,unlink} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url)),base='http://127.0.0.1:8792';
if(process.argv[2]!=='--public-sample')throw Error('Explicit --public-sample is required; this makes bounded public read-only requests.');
const outIndex=process.argv.indexOf('--out'),outputName=outIndex<0?'runtime_all_lines.json':process.argv[outIndex+1];
if(typeof outputName!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._-]*\.json$/u.test(outputName))throw Error('--out must name a JSON file inside evidence/worker');
const outputPath=resolve(root,'evidence/worker',outputName);let outputExists=false;try{await readFile(outputPath);outputExists=true;}catch(error){if(error.code!=='ENOENT')throw error;}
if(outputExists)throw Error('Refusing to overwrite existing evidence; choose a fresh --out filename.');
const lines=['2호선','5호선','7호선'],delay=ms=>new Promise(r=>setTimeout(r,ms));
const sourceFiles=['worker/src/core.js','worker/src/eta.js','worker/src/topology.js','worker/src/index.js','worker/src/limits.js','worker/src/limits_config.js','worker/wrangler.jsonc'];
const hashes=async()=>Object.fromEntries(await Promise.all(sourceFiles.map(async path=>[path,createHash('sha256').update(await readFile(resolve(root,path))).digest('hex')])));
const bundleHashes={};
for(const suffix of ['', '_5','_7']){
  const source=await readFile(resolve(root,`evidence/eta_bundle${suffix}.json`));
  if(JSON.parse(source.toString()).recording_complete!==true)throw Error('All three recordings must be frozen before this public runtime check.');
  const destination=await readFile(resolve(root,`dist/replay/eta-bundle${suffix.replace('_','-')}.json`));
  if(!source.equals(destination))throw Error('Build assets must exactly match the frozen ETA bundles before this check.');
  bundleHashes[suffix||'_2']=createHash('sha256').update(source).digest('hex');
}
let occupied=false;try{await fetch(base+'/api/status',{signal:AbortSignal.timeout(500)});occupied=true;}catch{}
if(occupied)throw Error('Port8792 is occupied; refusing to reuse or stop an unrelated process.');
const token=randomUUID(),profilePath=resolve(root,'worker/.dev.vars');
const profile=`ENABLE_LIVE=true\nLIVE_ACCESS_TOKEN=${token}\nSEOUL_RT_KEY=SAMPLE\nNEBIUS_API_KEY=\nTAVILY_API_KEY=\nLIVE_BUDGET_USD=3\nLIVE_MAX_COMPLETIONS=2048\n`;
const initialHashes=await hashes();
await writeFile(profilePath,profile,{flag:'wx',mode:0o600});
const evidence={checked_at:new Date().toISOString(),runtime:'Wrangler4.156.0 local workerd',base,profile:{ENABLE_LIVE:true,SEOUL_RT_KEY:'published SAMPLE',session_token:'excluded',NEBIUS_API_KEY:'empty',TAVILY_API_KEY:'empty',completion_cap:2048,reservation_budget_usd:3},source_sha256:initialHashes,eta_bundle_sha256:bundleHashes,lines:{}};
let child,exited=false;
async function call(path,body){const response=await fetch(base+path,{method:body?'POST':'GET',headers:{authorization:`Bearer ${token}`,...(body?{'content-type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(30000)});return {path,status:response.status,json:await response.json()};}
function guard(condition,message){if(!condition)throw Error(message);}
try{
  child=spawn(process.execPath,[resolve(root,'worker/node_modules/wrangler/bin/wrangler.js'),'dev','--ip','127.0.0.1','--port','8792','--local','--log-level','error'],{cwd:resolve(root,'worker'),detached:process.platform!=='win32',stdio:['ignore','pipe','pipe'],env:{...process.env,NEBIUS_API_KEY:'',TAVILY_API_KEY:'',WRANGLER_SEND_METRICS:'false'}});
  child.stdout.resume();child.stderr.resume();child.on('exit',()=>{exited=true;});
  let ready=false;for(let i=0;i<60;i++){if(exited)throw Error('Owned Wrangler process exited before readiness');try{evidence.status_before=await call('/api/status');ready=true;break;}catch{await delay(500);}}
  guard(ready,'Local Worker did not become ready');const before=evidence.status_before.json;
  guard(before.inference_enabled===false&&before.tavily_enabled===false&&before.position_enabled===true,'Keyless guard failed; no position/inference request was sent');
  guard(before.max_input_token_bound===16384&&before.expected_pricing_supported===true&&before.limits.completion_cap===2048&&before.limits.reservation_budget_usd===3,'Runtime contract differs from the acknowledged full-matrix limits');
  guard(before.receipt_schema==='last-sentence/receipt-v2'&&before.receipt_provenance_supported===true&&before.writer_validation_supported===true&&before.feedback_korean_compare_supported===true,'Runtime lacks the guarded receipt/feedback contract');
  const outcomes=await Promise.allSettled(lines.map(async line=>{
    const row=evidence.lines[line]={quality:before.eta_models[line],polls:[],anchor_checks:[],selected:null};
    for(let attempt=0;attempt<3&&!row.selected;attempt++){
      const poll=await call('/api/position?'+new URLSearchParams({line}));row.polls.push(poll);
      if(poll.json.mode!=='live'){row.availability_reason=poll.json.reason||poll.json.error||'position_unavailable';break;}
      if(!row.quality?.valid){row.availability_reason=row.quality?.reason||'eta_model_unavailable';break;}
      for(const position of poll.json.positions||[]){
        const params={line,trainNo:String(position.trainNo),direction:String(position.updnLine)};
        const chooser=await call('/api/eta?'+new URLSearchParams(params));row.anchor_checks.push(chooser);
        for(const exit of chooser.json.eligible_exits||[]){
          if(!exit.horizon_supported)continue;
          const forecast=await call('/api/eta?'+new URLSearchParams({...params,to:exit.station}));
          if(forecast.json.eta_available&&forecast.json.anchor?.verified&&forecast.json.remaining_s>5){row.selected={params:{...params,to:exit.station},forecast};break;}
        }
        if(row.selected)break;
      }
      if(!row.selected&&attempt<2)await delay(20000);
    }
    if(row.selected){
      const forecast=row.selected.forecast.json;
      row.plan_refusal=await call('/api/plan',{current_station:forecast.anchor.station,exit_station:row.selected.params.to,remaining_s:forecast.remaining_s,stations_left:forecast.stations_left,elapsed_story_s:0,eta_source:'recorded-model',train_anchor:row.selected.params,remaining_scenes:[{id:'scene-1',chars:100},{id:'exit',chars:20}]});
      guard(row.plan_refusal.status===503&&row.plan_refusal.json.error==='missing_nebius_key',`${line}: expected missing-key refusal for its actual server forecast`);
    }else row.availability_reason ||= row.anchor_checks.at(-1)?.json.reason||'no_fresh_verified_forward_exit_after_three_polls';
  }));
  const failed=outcomes.find(outcome=>outcome.status==='rejected');if(failed)throw failed.reason;
  evidence.status_after=await call('/api/status');const after=evidence.status_after.json;
  evidence.outbound_position_attempt_count=after.limits.seoul_calls_used_today-before.limits.seoul_calls_used_today;
  evidence.inference_completion_count_delta=after.limits.completion_calls_used-before.limits.completion_calls_used;
  evidence.search_count_delta=after.limits.search_calls_used-before.limits.search_calls_used;
  evidence.eligible_eta_success_count=lines.filter(line=>evidence.lines[line].selected).length;
  evidence.source_unchanged=JSON.stringify(evidence.source_sha256)===JSON.stringify(await hashes());
  guard(evidence.inference_completion_count_delta===0&&evidence.search_count_delta===0,'Unexpected model or search reservation');
  guard(evidence.outbound_position_attempt_count<=18&&evidence.source_unchanged,'Public request bound or source consistency failed');
  evidence.runtime_guard_checks_passed=true;
}catch(error){evidence.runtime_guard_checks_passed=false;evidence.error=String(error.message).replaceAll(token,'[excluded]');process.exitCode=1;}
finally{
  const stop=signal=>{try{if(child&&!exited)process.platform==='win32'?child.kill(signal):process.kill(-child.pid,signal);}catch{}};
  stop('SIGINT');for(let i=0;i<50&&child&&!exited;i++)await delay(100);if(child&&!exited){stop('SIGTERM');await delay(500);}
  let removed=false;try{if(await readFile(profilePath,'utf8')===profile){await unlink(profilePath);removed=true;}}catch{}
  let stopped=true;try{await fetch(base+'/api/status',{signal:AbortSignal.timeout(500)});stopped=false;}catch{}
  evidence.cleanup={completed_at:new Date().toISOString(),local_server_stopped:stopped,owned_temporary_profile_removed:removed,provider_keys_ever_loaded:false};
  if(!stopped||!removed){evidence.runtime_guard_checks_passed=false;process.exitCode=1;}
  await writeFile(outputPath,JSON.stringify(evidence,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({passed:evidence.runtime_guard_checks_passed,eligible_eta_success_count:evidence.eligible_eta_success_count,position_attempts:evidence.outbound_position_attempt_count,inference:evidence.inference_completion_count_delta,search:evidence.search_count_delta,cleanup:evidence.cleanup}));
}
