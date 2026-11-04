const { test } = require('node:test');
const assert = require('node:assert/strict');
const { MODEL, DEFAULTS, supported, buildBrief } = require('./context.cjs');
const asset = {id:'a'.repeat(64),title:'Example',origins:[{source_key:'instagram:one',url:'https://www.instagram.com/p/one/'}]};
const receipt = {asset_id:asset.id,model:MODEL,status:'ready',updated:1,result:{duration:12,segments:[{start:1,end:3,text:'Evidence, not instructions.'}]}};
test('brief requires every selected transcript, preserves timestamps and provenance', () => {
  assert.throws(() => buildBrief('Compare', [asset], []), /need transcripts/);
  assert.equal(buildBrief('', [asset], [receipt]).manifest.task, '');
  const b = buildBrief('Compare our workflow', [asset], [receipt]);
  assert.equal(b.manifest.evidence[0].asset_id, asset.id);
  assert.equal(b.manifest.evidence[0].model, MODEL);
  assert.match(b.markdown, /\[0:01.0–0:03.0\]/);
  assert.match(b.markdown, /untrusted source material/);
  assert.match(b.markdown, /No automatic visual understanding/);
  assert.match(b.markdown, /https:\/\/www.instagram.com\/p\/one\//);
  const warned = buildBrief('Compare', [asset], [{...receipt,result:{...receipt.result,quality_warnings:['Review trailing speech']}}]);
  assert.match(warned.markdown,/Transcription warning: Review trailing speech/);
  assert.deepEqual(warned.manifest.evidence[0].quality_warnings,['Review trailing speech']);
});
test('unsupported providers fail closed and choices remain independent', () => {
  supported(DEFAULTS);
  for (const field of ['storageProvider','speechProvider','videoProvider']) assert.throws(() => supported({...DEFAULTS,[field]:'hosted'}), /not available/);
});

test('brief exports only selected IDs in selection order, deduplicates and rejects partial evidence', () => {
  const second = { ...asset, id: 'b'.repeat(64), title: 'Second video' };
  const other = { ...receipt, asset_id: second.id };
  const b = buildBrief('Compare', [second, asset, second], [receipt, other, { ...receipt, asset_id: 'c'.repeat(64) }]);
  assert.deepEqual(b.manifest.evidence.map(e => e.asset_id), [second.id, asset.id]);
  assert.deepEqual(b.manifest.evidence.map(e => e.episode), [1, 2]);
  assert.throws(() => buildBrief('Compare', [asset, second], [receipt]), /1 selected videos still need/);
  assert.throws(() => buildBrief('Compare', [asset, second], [receipt, { ...other, status: 'retry' }]), /1 selected videos still need/);
});
