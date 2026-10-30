from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_ops import partition,editable_inputs,prepare,apply


def test_current_scene_is_fully_protected_and_exit_cannot_be_dropped():
    scenes=partition(['one','two','three','four','exit'])
    assert editable_inputs(scenes,1)==[{'id':'scene-2','chars':9},{'id':'exit','chars':4}]
    assert prepare(scenes,1,{'op':'compress','scene':'scene-1'},100)['allowed'] is False
    assert prepare(scenes,1,{'op':'drop','scene':'exit'},100)['allowed'] is False


def test_scene_patch_fingerprint_and_late_protection_keep_untouched_scenes():
    scenes=partition(['one','two','three','four','exit'])
    patch={**prepare(scenes,1,{'op':'compress','scene':'scene-2'},100),'sentences':['short']}
    updated,reason=apply(scenes,1,patch)
    assert reason is None
    assert updated[0]==scenes[0] and updated[-1]==scenes[-1]
    assert updated[1]['sentences']==['short']
    late,reason=apply(scenes,3,patch)
    assert late==scenes and 'protected' in reason
    changed=[scenes[0],{**scenes[1],'sentences':['changed']},scenes[2]]
    assert apply(changed,1,patch)[1]=='scene changed after generation'


def test_insert_limit_and_drop_then_insert_do_not_rewrite_existing_scenes():
    scenes=partition(['one','two','three','four','exit'])
    patch={**prepare(scenes,1,{'op':'insert','scene':'bridge'},900),'sentences':['bridge']}
    updated,reason=apply(scenes,1,patch)
    assert reason is None
    assert [scene['id'] for scene in updated]==['scene-1','scene-2','bridge','exit']
    assert updated[0]==scenes[0] and updated[1]==scenes[1] and updated[-1]==scenes[-1]
    assert prepare(updated,1,{'op':'insert','scene':'extra'},900)['allowed'] is False
    drop=prepare(updated,1,{'op':'drop','scene':'scene-2'},900)
    reduced,reason=apply(updated,1,drop)
    assert reason is None
    assert prepare(reduced,1,{'op':'insert','scene':'extra'},900)['allowed'] is True


def test_exit_replacement_cannot_expand_into_multiple_sentences():
    scenes=partition(['body','the final exit sentence'])
    descriptor=prepare(scenes,0,{'op':'compress','scene':'exit'},100)
    updated,reason=apply(scenes,0,{**descriptor,'sentences':['short','ending']})
    assert updated==scenes
    assert reason=='exit scene must remain exactly one sentence'


def test_inserts_share_unread_headroom_and_recheck_after_generation():
    scenes=[{'id':'exit','kind':'exit','sentences':['E'*40]}]
    first={**prepare(scenes,0,{'op':'insert','scene':'first'},100),'sentences':['B'*33]}
    one,reason=apply(scenes,0,first,100)
    assert reason is None
    second=prepare(one,0,{'op':'insert','scene':'second'},100)
    assert first['budget_chars']==33 and second['budget_chars']==27
    unchanged,reason=apply(scenes,0,first,60)
    assert unchanged==scenes
    assert reason=='replacement exceeded current insertion headroom'
