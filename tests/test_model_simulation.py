import datetime as dt
import json
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from model_simulation import NoRedirect, WorkerHttp, SimulationError, execute as execute_actual, select_windows, simulate_story
from run_matrix import LIGHTNING, SUPER, ULTRA


class FakeTime:
    def __init__(self):self.elapsed=0;self.epoch=time.time()
    def clock(self):return self.elapsed
    def sleep(self,seconds):self.elapsed+=seconds
    def wall(self):return self.epoch+self.elapsed


def clock_args():
    fake=FakeTime()
    return {'clock':fake.clock,'sleep':fake.sleep,'wall_clock':fake.wall}


def execute(*args,**kwargs):
    injected=clock_args();injected.update(kwargs)
    return execute_actual(*args,**injected)


def inputs(tmp_path):
    rows = []
    base = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    for train in range(3):
        for index, station in enumerate(("강남","역삼","선릉","삼성","종합운동장")):
            value = (base + dt.timedelta(seconds=train*1000+index*120)).isoformat()
            rows.append(dict(ts=value,recptnDt=value,line="2호선",trainNo=str(train),statnNm=station,updnLine="0",trainSttus="1",source="seoul-api"))
    trace = tmp_path / "trace.jsonl"
    trace.write_text("".join(json.dumps(row)+"\n" for row in rows))
    catalog = tmp_path / "prices.json"
    catalog.write_text(json.dumps({"schema":"last-sentence/model-prices-v1","retrieved_at":base.isoformat(),"prices":{
        model:{"input_price_per_million_tokens":a,"output_price_per_million_tokens":b}
        for model,(a,b) in {LIGHTNING:(.06,.24),SUPER:(.3,.9),ULTRA:(1,3)}.items()}}))
    token = tmp_path / "session-token"
    token.write_text("private-test-session-token")
    token.chmod(0o600)
    return rows, trace, catalog, token


class FakeWorker:
    def __init__(self, missing_usage=False, insufficient=False):
        self.requests = []
        self.missing_usage = missing_usage
        self.insufficient = insufficient

    def __call__(self, path, body, timeout):
        self.requests.append((path,body))
        if path == "/api/status":
            return 200,{"inference_enabled":True,"max_input_token_bound":16384,"expected_pricing_supported":True,"limits":{"reservation_budget_usd":3,"reserved_usd":0,"completion_calls_remaining":0 if self.insufficient else 300}},5
        model = LIGHTNING if path == "/api/plan" else ULTRA if body["lang"] == "ko" else SUPER
        a,b = {LIGHTNING:(.06,.24),SUPER:(.3,.9),ULTRA:(1,3)}[model]
        usage = {"prompt_tokens":100,"completion_tokens":100}
        cost = (100*a+100*b)/1_000_000
        call = {"model":model,"usage":None if self.missing_usage else usage,"cost_usd":None if self.missing_usage else cost,
                "latency_ms":20,"pricing":{"input_price_per_million_tokens":a,"output_price_per_million_tokens":b,'fresh_for_dispatch':True,'acknowledged':True}}
        response = {"model":model,"usage":usage,"cost_usd":call["cost_usd"],"latency_ms":20,"calls":[call]}
        if path == "/api/plan":
            target=next((scene['id'] for scene in body['remaining_scenes'] if scene['id']!='exit'),None)
            response.update(plan={"stations_left":body["stations_left"],"remaining_s":body["remaining_s"],"budget_chars":int(max(0,body["remaining_s"]-20)*4.51),
                                 "ops":[{"scene":target,"op":"compress","reason":"time budget"}] if target else [],"log":"Compress remainder"},tool_calls_supported=True)
        else:
            cap = 38 if body["lang"] == "ko" else 80
            if body['is_last_scene']:
                count = max(0,(body["budget_chars"]-len(body["exit_station"]))//cap)
                response["sentences"] = ["A"*cap]*count+[body["exit_station"]]
            else:
                count=body['budget_chars']//cap
                response['sentences']=["B"*cap]*count or ["B"*body['budget_chars']]
        return 200,response,20


def test_executor_requires_explicit_flags_and_refuses_default_full_cost_before_http(tmp_path):
    rows,trace,catalog,token = inputs(tmp_path)
    fake = FakeWorker()
    with pytest.raises(SimulationError,match="--execute"):
        execute(trace,catalog,tmp_path/"out.json","https://worker.example",token,journeys=1,transport=fake)
    with pytest.raises(SimulationError,match="exceeds dollar or completion"):
        execute(trace,catalog,tmp_path/"out.json","https://worker.example",token,execute_flag=True,ack_cost=3,transport=fake)
    with pytest.raises(SimulationError,match='no greater than 7200'):
        execute(trace,catalog,tmp_path/'out.json','https://worker.example',token,journeys=1,execute_flag=True,ack_cost=3,transport=fake,max_runtime_s=7201)
    assert fake.requests == []


def test_guarded_executor_records_real_contract_receipts_but_labels_timing_simulated(tmp_path):
    rows,trace,catalog,token = inputs(tmp_path)
    fake = FakeWorker()
    output = tmp_path/"out.json"
    result = execute(trace,catalog,output,"https://worker.example",token,journeys=1,execute_flag=True,ack_cost=3,transport=fake)
    assert result["status"] == "complete"
    assert len(result["rows"]) == 3
    assert len(result["language_pair"]) == 2
    assert result["measured_tts_runs"] == 0
    assert result["execution_transport"] == "injected-test-transport"
    assert result["actual_api_cost_usd"] > 0
    assert result["actual_api_cost_usd"] < 3
    assert all(row["writer_calls"] <= 4 for row in result["rows"])
    assert all(row["evidence_kind"] == "model-backed-timing-simulation" for row in result["rows"])
    assert "private-test-session-token" not in output.read_text()
    assert result["coverage"]["comparison_basis"] == "fully-paired"


def test_missing_usage_aborts_and_preserves_unknown_spend_instead_of_zero(tmp_path):
    rows,trace,catalog,token = inputs(tmp_path)
    fake = FakeWorker(missing_usage=True)
    result = execute(trace,catalog,tmp_path/"out.json","https://worker.example",token,journeys=1,execute_flag=True,ack_cost=3,transport=fake)
    assert result["status"] == "aborted"
    assert result["actual_api_cost_usd"] is None
    assert result["inference_dispatch_attempts"] == 1
    assert result["model_completion_attempts"] == 1
    assert len([path for path,_ in fake.requests if path != "/api/status"]) == 1
    assert result["attempts"][0]["state"] == "failed"
    assert "usage" in result["failures"][0]["reason"]


def test_insufficient_server_capacity_prevents_paid_dispatch(tmp_path):
    rows,trace,catalog,token = inputs(tmp_path)
    fake = FakeWorker(insufficient=True)
    result = execute(trace,catalog,tmp_path/"out.json","https://worker.example",token,journeys=1,execute_flag=True,ack_cost=3,transport=fake)
    assert result["status"] == "aborted"
    assert result["inference_dispatch_attempts"] == 0
    assert all(path == "/api/status" for path,_ in fake.requests)


def test_controller_forecasts_do_not_receive_final_arrival_and_training_excludes_train(tmp_path):
    rows,trace,catalog,token = inputs(tmp_path)
    window = select_windows(rows,1)[0]
    assert all(entry["trains"] == 2 for entry in window["model"]["segments"].values())
    from model_simulation import Session
    from run_matrix import cost_plan,prices_from_catalog
    prices = prices_from_catalog(catalog)
    outputs = []
    for i,shift in enumerate((0,300)):
        altered = dict(window,events=[dict(event) for event in window["events"]])
        altered["events"][-1]["t"] += shift
        fake = FakeWorker()
        session = Session(fake,"secret",prices,cost_plan(prices,1),tmp_path/f"session{i}.json",test_transport=True,**clock_args())
        row = simulate_story(session,altered,"sentence_replan")
        outputs.append((row,fake.requests))
    assert outputs[0][1] == outputs[1][1]
    assert outputs[0][0]["story_end_s"] == outputs[1][0]["story_end_s"]
    assert outputs[1][0]["landing_error_s"] == pytest.approx(outputs[0][0]["landing_error_s"]-300)


def test_worker_http_refuses_redirects_and_empty_hosts_without_egress(monkeypatch):
    import io
    import urllib.error
    import urllib.request
    seen = []
    class FakeOpener:
        def open(self, request, timeout):
            seen.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url,302,"Found",{},io.BytesIO(b'{"error":"redirect"}'))
    def opener(handler):
        assert handler is NoRedirect
        return FakeOpener()
    monkeypatch.setattr(urllib.request,"build_opener",opener)
    client = WorkerHttp("https://worker.example","test-session")
    code,body,_ = client("/api/status",None,1)
    assert code == 302
    assert seen == ["https://worker.example/api/status"]
    assert NoRedirect().redirect_request(None,None,302,"Found",{},"https://elsewhere.example") is None
    with pytest.raises(SimulationError):
        WorkerHttp("https:","test-session")


def test_malformed_call_list_aborts_with_unknown_cost_and_preserved_dispatch(tmp_path):
    rows,trace,catalog,token = inputs(tmp_path)
    fake = FakeWorker()
    def malformed(path,body,timeout):
        code,result,elapsed = fake(path,body,timeout)
        if path != "/api/status":
            result["calls"] = None
        return code,result,elapsed
    result = execute(trace,catalog,tmp_path/"out.json","https://worker.example",token,journeys=1,execute_flag=True,ack_cost=3,transport=malformed)
    assert result["status"] == "aborted"
    assert result["actual_api_cost_usd"] is None
    assert result["inference_dispatch_attempts"] == 1
    assert result["completion_attempt_count_known"] is False


def test_full_matrix_requires_ten_recorded_windows_from_each_line():
    from eta_model import LINE2
    from topology import DATA
    rows=[]
    base=dt.datetime(2026,10,30,10,0,tzinfo=dt.timezone.utc)
    paths={"2호선":LINE2[:9],**{line:info["paths"][0][:9] for line,info in DATA["lines"].items()}}
    for line,path in paths.items():
        for train in range(3):
            for index,station in enumerate(path):
                value=(base+dt.timedelta(seconds=train*2000+index*120)).isoformat()
                rows.append(dict(ts=value,recptnDt=value,line=line,trainNo=str(train),statnNm=station,updnLine="0" if line=="2호선" else "1",trainSttus="1",source="seoul-api"))
    windows=select_windows(rows,30)
    assert {line:sum(window["line"]==line for window in windows) for line in paths} == {line:10 for line in paths}
    assert len(set(window["id"] for window in windows)) == 30
    with pytest.raises(SimulationError,match="10 eligible recorded windows per line"):
        select_windows([row for row in rows if row["line"]!="7호선"],30)


def test_named_compression_calls_only_affected_scene_and_keeps_untouched_text(tmp_path):
    from model_simulation import Session
    from run_matrix import prices_from_catalog,cost_plan
    from scene_ops import partition
    rows,trace,catalog,token=inputs(tmp_path);prices=prices_from_catalog(catalog);fake=FakeWorker()
    session=Session(fake,"test",prices,cost_plan(prices,1),tmp_path/'scene.json',test_transport=True,**clock_args())
    row=simulate_story(session,select_windows(rows,1)[0],'sentence_replan')
    initial=next(receipt['sentences'] for receipt in row['receipts'] if 'sentences' in receipt)
    original=partition(initial)
    final={scene['id']:scene for scene in row['final_scene_state']}
    assert final['scene-1']['sentences']==original[0]['sentences']
    assert final['exit']['sentences']==original[2]['sentences']
    assert final['scene-2']['sentences']!=original[1]['sentences']
    writes=[body for path,body in fake.requests if path=='/api/write']
    assert len(writes)==2
    assert writes[1]['is_last_scene'] is False
    assert 'only named scene scene-2' in writes[1]['scene']
    assert any(d.get('scene')=='scene-2' and d.get('action')=='applied' for d in row['controller_decisions'])


def test_named_drop_is_local_preserves_exit_and_uses_no_additional_writer(tmp_path):
    from model_simulation import Session
    from run_matrix import prices_from_catalog,cost_plan
    rows,trace,catalog,token=inputs(tmp_path);prices=prices_from_catalog(catalog);fake=FakeWorker()
    def dropper(path,body,timeout):
        code,result,latency=fake(path,body,timeout)
        if path=='/api/plan':
            for op in result['plan']['ops']:op['op']='drop'
        return code,result,latency
    session=Session(dropper,'test',prices,cost_plan(prices,1),tmp_path/'drop.json',test_transport=True,**clock_args())
    row=simulate_story(session,select_windows(rows,1)[0],'sentence_replan')
    assert row['writer_calls']==1
    assert 'scene-2' not in [scene['id'] for scene in row['final_scene_state']]
    assert row['final_scene_state'][-1]['id']=='exit'
    assert any(d.get('op')=='drop' and d.get('action')=='applied' and d['writer_request'] is False for d in row['controller_decisions'])


def test_route_timeouts_match_plan_write_budgets_and_remaining_runtime(tmp_path):
    from model_simulation import Session
    from run_matrix import prices_from_catalog,cost_plan
    rows,trace,catalog,token=inputs(tmp_path);prices=prices_from_catalog(catalog);fake=FakeTime();seen=[]
    def transport(path,body,timeout):seen.append((path,timeout));return 200,{},0
    session=Session(transport,'session',prices,cost_plan(prices,1),tmp_path/'timeouts.json',clock=fake.clock,sleep=fake.sleep,wall_clock=fake.wall,test_transport=True)
    session.http('/api/plan',{});session.http('/api/write',{});session.http('/api/status')
    assert seen==[('/api/plan',90),('/api/write',45),('/api/status',25)]
    fake.elapsed=7190;session.http('/api/plan',{})
    assert seen[-1]==('/api/plan',10)
