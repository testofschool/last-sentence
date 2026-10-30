import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from eta_model import timestamp
from run_matrix import SUPER,measured_import


def replay_data(tmp_path):
    rows=[]
    for station,receipt in [('강남','10:00:00'),('역삼','10:02:00'),('선릉','10:04:00')]:
        value='2026-10-30T'+receipt+'+09:00'
        rows.append(dict(ts=value,recptnDt=value,line='2호선',trainNo='42',updnLine='1',statnNm=station,trainSttus='1',source='seoul-sample'))
    trace=tmp_path/'trace.jsonl';trace.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    import hashlib
    mapping={'kind':'historical-replay-1x','source':'recorded-observations','direction':'1','speed':1,
        'uninterrupted':True,'paused':False,'seeked':False,'recorded_origin_station':'강남',
        'recorded_origin_at':'2026-10-30T10:00:00+09:00','playback_origin_at':'2026-10-30T11:00:00+09:00'}
    receipt={'model':SUPER,'usage':{'prompt_tokens':100,'completion_tokens':50},'cost_usd':.000075,'latency_ms':100,
        'pricing':{'input_price_per_million_tokens':.3,'output_price_per_million_tokens':.9}}
    row={'id':'replay-1','trainNo':'42','line':'2호선','exit_station':'선릉','policy':'fixed_clip',
        'arrival_at':'2026-10-30T10:04:00+09:00','speech_end_at':'2026-10-30T11:04:08+09:00',
        'clock_mapping':mapping,'controller_provenance':{'policy':'fixed_clip','eta_source':'recorded-replay'},'receipts':[receipt]}
    data={'trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(),'speech_clock':'browser-speech-end-event','rows':[row]}
    return data,trace,timestamp('2026-10-30T12:00:00+09:00')


def test_historical_browser_speech_uses_explicit_elapsed_clock_mapping(tmp_path):
    data,trace,now=replay_data(tmp_path)
    result=measured_import(data,trace,now=now);row=result['rows'][0]
    assert row['landing_error_s']==8
    assert row['measurement_clock']=='historical-replay-1x'
    assert row['clock_mapping']['recorded_interval_s']==240
    assert row['clock_mapping']['measured_speech_elapsed_s']==248
    assert row['clock_mapping']['mapped_arrival_wall_at']=='2026-10-30T11:04:00+09:00'
    assert row['clock_mapping']['contiguous_window_validated'] is True
    assert row['controller_provenance']==data['rows'][0]['controller_provenance']


@pytest.mark.parametrize('field,value,error',[
    ('speed',4,'speed=1'),('paused',True,'interrupted'),('seeked',True,'interrupted'),('uninterrupted',False,'interrupted'),
    ('source','synthetic-fixture','recorded observations'),('direction','0','same raw train'),
    ('recorded_origin_station','선릉','same raw train'),
    ('recorded_origin_at','2026-10-30T10:00:05+09:00','same raw train'),
    ('playback_origin_at','2026-10-31T11:00:00+09:00','future'),
    ('playback_origin_at','2026-10-30T11:00:00','timezone'),
    ('kind','character-rate-simulation','unsupported'),
])
def test_historical_clock_mapping_refuses_invalid_origins_and_interrupted_replays(tmp_path,field,value,error):
    data,trace,now=replay_data(tmp_path);data['rows'][0]['clock_mapping'][field]=value
    with pytest.raises(ValueError,match=error):measured_import(data,trace,now=now)


def test_historical_replay_rejects_character_rate_estimates(tmp_path):
    data,trace,now=replay_data(tmp_path);data['speech_clock']='character-rate-estimate'
    with pytest.raises(ValueError,match='actual browser speech-end'):
        measured_import(data,trace,now=now)


def test_historical_replay_retains_matching_controller_policy(tmp_path):
    data,trace,now=replay_data(tmp_path);data['rows'][0]['controller_provenance']['policy']='single_fit'
    with pytest.raises(ValueError,match='controller-policy provenance'):
        measured_import(data,trace,now=now)
