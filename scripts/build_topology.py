#!/usr/bin/env python3
"""Rebuild derived line5/7 facts from locally retained official SMSS sources.

Raw website assets stay under ignored .local/topology. Code paths are the
manually reviewed operating paths on the official highlighted maps, not numeric
nearest-neighbor guesses. No network requests occur in this script.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def build(raw_folder, output):
    raw_folder=Path(raw_folder)
    css=(raw_folder/"smss_map.css").read_text()
    renames={"뚝섬유원지":"자양","석남(거북시장)":"석남"}
    result={"schema":"last-sentence/topology-v1","retrieved_at":dt.datetime.now(dt.timezone.utc).isoformat(),"lines":{},"sources":[]}
    for number in (5,7):
        markers=re.findall(r"\.t_way"+str(number)+r"_(\d+)_v2\{[^}]+\}/\*\s*(.*?)\s*\*/",css)
        if len(markers)!={5:56,7:53}[number]:
            raise ValueError("official marker count changed; manually review topology before rebuilding")
        names={code:renames.get(name,name) for code,name in markers}
        if number==5:
            # Official line5 map: common trunk ends at 강동; branches leave there.
            paths=[[names[str(code)] for code in list(range(2511,2555))+list(range(2562,2567))],
                   [names[str(code)] for code in list(range(2511,2550))+list(range(2555,2562))]]
        else:
            paths=[[names[code] for code in sorted(names,key=int)]]
        stations={names[code]:{"smss_station_code":code,"code_namespace":"SeoulMetro-SMSS",
            "aliases":sorted(set([name,names[code],re.sub(r"\(.*?\)","",name).strip()])),
            "observed_api_station_ids":[],"observed_api_terminal_ids":[]} for code,name in markers}
        if number==7:
            stations["총신대입구(이수)"]["aliases"].append("이수")
        def canonical(name):
            name=renames.get(name,name)
            if name in stations:
                return name
            base=re.sub(r"\(.*?\)","",name).strip()
            return next((station for station,node in stations.items() if base in node["aliases"]),None)
        observed=[]
        full_sample=ROOT/f"evidence/topology/line{number}_api_full_sample.json"
        if full_sample.exists():
            observed.extend(json.loads(full_sample.read_text()).get("realtimePositionList",[]))
        trace=ROOT/f"web/replay/trace_2026-10-30_line{number}.jsonl"
        if trace.exists():
            observed.extend(json.loads(line) for line in trace.read_text().splitlines() if line.strip())
        for row in observed:
            for name_field,id_field,target in (("statnNm","statnId","observed_api_station_ids"),("statnTnm","statnTid","observed_api_terminal_ids")):
                name=canonical(row.get(name_field,""))
                if name and row.get(id_field):
                    node=stations[name]
                    if row[id_field] not in node[target]:node[target].append(row[id_field])
                    if row[name_field] not in node["aliases"]:node["aliases"].append(row[name_field])
        edges=sorted(set(pair for path in paths for pair in zip(path,path[1:])))
        result["lines"][f"{number}호선"]={"paths":paths,"direction_steps":{"0":-1,"1":1},"stations":stations,
            "edges":[list(edge) for edge in edges],"branch_junction":"강동" if number==5 else None,
            "scope":"Official displayed physical topology; verify live service/terminus separately."}
    sources=[("smss.html","https://smss.seoulmetro.co.kr/traininfo/traininfoUserView.do"),
        ("smss_map.css","https://smss.seoulmetro.co.kr/css/traininfo_user_v2.css")]
    for number in (5,7):
        sources += [(f"line{number}_official.png",f"https://smss.seoulmetro.co.kr/images/train/user/normal/line{number}_v4.png"),
                    (f"smss_line{number}.html","https://smss.seoulmetro.co.kr/traininfo/traininfoUserMap.do")]
    for name,url in sources:
        path=raw_folder/name
        raw=path.read_bytes()
        entry={"url":url,"saved_path":str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"local_only":True}
        if name.startswith("smss_line"):
            entry.update(method="POST",form={"line":name.removeprefix("smss_line").removesuffix(".html"),"isCb":"N"})
        result["sources"].append(entry)
    for number in (5,7):
        path=ROOT/f"evidence/topology/line{number}_api_full_sample.json"
        if path.exists():
            raw=path.read_bytes();result["sources"].append({"url":f"http://swopenapi.seoul.go.kr/api/subway/sample/json/realtimePosition/0/5/{number}%ED%98%B8%EC%84%A0",
                "saved_path":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)})
    result["method"]="Station markers from official CSS; operating paths manually reviewed on official maps. Current SMSS train labels/scheduled station names corroborate 자양 alias. API IDs are included only from actual observations, in a separate namespace."
    result["raw_source_distribution"]="Complete third-party HTML/CSS/map assets remain local-only under ignored .local/topology; tracked topology contains derived factual station/edge data and source hashes/URLs."
    # Save the reviewed graph before using the regular continuity extractor.
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    from eta_model import arrivals,load_trace
    from collections import Counter
    for number in (5,7):
        line=f"{number}호선";trace=ROOT/f"web/replay/trace_2026-10-30_line{number}.jsonl"
        positive=set(tuple(edge) for edge in result["lines"][line]["edges"])
        counts=Counter()
        if trace.exists():
            chains,_=arrivals(load_trace(trace))
            for chain in chains:
                direction=chain[0]["identity"].split("|")[1]
                for a,b in zip(chain,chain[1:]):
                    sign=1 if (a["station"],b["station"]) in positive else -1
                    counts[(direction,sign)]+=1
        inconsistent=sum(value for (direction,sign),value in counts.items() if {"0":-1,"1":1}.get(direction)!=sign)
        result["lines"][line]["direction_confirmation"]={"confirmed":bool(counts) and inconsistent==0,
            "source":"recorded-adjacent-station-transitions","transitions":sum(counts.values()),
            "counts":{f"api_direction_{direction}_path_step_{sign}":value for (direction,sign),value in sorted(counts.items())},
            "inconsistent_pairs":inconsistent,"trace_sha256":hashlib.sha256(trace.read_bytes()).hexdigest() if trace.exists() else None,
            "checked_at":dt.datetime.now(dt.timezone.utc).isoformat()}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-folder",type=Path,default=ROOT/".local/topology")
    parser.add_argument("--out",type=Path,default=ROOT/"web/replay/topology.json")
    args=parser.parse_args();result=build(args.raw_folder,args.out)
    print(json.dumps({line:{"nodes":len(info["stations"]),"edges":len(info["edges"]),"direction_confirmed":info["direction_confirmation"]["confirmed"]} for line,info in result["lines"].items()},ensure_ascii=False))


if __name__=="__main__":
    main()
