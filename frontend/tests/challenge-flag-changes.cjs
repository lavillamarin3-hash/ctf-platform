const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const sourcePath = path.resolve(__dirname, '../src/lib/challengeFlagChanges.ts');
const compiled = ts.transpileModule(fs.readFileSync(sourcePath, 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const fixtureModule = new Module(sourcePath, module);
fixtureModule._compile(compiled, sourcePath);
const { hasFlagDraftChanges, initialFlagTemplate } = fixtureModule.exports;

const original = { id: 7, label: 'Evidence', mode: 'dynamic', template: 'FLAG{run_{{RUN_ID}}_{{RAND}}}', flag_order: 1, is_active: true };
const draft = { ...original, value: '' };
const checks = [
  ['editing a video or instructions does not update an unchanged dynamic flag', () => {
    assert.equal(hasFlagDraftChanges(original, draft, 'LAB-01'), false);
    assert.equal(hasFlagDraftChanges(original, { ...draft, label: ' Evidence ', template: ` ${draft.template} ` }, 'LAB-01'), false);
  }],
  ['empty static value retains the existing secret rather than requesting replacement', () => {
    const flag = { id: 7, label: 'Evidence', flag_order: 1, is_active: true };
    const staticDraft = { ...flag, mode: 'static', template: initialFlagTemplate(flag, 'LAB-01'), value: '   ' };
    assert.equal(hasFlagDraftChanges(flag, staticDraft, 'LAB-01'), false);
    assert.equal(hasFlagDraftChanges(flag, { ...staticDraft, value: 'FLAG{replacement}' }, 'LAB-01'), true);
  }],
  ['editor defaults for legacy metadata do not turn content edits into flag mutations', () => {
    const flag = { ...original, template: null };
    assert.equal(hasFlagDraftChanges(flag, { ...draft, template: initialFlagTemplate(flag, 'LAB-01') }, 'LAB-01'), false);
  }],
  ['explicit runtime or metadata edits remain detectable', () => {
    for (const change of [{ label: 'Another label' }, { flag_order: 2 }, { is_active: false }, { mode: 'static' }, { template: 'FLAG{different_{{RAND}}}' }]) {
      assert.equal(hasFlagDraftChanges(original, { ...draft, ...change }, 'LAB-01'), true, JSON.stringify(change));
    }
  }],
  ['a static-only value is ignored by a dynamic draft', () => {
    assert.equal(hasFlagDraftChanges(original, { ...draft, value: 'Unused value' }, 'LAB-01'), false);
  }],
  ['new or missing flags still require a create/update operation', () => {
    assert.equal(hasFlagDraftChanges(undefined, draft, 'LAB-01'), true);
  }],
];

for (const [name, run] of checks) {
  run();
  console.log(`PASS ${name}`);
}
console.log(`${checks.length} flag edit regression checks passed`);
