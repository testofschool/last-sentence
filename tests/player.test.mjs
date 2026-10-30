import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { formatTime, storyBudget, makeSchedule, sampleSchedule, validatedJourneys, journeyWindow } from '../web/app.js';

test('clock and speech budget retain a 20-second margin',()=>{
  assert.equal(formatTime(560),'09:20');assert.equal(formatTime(-4),'00:00');assert.equal(formatTime(NaN),'00:00');assert.equal(storyBudget(20),0);assert.equal(storyBudget(100),360);
});
test('authored fixture schedules are monotonic and explicitly target a known event',async()=>{
  const manifest=JSON.parse(await readFile(new URL('../web/replay/manifest.json',import.meta.url),'utf8'));
  for(const journey of manifest.journeys){const end=journey.stations.at(-1).offset_s;const schedule=makeSchedule(['An opening.','A bridge scene.','The last sentence.'],end);assert.equal(schedule[0].start,0);assert.ok(Math.abs(schedule.at(-1).end-(end-3))<1e-8);assert.ok(schedule.every((s,i)=>s.end>s.start&&(!i||s.start>=schedule[i-1].end)));}
});
test('single-sentence streams preserve the known-event target',()=>{
  const schedule=makeSchedule(['One last line.'],120);assert.equal(schedule.at(-1).end,117);assert.deepEqual(makeSchedule([],120),[]);assert.deepEqual(makeSchedule(['Text'],0),[]);
});
test('sentence sampling respects boundaries and clamps to the stream',()=>{
  const schedule=makeSchedule(['First','Middle','Last'],100);assert.equal(sampleSchedule(schedule,-5),0);assert.equal(sampleSchedule(schedule,schedule[1].start),1);assert.equal(sampleSchedule(schedule,999),2);
});
test('recorded source rejects synthetic provenance and malformed station clocks',()=>{
  const good={id:'r1',line:'2호선',source:'seoul-sample',stations:[{name:'A',offset_s:0},{name:'B',offset_s:80}]};
  const data={schema:'last-sentence/replay-v1',provenance:'recorded-observations',journeys:[good,{...good,id:'zero',stations:[{name:'A',offset_s:0},{name:'B',offset_s:0}]},{...good,id:'reverse',stations:[{name:'A',offset_s:20},{name:'B',offset_s:10}]},{...good,id:'fake',source:'synthetic-fixture'}]};
  assert.deepEqual(validatedJourneys(data,'recorded-observations','seoul-sample').map(j=>j.id),['r1']);assert.deepEqual(validatedJourneys({...data,provenance:'synthetic-fixture'},'recorded-observations','seoul-sample'),[]);
});

test('boarding at an observed station preserves actual intervals and limits exits to forward stations',()=>{
  const journey={stations:[{name:'A',offset_s:0},{name:'B',offset_s:90},{name:'C',offset_s:210},{name:'D',offset_s:340}]};
  assert.deepEqual(journeyWindow(journey,1,'D'),{startIndex:1,exitIndex:3,stations:[{name:'B',offset_s:0},{name:'C',offset_s:120},{name:'D',offset_s:250}]});assert.equal(journeyWindow(journey,2,'A').exitIndex,3);
});
test('a combined recorded manifest keeps all three line identities and observed windows selectable',()=>{
  const journeys=['2호선','5호선','7호선'].map((line,index)=>({id:`recorded-${line}-${index}`,line,trainNo:`${index+1}`,source:'seoul-sample',stations:[{name:`${line} A`,offset_s:0},{name:`${line} B`,offset_s:100}]}));const valid=validatedJourneys({schema:'last-sentence/replay-v1',provenance:'recorded-observations',journeys},'recorded-observations','seoul-sample');assert.deepEqual(valid.map(j=>j.line),['2호선','5호선','7호선']);assert.equal(new Set(valid.map(j=>j.id)).size,3);
});
