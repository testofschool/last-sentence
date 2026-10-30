import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {handleRequest} from '../worker/src/core.js';
import {topologyFor,directedPath} from '../worker/src/topology.js';
import {validateEtaBundle,estimateEta,verifiedArrival,etaFromQuery,anchorCacheKey} from '../worker/src/eta.js';

// Model metrics below are declared fixtures for code tests. Official topology and
// API namespaces are read from the saved evidence; no validation result is forged.
const topology=JSON.parse(await readFile(new URL('../web/replay/topology.json',import.meta.url),'utf8'));
const now=Date.parse('2026-10-30T02:00:00Z');
function bundle(line){return {schema:'last-sentence/eta-bundle-v1',line,trace_sha256:topology.lines[line].direction_confirmation.trace_sha256,prepared_at:'2026-10-30T01:59:00Z',recording_complete:true,topology_sha256:'d'.repeat(64),topology:{schema:topology.schema,line,...structuredClone(topology.lines[line]),sources:topology.sources},model:{schema:'last-sentence/eta-v1',source:'recorded-station-arrival-proxy',segments:{},line_medians_s:{[line]:120},segment_observations:20},evaluation:{method:'leave-one-train-identity-out',status:'measured',gate_lte_15_percent:true,arrival_event:'station-arrival-proxy',n:20,train_identities:3,median_relative_error:.1,station_horizons:[3,10]}};}
function anchor(line,station,direction,terminal,id){return {line,station,recptnDt:'2026-10-30T01:59:20Z',epoch_s:(now-40000)/1000,trainSttus:'1',trainNo:'5555',direction,verified:true,terminus:{station:terminal,raw_name:terminal,id}};}
function cache(){const entries=new Map();return {match:async r=>entries.get(r.url)?.clone(),put:async(r,v)=>entries.set(r.url,v.clone())};}

test('official line 5 and 7 graphs have complete verified edges and independently gated directions',()=>{
  for(const[line,nodes,edges]of[['5호선',56,55],['7호선',53,52]]){
    const value=bundle(line),graph=topologyFor(value,line);assert.equal(graph.valid,true);assert.equal(graph.nodes.size,nodes);assert.equal(graph.edge_count,edges);assert.equal(validateEtaBundle(value,line).valid,true);
    value.topology.direction_confirmation.confirmed=false;assert.equal(validateEtaBundle(value,line).reason,'topology_direction_unverified');
  }
});
test('line 5 chooses the actual terminal branch and cannot cross from one branch into the other',()=>{
  const b=bundle('5호선'),a=anchor('5호선','강동','1','마천','1005080555');
  const eta=estimateEta(b,a,'오금',{now:()=>now});assert.equal(eta.eta_available,true);assert.deepEqual(eta.route,['강동','둔촌동','올림픽공원','방이','오금']);assert.equal(eta.remaining_s,440);
  assert.equal(estimateEta(b,a,'길동',{now:()=>now}).reason,'route_exceeds_train_terminus');
  const other=estimateEta(b,anchor('5호선','강동','1','하남검단산','1005000558'),'명일',{now:()=>now});assert.deepEqual(other.route,['강동','길동','굽은다리','명일']);assert.ok(!other.route.includes('둔촌동'));
  const impossible=estimateEta(b,anchor('5호선','방이','0','하남검단산','1005000558'),'길동',{now:()=>now});assert.equal(impossible.reason,'terminus_direction_mismatch');
});
test('line 5 reverse direction follows the branch to the trunk toward 방화',()=>{
  const value=estimateEta(bundle('5호선'),anchor('5호선','방이','0','방화','1005000510'),'천호',{now:()=>now});
  assert.deepEqual(value.route,['방이','올림픽공원','둔촌동','강동','천호']);assert.equal(value.stations_left,4);
});
test('line 7 supports canonical aliases and refuses SMSS codes masquerading as realtime terminal IDs',()=>{
  const b=bundle('7호선');
  const a=verifiedArrival({trainNo:'5555',statnNm:'상도(중앙대앞)',statnId:'1007000739',recptnDt:'2026-10-30T01:59:20Z',trainSttus:'1',updnLine:'1',statnTnm:'석남(거북시장)',statnTid:'1007000761'},'7호선','http-public-sample',{etaBundle:b,now:()=>now});
  assert.equal(a.station,'상도');assert.equal(a.terminus.station,'석남');
  const eta=estimateEta(b,a,'보라매',{now:()=>now});assert.equal(eta.eta_available,true);assert.deepEqual(eta.route,['상도','장승배기','신대방삼거리','보라매']);
  const fake=estimateEta(b,anchor('7호선','상도','0','장암','2711'),'숭실대입구',{now:()=>now});assert.equal(fake.reason,'verified_terminus_unavailable');
});
test('joining branch ends or changing published edge evidence invalidates the graph',()=>{
  const b=bundle('5호선');b.topology.paths=[...b.topology.paths,[b.topology.paths[0].at(-1),b.topology.paths[1].at(-1)]];assert.equal(topologyFor(b,'5호선').valid,false);
  const changed=bundle('7호선');changed.topology.edges.pop();assert.equal(topologyFor(changed,'7호선').reason,'topology_edges_disagree_with_paths');
});
test('line readiness is independent: partial and failed recordings do not disable a valid other line',async()=>{
  const b5=bundle('5호선'),b7=bundle('7호선');b5.recording_complete=false;
  const response=await handleRequest(new Request('https://test.example/api/status'),{}, {etaBundles:{'5호선':b5,'7호선':b7},fetch:async()=>{throw Error('No vendor request permitted');}});
  const result=await response.json();assert.equal(result.eta_models['5호선'].valid,false);assert.equal(result.eta_models['7호선'].valid,true);assert.deepEqual(result.eta_model_lines,['7호선']);assert.equal(result.eta_model_configured,true);
  const failed=bundle('7호선');failed.evaluation.median_relative_error=.2;assert.equal(validateEtaBundle(failed,'7호선').reason,'eta_held_out_gate_not_met');
});
test('cached arrival identities remain bound to line, train and direction',async()=>{
  const store=cache(),b=bundle('5호선');await store.put(anchorCacheKey('5호선','5555','1'),Response.json(anchor('5호선','강동','1','마천','1005080555')));
  const deps={etaBundles:{'5호선':b,'7호선':bundle('7호선')},cache:store,now:()=>now};
  const good=await etaFromQuery(new URLSearchParams({line:'5호선',trainNo:'5555',direction:'1',to:'오금'}),{},deps);assert.equal(good.eta_available,true);
  const wrongLine=await etaFromQuery(new URLSearchParams({line:'7호선',trainNo:'5555',direction:'1',to:'보라매'}),{},deps);assert.equal(wrongLine.reason,'verified_arrival_anchor_unavailable');
  const wrongDirection=await etaFromQuery(new URLSearchParams({line:'5호선',trainNo:'5555',direction:'0',to:'오금'}),{},deps);assert.equal(wrongDirection.reason,'verified_arrival_anchor_unavailable');
});
