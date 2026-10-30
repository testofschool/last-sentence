export const LINE2 = Object.freeze('시청 을지로입구 을지로3가 을지로4가 동대문역사문화공원 신당 상왕십리 왕십리 한양대 뚝섬 성수 건대입구 구의 강변 잠실나루 잠실 잠실새내 종합운동장 삼성 선릉 역삼 강남 교대 서초 방배 사당 낙성대 서울대입구 봉천 신림 신대방 구로디지털단지 대림 신도림 문래 영등포구청 당산 합정 홍대입구 신촌 이대 아현 충정로'.split(' '));
export const ETA_LINES = Object.freeze(['2호선','5호선','7호선']);
const invalid = reason => ({valid:false,reason});

export function topologyFor(bundle,line='2호선') {
  if(!ETA_LINES.includes(line))return invalid('unsupported_line');
  let paths,stations,directionSteps,circular=false,sources=[],directionConfirmation,declaredEdges;
  if(line==='2호선'){
    paths=[LINE2];circular=true;directionSteps={'0':1,'1':-1};
    stations=Object.fromEntries(LINE2.map((name,i)=>[name,{aliases:[],observed_api_station_ids:[`1002000${201+i}`],observed_api_terminal_ids:[`1002000${201+i}`]}]));
    sources=['Fixed line-2 main-loop order and canonical realtime station-ID map; the frozen recording corroborates observed pairs, not every mapped station'];
  }else{
    const t=bundle?.topology;
    if(t?.schema!=='last-sentence/topology-v1'||t.line!==line||!Array.isArray(t.sources)||!t.sources.length||!/^[a-f0-9]{64}$/u.test(bundle?.topology_sha256||''))return invalid('official_topology_unavailable');
    paths=t.paths;stations=t.stations;directionSteps=t.direction_steps;sources=t.sources;directionConfirmation=t.direction_confirmation;declaredEdges=t.edges;
    if(directionConfirmation?.confirmed!==true||directionConfirmation.source!=='recorded-adjacent-station-transitions'||directionConfirmation.inconsistent_pairs!==0||directionConfirmation.trace_sha256!==bundle.trace_sha256||!Number.isInteger(directionConfirmation.transitions)||directionConfirmation.transitions<1)return invalid('topology_direction_unverified');
  }
  if(!Array.isArray(paths)||!paths.length||paths.length>3||!stations||typeof stations!=='object'||![-1,1].includes(directionSteps?.['0'])||directionSteps['1']!==-directionSteps['0'])return invalid('topology_invalid');
  const nodes=new Set(),edges=new Set(),ordered=new Map(),aliasMap=new Map();
  for(const path of paths){
    if(!Array.isArray(path)||path.length<2||path.length>128||new Set(path).size!==path.length)return invalid('topology_path_invalid');
    for(const station of path){if(typeof station!=='string'||!station||Array.from(station).length>40||!Object.hasOwn(stations,station))return invalid('topology_station_invalid');nodes.add(station);}
    for(let i=0;i<path.length-1;i++){
      const a=path[i],b=path[i+1],key=[a,b].sort().join('|');
      if(ordered.has(key)&&ordered.get(key)!==`${a}|${b}`)return invalid('topology_direction_conflict');
      ordered.set(key,`${a}|${b}`);edges.add(key);
    }
  }
  if(circular){const a=paths[0].at(-1),b=paths[0][0],key=[a,b].sort().join('|');ordered.set(key,`${a}|${b}`);edges.add(key);}
  if(!circular&&edges.size!==nodes.size-1)return invalid('topology_not_a_verified_tree');
  if(!circular){
    if(!Array.isArray(declaredEdges)||declaredEdges.some(e=>!Array.isArray(e)||e.length!==2))return invalid('topology_edge_evidence_missing');
    const declared=new Set(declaredEdges.map(([a,b])=>[a,b].sort().join('|')));
    if(declared.size!==edges.size||[...edges].some(edge=>!declared.has(edge)))return invalid('topology_edges_disagree_with_paths');
  }
  const directed={'0':new Map(),'1':new Map()},undirected=new Map([...nodes].map(n=>[n,new Set()]));
  for(const value of ordered.values()){
    const[a,b]=value.split('|');undirected.get(a).add(b);undirected.get(b).add(a);
    for(const direction of ['0','1']){const[from,to]=directionSteps[direction]===1?[a,b]:[b,a];if(!directed[direction].has(from))directed[direction].set(from,new Set());directed[direction].get(from).add(to);}
  }
  const seen=new Set(),pending=[nodes.values().next().value];while(pending.length){const n=pending.pop();if(seen.has(n))continue;seen.add(n);pending.push(...undirected.get(n));}
  if(seen.size!==nodes.size)return invalid('topology_disconnected');
  if((line==='7호선'&&[...undirected.values()].some(n=>n.size>2))||(line==='5호선'&&[...undirected.values()].some(n=>n.size>3)))return invalid('topology_degree_invalid');
  const prefix=line==='2호선'?'1002':line==='5호선'?'1005':'1007';
  for(const name of nodes){
    const row=stations[name];
    if(!row||typeof row!=='object'||!Array.isArray(row.aliases||[])||!Array.isArray(row.observed_api_station_ids||[])||!Array.isArray(row.observed_api_terminal_ids||[]))return invalid('topology_station_metadata_invalid');
    const aliases=[name,...(row.aliases||[])];
    if(![...(row.observed_api_station_ids||[]),...(row.observed_api_terminal_ids||[])].every(id=>typeof id==='string'&&/^\d{10}$/u.test(id)&&id.startsWith(prefix)))return invalid('topology_api_id_namespace_invalid');
    for(const alias of aliases){if(typeof alias!=='string'||!alias||(aliasMap.has(alias)&&aliasMap.get(alias)!==name))return invalid('topology_alias_ambiguous');aliasMap.set(alias,name);}
  }
  return {valid:true,line,paths,stations,nodes,directed,undirected,aliasMap,circular,direction_steps:directionSteps,sources,direction_confirmation:directionConfirmation,edge_count:edges.size};
}

export function stationName(topology,raw){return topology?.valid&&typeof raw==='string'?topology.aliasMap.get(raw.trim())||null:null;}
export function canonicalTerminus(topology,raw,id){
  if(!topology?.valid||typeof raw!=='string')return null;
  const station=stationName(topology,raw.trim().replace(/종착$/u,''));if(!station)return null;
  const row=topology.stations[station],ids=[...(row.observed_api_terminal_ids||[]),...(row.observed_api_station_ids||[])];
  if(!ids.includes(String(id)))return null;
  return {station,id:String(id),raw_name:raw};
}
export function directedPath(topology,from,to,direction){
  if(!topology?.valid||!topology.nodes.has(from)||!topology.nodes.has(to)||!['0','1'].includes(String(direction)))return null;
  const queue=[[from]],seen=new Set();
  while(queue.length){const path=queue.shift(),node=path.at(-1);if(node===to)return path;if(seen.has(node))continue;seen.add(node);for(const next of topology.directed[String(direction)].get(node)||[])if(!seen.has(next))queue.push([...path,next]);}
  return null;
}
export function circularContinuation(topology,from,direction,count=10){
  if(!topology?.valid||!topology.circular)return null;const path=[from];
  for(let i=0;i<count;i++){const next=[...(topology.directed[String(direction)].get(path.at(-1))||[])];if(next.length!==1)return null;path.push(next[0]);}return path;
}
