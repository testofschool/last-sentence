import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rate_pacing import MinutePacer,PacingError
from model_simulation import Session,SimulationError
from run_matrix import LIGHTNING,SUPER,ULTRA,cost_plan


class Clock:
    def __init__(self):self.value=0;self.pauses=[]
    def now(self):return self.value
    def sleep(self,seconds):self.pauses.append(seconds);self.value+=seconds


def test_pacing_reserves_whole_completion_groups_and_token_envelope():
    clock=Clock();pacer=MinutePacer(clock.now,clock.sleep)
    for _ in range(5):assert pacer.reserve(3,3*(16384+400),7200)==0
    waited=pacer.reserve(3,3*(16384+400),7200)
    assert waited>=60
    assert max(clock.pauses)<=30
    assert sum(event[2] for event in pacer.events)<=300000
    # Separately exercise request-count pressure when token usage is tiny.
    count_pacer=MinutePacer(clock.now,clock.sleep)
    assert count_pacer.reserve(45,45,7200)==0
    assert count_pacer.reserve(1,1,7200)>=60


def test_runtime_refuses_a_pacing_wait_before_dispatch():
    clock=Clock();pacer=MinutePacer(clock.now,clock.sleep)
    pacer.reserve(45,100,59)
    with pytest.raises(PacingError,match='runtime would expire'):
        pacer.reserve(1,100,59)
    assert clock.pauses==[]


def test_hourly_public_price_revalidation_retains_bound_and_refuses_changes(tmp_path):
    clock=Clock();prices={LIGHTNING:(.06,.24),SUPER:(.3,.9),ULTRA:(1,3)}
    requests=[]
    def no_http(*args):requests.append(args);raise AssertionError('no Worker call expected')
    changed={**prices,SUPER:(.4,.9)}
    session=Session(no_http,'session',prices,cost_plan(prices,1),tmp_path/'run.json',clock=clock.now,sleep=clock.sleep,
        wall_clock=lambda:4000+clock.value,price_checked_at=0,price_refresher=lambda:(changed,{'source_url':'public-model-catalog'}),test_transport=True)
    with pytest.raises(SimulationError,match='rates changed'):
        session.request('/api/write',{'test':True},SUPER,1)
    assert requests==[]
    assert session.document['price_revalidations'][0]['rates_unchanged'] is False
    assert session.document['actual_api_cost_usd']==0
    assert session.document['inference_dispatch_attempts']==0
    stable=Session(no_http,'session',prices,cost_plan(prices,1),tmp_path/'stable.json',clock=clock.now,sleep=clock.sleep,
        wall_clock=lambda:4000+clock.value,price_checked_at=0,price_refresher=lambda:(prices,{'source_url':'public-model-catalog'}),test_transport=True)
    stable.revalidate_prices()
    assert stable.price_checked_at==4000
    assert stable.document['price_revalidations'][0]['rates_unchanged'] is True
