import test from 'node:test';
import assert from 'node:assert/strict';
import { measureEnvelope } from '../scripts/measure_prompt_envelope.mjs';

test('maximum legal scene, Unicode/JSON escaping and retry histories fit the full-matrix input budget',async()=>{
  const result=await measureEnvelope();
  assert.equal(result.actual_provider_requests,0);
  assert.equal(result.max_input_token_bound,16384);
  assert.equal(result.cases.length,24);
  assert.equal(result.passed,true,JSON.stringify(result.cases.filter(c=>c.status!==200)));
  assert.ok(result.maximum_observed_input_bound<=16384);
});
