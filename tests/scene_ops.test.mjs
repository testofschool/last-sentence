import test from 'node:test';
import assert from 'node:assert/strict';
import { partitionStoryScenes,sceneLayout,editableSceneInputs,prepareSceneOperation,applyNamedScenePatches } from '../web/app.js';
const lines=['Opening one.','Opening two.','Opening three.','Middle one.','Middle two.','The exit is Seongsu'];
const scenes=()=>partitionStoryScenes(lines);

test('initial Writer text partitions into two identifiable body scenes and a sole exit scene',()=>{
  const value=scenes();assert.deepEqual(value.map(scene=>scene.id),['scene-1','scene-2','exit']);assert.deepEqual(value[0].sentences,lines.slice(0,3));assert.deepEqual(value[1].sentences,lines.slice(3,5));assert.deepEqual(value[2].sentences,lines.slice(5));assert.equal(sceneLayout(value)[2].start,5);
});
test('current or partially spoken scenes and the exit cue cannot be dropped',()=>{
  assert.deepEqual(editableSceneInputs(scenes(),1).map(scene=>scene.id),['scene-2','exit']);assert.equal(prepareSceneOperation(scenes(),1,{op:'drop',scene:'scene-1'},500).allowed,false);assert.equal(prepareSceneOperation(scenes(),1,{op:'drop',scene:'exit'},500).allowed,false);
});
test('named drop removes only the unspoken body scene and retains the current scene and exit text',()=>{
  const before=scenes(),patch=prepareSceneOperation(before,1,{op:'drop',scene:'scene-2'},500);const result=applyNamedScenePatches(before,1,[patch]);assert.deepEqual(result.scenes.map(scene=>scene.id),['scene-1','exit']);assert.deepEqual(result.scenes[0],before[0]);assert.deepEqual(result.scenes[1],before[2]);assert.equal(result.applied.length,1);
});
test('compress replaces only its named target and carries a smaller character budget',()=>{
  const before=scenes(),descriptor=prepareSceneOperation(before,1,{op:'compress',scene:'scene-2'},500);assert.ok(descriptor.budget_chars<before[1].sentences.join('').length);const result=applyNamedScenePatches(before,1,[{...descriptor,sentences:['Short middle.']}]);assert.deepEqual(result.scenes[0],before[0]);assert.deepEqual(result.scenes[2],before[2]);assert.deepEqual(result.scenes[1].sentences,['Short middle.']);
});
test('insert creates only a named body scene before the protected exit with at most three future slots',()=>{
  const before=scenes();assert.equal(prepareSceneOperation(before,0,{op:'insert',scene:'bridge'},500).allowed,false);const descriptor=prepareSceneOperation(before,1,{op:'insert',scene:'bridge'},500);const result=applyNamedScenePatches(before,1,[{...descriptor,sentences:['An inserted bridge.']}]);assert.deepEqual(result.scenes.map(scene=>scene.id),['scene-1','scene-2','bridge','exit']);assert.deepEqual(result.scenes.at(-1),before.at(-1));assert.equal(prepareSceneOperation(result.scenes,1,{op:'insert',scene:'another'},500).allowed,false);
});
test('queued scene changes are rejected when their exact target changes or becomes current',()=>{
  const before=scenes(),descriptor=prepareSceneOperation(before,1,{op:'compress',scene:'scene-2'},500),patch={...descriptor,sentences:['Replacement.']};const changed=before.map(scene=>scene.id==='scene-2'?{...scene,sentences:['Newer text.']}:scene);assert.equal(applyNamedScenePatches(changed,1,[patch]).applied.length,0);assert.equal(applyNamedScenePatches(before,4,[patch]).applied.length,0);assert.deepEqual(before,scenes());
});

test('an exit-target revision must preserve exactly one final sentence rather than truncate extra lines',()=>{
  const before=scenes(),descriptor=prepareSceneOperation(before,1,{op:'compress',scene:'exit'},500);const result=applyNamedScenePatches(before,1,[{...descriptor,sentences:['A','Seongsu']}]);assert.equal(result.applied.length,0);assert.deepEqual(result.scenes,before);assert.match(result.skipped[0].reason,/exactly one/u);
});

test('insertions consume only spare unread-story headroom and recheck it at installation',()=>{
  const initial=partitionStoryScenes(['x'.repeat(40)]);const first=prepareSceneOperation(initial,0,{op:'insert',scene:'bridge-a'},100);assert.equal(first.budget_chars,33);const withFirst=applyNamedScenePatches(initial,0,[{...first,sentences:['a'.repeat(33)]}],100).scenes;const second=prepareSceneOperation(withFirst,0,{op:'insert',scene:'bridge-b'},100);assert.equal(second.budget_chars,27);const all=applyNamedScenePatches(withFirst,0,[{...second,sentences:['b'.repeat(27)]}],100);assert.equal(all.scenes.flatMap(scene=>scene.sentences).join('').length,100);assert.equal(applyNamedScenePatches(initial,0,[{...first,sentences:['a'.repeat(33)]}],60).applied.length,0);
  const shrink=partitionStoryScenes(['y'.repeat(80),'x'.repeat(40)]),compression=prepareSceneOperation(shrink,0,{op:'compress',scene:'scene-1'},100);const useful=applyNamedScenePatches(shrink,0,[{...compression,sentences:['z'.repeat(40)]}],10);assert.equal(useful.applied.length,1);assert.equal(useful.scenes[0].sentences[0].length,40);
});
