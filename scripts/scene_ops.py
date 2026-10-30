"""Named-scene contract matching the frontend's pure scene helpers."""
import math


def partition(sentences):
    body=sentences[:-1];split=math.ceil(len(body)/2)
    return [{"id":"scene-1","kind":"body","sentences":body[:split]},
            {"id":"scene-2","kind":"body","sentences":body[split:]},
            {"id":"exit","kind":"exit","sentences":sentences[-1:]}]


def layout(scenes):
    result=[];start=0
    for scene in scenes:
        entry={**scene,"start":start,"end":start+len(scene["sentences"]),"chars":sum(len(text) for text in scene["sentences"])}
        result.append(entry);start=entry["end"]
    return result


def editable_inputs(scenes,read_count):
    return [{"id":s["id"],"chars":s["chars"]} for s in layout(scenes) if s["start"]>=read_count and s["sentences"]]


def prepare(scenes,read_count,op,budget_chars):
    def reject(reason):return {"allowed":False,"scene":op.get("scene"),"op":op.get("op"),"reason":reason}
    if op.get("op") not in ("drop","insert","compress") or not isinstance(op.get("scene"),str) or not op["scene"].strip() or len(op["scene"])>40:
        return reject("invalid named operation")
    entries=layout(scenes);target=next((s for s in entries if s["id"]==op["scene"]),None)
    future=[s for s in entries if s["start"]>=read_count and s["sentences"]]
    if op["op"]=="insert":
        if target:return reject("insert id already exists")
        if len(future)>=3:return reject("three unstarted scene slots are already occupied")
        if not any(s["kind"]=="exit" and s["start"]>=read_count for s in entries):return reject("exit scene is already committed")
        flattened=[text for scene in scenes for text in scene['sentences']]
        unread=sum(len(text) for text in flattened[read_count:])
        chars=min(300,math.floor(max(0,budget_chars)/3),math.floor(max(0,budget_chars-unread))) if math.isfinite(budget_chars) else 300
        return {"allowed":True,"op":"insert","scene":op["scene"],"kind":"body","expected":None,"budget_chars":chars} if chars>0 else reject("no insertion budget")
    if not target:return reject("unknown scene")
    if target["start"]<read_count:return reject("current or spoken scene is protected")
    if not target["sentences"]:return reject("scene is empty")
    if op["op"]=="drop" and target["kind"]=="exit":return reject("exit scene cannot be dropped")
    result={"allowed":True,"op":op["op"],"scene":op["scene"],"kind":target["kind"],"expected":list(target["sentences"]),"existing":list(target["sentences"])}
    if op["op"]=="drop":return result
    chars=min(math.floor(target["chars"]*.65),math.floor(max(0,budget_chars)) if math.isfinite(budget_chars) else math.inf)
    return {**result,"budget_chars":chars} if chars>0 else reject("no compression budget")


def apply(scenes,read_count,patch,budget_chars=math.inf):
    check=prepare(scenes,read_count,patch,budget_chars if patch['op']=='insert' else math.inf)
    target=next((s for s in scenes if s["id"]==patch["scene"]),None)
    if not check["allowed"] or (patch["op"]!="insert" and target["sentences"]!=patch["expected"]):
        return scenes,check.get("reason","scene changed after generation")
    if patch["op"]=="drop":return [s for s in scenes if s["id"]!=patch["scene"]],None
    lines=patch.get("sentences")
    if not isinstance(lines,list) or not lines or any(not isinstance(text,str) or not text.strip() for text in lines):
        return scenes,"replacement has no valid sentences"
    if check["kind"]=="exit" and len(lines)!=1:return scenes,"exit scene must remain exactly one sentence"
    if patch['op']=='insert' and sum(len(text) for text in lines)>check['budget_chars']:
        return scenes,"replacement exceeded current insertion headroom"
    if sum(len(text) for text in lines)>patch["budget_chars"]:return scenes,"replacement exceeded scene budget"
    replacement={"id":patch["scene"],"kind":check["kind"],"sentences":list(lines)}
    if patch["op"]=="compress":return [replacement if s["id"]==patch["scene"] else s for s in scenes],None
    index=next(i for i,s in enumerate(scenes) if s["kind"]=="exit")
    return scenes[:index]+[replacement]+scenes[index:],None
