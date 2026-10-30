import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { formatTime, storyBudget, makeSchedule, sampleSchedule, validatedJourneys } from '../web/app.js';

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
