import copy
import datetime as dt
import json
import os
from pathlib import Path
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import collect_feedback as cf

NOW = dt.datetime(2026, 10, 30, 4, 0, tzinfo=dt.timezone.utc)
TOKEN = 'private-worker-session-token-for-feedback-tests'
RATES = {cf.SUPER: (.3, .9), cf.ULTRA: (1., 3.)}

def catalog():
    return [{'status': 'active', 'flavors': [{'model_id': model, 'input_price_per_million_tokens': a,
             'output_price_per_million_tokens': b} for model, (a, b) in RATES.items()]}]

def status():
    return {'receipt_schema':'last-sentence/receipt-v2','inference_enabled':True,'max_input_token_bound':16384,
        **{flag:True for flag in ('feedback_korean_compare_supported','receipt_provenance_supported','writer_validation_supported','expected_pricing_supported')},
        'feedback_probe_limits':{'max_input_token_bound':16384,'max_output_tokens':180,'sentence_count':3,'sentence_cap':40,'budget_chars':120,'allowed_models':list(cf.MODELS)},
        'limits':{'reservation_budget_usd':3,'reserved_usd':0,'completion_calls_remaining':300}}

def completion(model):
    lines = ['빈 좌석에 노란 봉투가 놓여 있었다.', '봉투 속에는 손으로 그린 지도가 있었다.', '그는 지도의 작은 별을 오래 바라보았다.']
    lengths = [len(line) for line in lines]
    usage = {'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}
    cost = (100 * RATES[model][0] + 50 * RATES[model][1]) / 1_000_000
    validation = {'status':'valid','purpose':cf.PURPOSE,'language':'ko','text_response':True,
        'counting_basis':'trimmed-nonempty-lines/unicode-code-points','ending_required':False,'ending_station_ok':None,
        'sentence_count':3,'sentences_within_cap':3,'sentences_over_cap':0,'max_sentence_chars':max(lengths),'total_chars':sum(lengths),
        'required_sentence_count':3,'max_sentence_count':3,'sentence_cap':40,'budget_chars':120,
        'scene_budget_ok':True,'sentence_count_ok':True,'sentence_lengths_ok':True,'passed':True,'failures':[]}
    call = {'receipt_schema':'last-sentence/receipt-v2','model':model,'requested_model':model,'provider_reported_model':model,
        'identity_match':True,'usage':usage,'cost_usd':cost,'requested_rate_cost_estimate_usd':cost,'latency_ms':12,
        'input_token_bound':5000,'reserved_microusd':1000,
        'pricing':{'input_price_per_million_tokens':RATES[model][0],'output_price_per_million_tokens':RATES[model][1],
            'fresh_for_dispatch':True,'acknowledged':True},'writer_validation':validation,
        'rate_limit_headers':{'x-ratelimit-limit-requests':'60'}}
    return {'receipt_schema':'last-sentence/receipt-v2','purpose':cf.PURPOSE,'model':model,'requested_model':model,
        'provider_reported_model':model,'identity_match':True,'usage':usage,'cost_usd':cost,
        'requested_rate_cost_estimate_usd':cost,'latency_ms':12,'calls':[call],'sentences':lines,'sentence_cap':40,'char_count':sum(lengths)}

class FakeTransport:
    def __init__(self, *, changed_after=None, status_change=None, completion_change=None, network=False):
        self.calls=[];self.catalog_calls=0;self.changed_after=changed_after;self.status_change=status_change;self.completion_change=completion_change;self.network=network
    def __call__(self, method, url, body=None, token=None, timeout=15):
        self.calls.append((method,url,copy.deepcopy(body),token,timeout))
        if url==cf.CATALOG_URL:
            self.catalog_calls+=1;data=catalog()
            if self.changed_after is not None and self.catalog_calls>self.changed_after:
                data[0]['flavors'][1]['input_price_per_million_tokens']=2
            return cf.Reply(200,data,{},2)
        if url.endswith('/api/status'):
            data=status()
            if self.status_change:self.status_change(data)
            return cf.Reply(200,data,{},2)
        if self.network:raise cf.TransportError('mock connection lost '+TOKEN)
        assert method=='POST' and url.endswith('/api/write')
        data=completion(body['feedback_model']);code=200
        if self.completion_change:code=self.completion_change(data,body) or code
        return cf.Reply(code,data,{'x-ratelimit-remaining-requests':'59'},12)
    @property
    def posts(self):return [call for call in self.calls if call[0]=='POST']

def prepare(tmp_path, fake=None):
    fake=fake or FakeTransport();plan=cf.make_plan(fake,now=lambda:NOW,worker='https://worker.example')
    token=tmp_path/'worker-session';token.write_text(TOKEN);token.chmod(0o600)
    return fake,plan,token

def run(tmp_path,fake,plan,token,**kwargs):
    return cf.execute(plan,tmp_path/'feedback.json','https://worker.example',token,'.03',execute_flag=True,
        transport=fake,now=lambda:NOW,**kwargs)

def test_default_plan_only_fetches_public_catalog_and_bounds_exactly_two_approved_models():
    fake=FakeTransport();plan=cf.make_plan(fake,now=lambda:NOW)
    assert len(fake.calls)==1 and fake.calls[0][0]=='GET' and fake.calls[0][3] is None
    assert plan['inference_calls_made']==0 and plan['evidence_kind']=='mocked-plan'
    assert plan['worst_case_usd']==pytest.approx(.0220012)
    assert plan['limits']['completion_attempts']==2 and plan['model_order']==list(cf.MODELS)

@pytest.mark.parametrize('cap',[None,'.001','.06','NaN'])
def test_execution_needs_explicit_small_cap_before_any_worker_or_model_call(tmp_path,cap):
    fake,plan,token=prepare(tmp_path);before=len(fake.calls)
    with pytest.raises(cf.FeedbackError):cf.execute(plan,tmp_path/'out.json','https://worker.example',token,cap,execute_flag=True,transport=fake,now=lambda:NOW)
    assert len(fake.calls)==before
    with pytest.raises(cf.FeedbackError,match='--execute'):cf.execute(plan,tmp_path/'out.json','https://worker.example',token,'.03',transport=fake)

@pytest.mark.parametrize('mode,symlink',[(0o644,False),(0o600,True)])
def test_session_token_is_protected_and_symlinks_refused(tmp_path,mode,symlink):
    fake,plan,token=prepare(tmp_path);token.chmod(mode)
    if symlink:
        alias=tmp_path/'alias';alias.symlink_to(token);token=alias
    before=len(fake.calls)
    with pytest.raises(cf.FeedbackError):run(tmp_path,fake,plan,token)
    assert len(fake.calls)==before

@pytest.mark.parametrize('flag',['expected_pricing_supported','writer_validation_supported','receipt_provenance_supported','feedback_korean_compare_supported','receipt_schema'])
def test_worker_capability_handshake_fails_closed_before_completions(tmp_path,flag):
    fake,plan,token=prepare(tmp_path,FakeTransport(status_change=lambda data:data.pop(flag)))
    result=run(tmp_path,fake,plan,token)
    assert result['status']=='aborted' and result['worker_write_attempts']==0 and not fake.posts

@pytest.mark.parametrize('change',[lambda data:data['limits'].update(completion_calls_remaining=1),lambda data:data['limits'].update(reserved_usd=2.99)])
def test_shared_three_dollar_budget_and_two_completion_slots_are_required(tmp_path,change):
    fake,plan,token=prepare(tmp_path,FakeTransport(status_change=change));result=run(tmp_path,fake,plan,token)
    assert result['status']=='aborted' and not fake.posts

def test_successful_controlled_requests_share_the_same_scene_and_preserve_receipts_without_claiming_quality(tmp_path):
    fake,plan,token=prepare(tmp_path);result=run(tmp_path,fake,plan,token)
    assert result['status']=='complete' and result['evidence_kind']=='mocked-feedback-probe'
    assert result['worker_write_attempts']==2 and all(row['status']=='success' for row in result['rows'])
    bodies=[call[2] for call in fake.posts]
    assert all(set(body)=={'purpose','lang','feedback_model','sentence_count','budget_chars','scene','expected_pricing'} for body in bodies)
    assert [{k:v for k,v in body.items() if k not in ('feedback_model','expected_pricing')} for body in bodies]==[cf.common_body(),cf.common_body()]
    assert [body['feedback_model'] for body in bodies]==list(cf.MODELS)
    assert all(row['validation_observed']['sentences_within_cap']==3 and len(row['sentences'])==3 for row in result['rows'])
    assert all(row['provider_rate_limit_headers']['x-ratelimit-limit-requests']=='60' for row in result['rows'])
    assert result['korean_quality']=='UNMEASURED-human-review-required' and result['onboarding']['status']=='UNMEASURED'
    assert TOKEN not in (tmp_path/'feedback.json').read_text()
    assert all(0<call[4]<=45 for call in fake.posts)

def test_changed_catalog_before_dispatch_refuses_all_completions(tmp_path):
    fake,plan,token=prepare(tmp_path,FakeTransport(changed_after=1));result=run(tmp_path,fake,plan,token)
    assert result['status']=='aborted' and not fake.posts and result['price_checks'][0]['unchanged'] is False

def test_price_change_between_models_keeps_first_receipt_and_refuses_second(tmp_path):
    fake,plan,token=prepare(tmp_path,FakeTransport(changed_after=2));result=run(tmp_path,fake,plan,token)
    assert result['status']=='aborted' and len(fake.posts)==1
    assert result['rows'][0]['status']=='success' and result['usage_cost_estimate_usd'] is not None

@pytest.mark.parametrize('kind',['missing','mismatched','compatibility-only','missing-usage'])
def test_unverified_provenance_or_usage_stays_unknown_and_cannot_become_a_model_sample(tmp_path,kind):
    def change(data,body):
        if kind=='missing':
            data.pop('provider_reported_model');data['calls'][0].pop('provider_reported_model')
        elif kind=='mismatched':
            data['provider_reported_model']=cf.ULTRA;data['calls'][0]['provider_reported_model']=cf.ULTRA
        elif kind=='compatibility-only':
            for item in (data,data['calls'][0]):
                for key in ('requested_model','provider_reported_model','identity_match'):item.pop(key)
        else:data['calls'][0]['usage']=None
    fake,plan,token=prepare(tmp_path,FakeTransport(completion_change=change));result=run(tmp_path,fake,plan,token)
    assert result['status']=='aborted' and len(fake.posts)==1 and result['usage_cost_estimate_usd'] is None
    assert result['rows'][0]['status']=='receipt-unverified' and 'sentences' not in result['rows'][0]['receipt']
    assert result['rows'][0]['receipt']['requested_rate_cost_estimate_usd']>0

def test_rejected_output_keeps_count_failures_and_cost_then_compares_the_other_model_once(tmp_path):
    def reject(data,body):
        if body['feedback_model']==cf.SUPER:
            data.pop('sentences');data['message']='wrong line count';validation=data['calls'][0]['writer_validation']
            validation.update(status='rejected',passed=False,sentence_count=4,sentences_within_cap=4,sentences_over_cap=0,max_sentence_chars=10,total_chars=40,sentence_count_ok=False,required_sentence_count=3,failures=['exact_sentence_count'])
            return 502
    fake,plan,token=prepare(tmp_path,FakeTransport(completion_change=reject));result=run(tmp_path,fake,plan,token)
    assert result['status']=='completed-with-rejected-output' and len(fake.posts)==2
    assert result['rows'][0]['writer_validation']['sentence_count']==4 and result['rows'][0]['cost_usd']>0
    assert result['rows'][0]['validation_countable'] is True and result['rows'][0]['validation_summary']['sentence_count']==4
    assert result['rows'][1]['status']=='success'

def test_network_failure_is_unknown_and_redacted_without_retry_or_second_completion(tmp_path):
    fake,plan,token=prepare(tmp_path,FakeTransport(network=True));result=run(tmp_path,fake,plan,token)
    assert result['status']=='aborted' and len(fake.posts)==1 and result['usage_cost_estimate_usd'] is None
    assert result['rows'][0]['status']=='unknown_outcome' and TOKEN not in (tmp_path/'feedback.json').read_text()

def test_output_nonoverwrite_and_stale_or_changed_plan_are_preflight_failures(tmp_path):
    fake,plan,token=prepare(tmp_path);path=tmp_path/'feedback.json';path.write_text('keep me')
    with pytest.raises(cf.FeedbackError,match='already exists'):run(tmp_path,fake,plan,token)
    assert path.read_text()=='keep me' and not fake.posts
    path.unlink();plan['expires_at']=cf.iso(NOW-dt.timedelta(seconds=1))
    with pytest.raises(cf.FeedbackError,match='stale'):run(tmp_path,fake,plan,token)
    assert not fake.posts

def test_vendor_key_bytes_are_not_read_and_aliases_are_refused(tmp_path,monkeypatch):
    vendor=tmp_path/'.nebius_key';vendor.write_text('private-vendor-key-never-read');vendor.chmod(0o600)
    monkeypatch.setattr(cf,'VENDOR_PATHS',(vendor,))
    original=cf.os.open;opened=[]
    def tracked(path,*args,**kwargs):
        opened.append(Path(path))
        if Path(path)==vendor:raise AssertionError('vendor key bytes must not be opened')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(cf.os,'open',tracked)
    os.utime(vendor,(1,1));marker=tmp_path/'ready.json';value=cf.mark_key_ready(marker,vendor,now=lambda:NOW)
    assert value['observed_at']==cf.iso(NOW) and value['key_bytes_read'] is False and vendor not in opened
    alias=tmp_path/'vendor-alias';os.link(vendor,alias)
    with pytest.raises(cf.FeedbackError,match='vendor credential'):cf.safe_read(alias,4096,protected=True)
    assert alias not in opened

def test_marker_is_explicit_and_mocks_do_not_become_an_onboarding_measurement(tmp_path):
    fake,plan,token=prepare(tmp_path);vendor=tmp_path/'key-presence';vendor.write_text('present');marker=tmp_path/'ready.json';cf.mark_key_ready(marker,vendor,now=lambda:NOW-dt.timedelta(minutes=2));result=run(tmp_path,fake,plan,token,marker_path=marker)
    assert result['onboarding']['status']=='UNMEASURED'
    future=tmp_path/'future.json';cf.mark_key_ready(future,vendor,now=lambda:NOW+dt.timedelta(hours=1))
    with pytest.raises(cf.FeedbackError,match='future'):cf.ready_marker(future,lambda:NOW)

def test_invalid_prices_and_redirects_are_not_silently_free_or_followed():
    for value in (None,'',True,float('nan')):
        data=catalog();data[0]['flavors'][0]['input_price_per_million_tokens']=value
        with pytest.raises(cf.FeedbackError):cf.rates_from_catalog(data)
    with pytest.raises(cf.TransportError,match='redirect'):cf.NoRedirect().redirect_request(None,None,302,'redirect',{},'https://other.example')

@pytest.mark.parametrize('kind',['missing','inconsistent'])
def test_rejected_validation_is_excluded_when_missing_or_falsified_but_attempt_cost_is_preserved(tmp_path,kind):
    def change(data,body):
        if body['feedback_model']==cf.SUPER:
            if kind=='missing':data['calls'][0].pop('writer_validation')
            else:data['calls'][0]['writer_validation'].update(status='rejected',passed=False,sentence_count=4,sentences_within_cap=1,failures=['exact_sentence_count'])
            data['message']='model rejected';return 502
    fake,plan,token=prepare(tmp_path,FakeTransport(completion_change=change));result=run(tmp_path,fake,plan,token)
    row=result['rows'][0];assert row['status']=='rejected' and row['cost_usd']>0
    assert row['validation_countable'] is False and row['validation_denominator_excluded'] is True
    assert 'sentences' not in row['receipt'] and row['rejected_text_discarded'] is True
    assert len(fake.posts)==2 and result['rows'][1]['status']=='success'

@pytest.mark.parametrize('kind',['counting-basis','ending-required','ending-station','compatibility-model','requested-rate-estimate'])
def test_exact_probe_and_cost_contract_failures_cannot_be_used_as_successful_samples(tmp_path,kind):
    def change(data,body):
        if kind=='counting-basis':data['calls'][0]['writer_validation']['counting_basis']='guessed sentences'
        elif kind=='ending-required':data['calls'][0]['writer_validation']['ending_required']=True
        elif kind=='ending-station':data['calls'][0]['writer_validation']['ending_station_ok']=True
        elif kind=='compatibility-model':data['calls'][0]['model']=cf.ULTRA
        else:data['requested_rate_cost_estimate_usd']=9
    fake,plan,token=prepare(tmp_path,FakeTransport(completion_change=change));result=run(tmp_path,fake,plan,token)
    assert result['status']=='aborted' and len(fake.posts)==1
    assert 'sentences' not in result['rows'][0]['receipt'] and result['rows'][0]['status']=='receipt-unverified'

def test_execution_deadline_records_the_known_first_reply_and_prevents_a_second_dispatch(tmp_path):
    elapsed=[0.0]
    class SlowMock(FakeTransport):
        def __call__(self,method,url,body=None,token=None,timeout=15):
            reply=super().__call__(method,url,body,token,timeout)
            if method=='POST':elapsed[0]=181
            return reply
    fake,plan,token=prepare(tmp_path,SlowMock());result=run(tmp_path,fake,plan,token,clock=lambda:elapsed[0])
    assert result['status']=='aborted' and len(fake.posts)==1
    assert result['rows'][0]['status']=='success' and result['rows'][0]['cost_usd']>0
    assert any('runtime exhausted' in error for error in result['errors'])
