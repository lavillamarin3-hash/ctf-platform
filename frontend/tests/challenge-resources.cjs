const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

// Test the exported resource policy without adding a second bundler/test stack.
const sourcePath = path.resolve(__dirname, '../src/lib/challengeResources.ts');
const compiled = ts.transpileModule(fs.readFileSync(sourcePath, 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const fixtureModule = new Module(sourcePath, module);
fixtureModule._compile(compiled, sourcePath);
const { safeResourceUrl, parseChallengeResources, serializeChallengeResources, youtubeEmbedUrl } = fixtureModule.exports;

const checks = [
  ['rejects script/data/protocol-relative/credential-bearing URLs', () => {
    for (const value of ['javascript:alert(1)', 'data:text/html,hello', '//external.invalid/video', 'https://user:password@example.invalid/slides', 'http://example.invalid/video', '/media\\unsafe', '/media/line\nbreak']) {
      assert.equal(safeResourceUrl(value), null, value);
    }
  }],
  ['accepts HTTPS and platform media paths', () => {
    assert.equal(safeResourceUrl('https://example.invalid/slides.pdf'), 'https://example.invalid/slides.pdf');
    assert.equal(safeResourceUrl('/media/slides.pdf'), '/media/slides.pdf');
  }],
  ['round-trip preserves instructions and optional resources', () => {
    const resources = [{ kind: 'video', title: 'SSH introduction', url: 'https://example.invalid/video' }, { kind: 'presentation', title: 'Slides', url: '/media/slides.pdf' }];
    const serialized = serializeChallengeResources('Investigate the assigned target.', resources);
    const parsed = parseChallengeResources(serialized);
    assert.equal(parsed.instructions, 'Investigate the assigned target.');
    assert.deepEqual(parsed.resources, resources);
  }],
  ['malformed/unsafe metadata preserves existing instructor text', () => {
    for (const value of ['Guide\n[CTF_RESOURCES]\nnot-json\n[/CTF_RESOURCES]', 'Guide\n[CTF_RESOURCES]\n[{"kind":"video","title":"Unsafe","url":"javascript:alert(1)"}]\n[/CTF_RESOURCES]']) {
      const parsed = parseChallengeResources(value);
      assert.equal(parsed.instructions, value);
      assert.deepEqual(parsed.resources, []);
    }
  }],
  ['a resource marker mentioned earlier in instructions remains intact', () => {
    const instructions = 'Example marker: [CTF_RESOURCES]\nExplain how metadata works.';
    const resources = [{ kind: 'video', title: 'Lecture', url: 'https://example.invalid/video' }];
    assert.deepEqual(parseChallengeResources(serializeChallengeResources(instructions, resources)), { instructions, resources });
  }],
  ['resource titles containing metadata markers remain valid', () => {
    const resources = [{ kind: 'video', title: 'How [CTF_RESOURCES] works', url: 'https://example.invalid/video' }];
    assert.deepEqual(parseChallengeResources(serializeChallengeResources('Guide', resources)), { instructions: 'Guide', resources });
  }],
  ['serialization rejects unsafe URLs and oversized resource lists', () => {
    assert.throws(() => serializeChallengeResources('Guide', [{ kind: 'video', title: 'Unsafe', url: 'javascript:alert(1)' }]));
    assert.throws(() => serializeChallengeResources('Guide', Array.from({ length: 13 }, () => ({ kind: 'video', title: 'Video', url: 'https://example.invalid/video' }))));
  }],
  ['YouTube embedding accepts validated IDs and rejects lookalike hosts', () => {
    assert.equal(youtubeEmbedUrl('https://youtu.be/dQw4w9WgXcQ'), 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ');
    assert.equal(youtubeEmbedUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ'), 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ');
    assert.equal(youtubeEmbedUrl('https://youtube.com.attacker.invalid/watch?v=dQw4w9WgXcQ'), null);
    assert.equal(youtubeEmbedUrl('https://youtu.be/invalid'), null);
  }],
];

for (const [name, run] of checks) {
  run();
  console.log(`PASS ${name}`);
}
console.log(`${checks.length} resource policy checks passed`);
