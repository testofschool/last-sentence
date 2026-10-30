import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_eta import prepare

ROOT=Path(__file__).resolve().parents[1]

def rows(line,stations,identity):
    start=dt.datetime(2026,10,30,10,0,tzinfo=dt.timezone(dt.timedelta(hours=9)))
    return [dict(ts=(start+dt.timedelta(seconds=120*i)).isoformat(),recptnDt=(start+dt.timedelta(seconds=120*i)).isoformat(),line=line,trainNo=identity,statnNm=station,updnLine='1',trainSttus='1',source='seoul-sample')for i,station in enumerate(stations)]

def test_single_snapshot_keeps_line_filter_and_embeds_topology_without_shadowing_it(tmp_path):
    path=tmp_path/'mixed.jsonl'
    records=rows('2호선',['강남','역삼','선릉','삼성'],'21')+rows('5호선',['방화','개화산','김포공항','송정'],'51')
    raw=''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in records).encode()
    path.write_bytes(raw);path.with_suffix('.meta.json').write_text('{"complete":true}')
    result=prepare(path,'5호선',ROOT/'web/replay/topology.json')
    assert result['line']=='5호선'
    assert result['recording_complete'] is True
    assert result['trace_sha256']==hashlib.sha256(raw).hexdigest()
    assert set(result['model']['line_medians_s'])=={'5호선'}
    assert result['topology']['line']=='5호선'
    assert result['topology_sha256']==hashlib.sha256((ROOT/'web/replay/topology.json').read_bytes()).hexdigest()
    original=prepare(path)
    assert 'line' not in original
    assert set(original['model']['line_medians_s'])=={'2호선','5호선'}

def test_prepare_cli_supports_isolated_python_and_does_not_overwrite_other_line_outputs(tmp_path):
    path=tmp_path/'trace.jsonl';path.write_text(''.join(json.dumps(row)+'\n'for row in rows('5호선',['방화','개화산','김포공항'],'51')))
    output=tmp_path/'eta_bundle_5.json'
    result=subprocess.run([sys.executable,'-I',str(ROOT/'scripts/prepare_eta.py'),str(path),'--line','5호선','--out',str(output)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(output.read_text())['line']=='5호선'
    assert (tmp_path/'eta_model_5.json').exists()
    assert not (tmp_path/'eta_model.json').exists()
