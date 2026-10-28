import assert from 'node:assert/strict';
import { test } from 'node:test';
import { learningPolicyDraft, remainingLearningPoints, serializeLearningPolicy } from '../src/lib/learningPolicy.ts';

const policy = () => ({ duration_minutes: 45, expired_points_percent: 35,
  hints: [{ title: 'Una orientación', content: 'Relaciona las dos fuentes.', penalty_percent: 15 },
    { title: 'Una herramienta', content: 'Usa el identificador compartido.', penalty_percent: 20 }], solution_text: 'La explicación privada.' });

test('round trips a custom instructor policy without replacing hint costs or duration', () => {
  assert.deepEqual(serializeLearningPolicy(learningPolicyDraft(policy())), policy());
});

test('new challenge defaults require instructor hint contents', () => {
  const draft = learningPolicyDraft();
  assert.equal(draft.duration_minutes, '60');
  assert.equal(draft.expired_points_percent, '25');
  assert.equal(draft.hints.length, 1);
  assert.throws(() => serializeLearningPolicy(draft), /Completa el título y el texto/);
});

test('rejects missing, fractional or out of range policy values and excessive combined discounts', () => {
  for (const invalid of ['', '1.5', '-1', '1441', 'Infinity']) {
    assert.throws(() => serializeLearningPolicy({ ...learningPolicyDraft(policy()), duration_minutes: invalid }));
  }
  const draft = learningPolicyDraft(policy());
  draft.hints[0].penalty_percent = '90';
  assert.throws(() => serializeLearningPolicy(draft), /suma de los descuentos/);
  draft.hints = [];
  const noHints = serializeLearningPolicy({ ...draft, timer_enabled: false });
  assert.deepEqual(noHints.hints, []);
  assert.equal(noHints.timer_enabled, false);
});

test('permits zero cost hints and zero or full expiry credit with one hint', () => {
  const draft = learningPolicyDraft(policy());
  draft.hints = [{ title: 'Gratis', content: 'Ayuda inicial.', penalty_percent: '0' }];
  for (const percent of ['0', '100']) {
    const saved = serializeLearningPolicy({ ...draft, expired_points_percent: percent, solution_text: '  ' });
    assert.equal(saved.expired_points_percent, Number(percent));
    assert.equal(saved.solution_text, null);
  }
});

test('point preview rounds down for each configured percentage, including assisted credit', () => {
  assert.equal(remainingLearningPoints(155, 85), 131);
  assert.equal(remainingLearningPoints(155, 65), 100);
  assert.equal(remainingLearningPoints(155, 35), 54);
  assert.equal(remainingLearningPoints(155, -10), 0);
});

test('private text validation trims whitespace and rejects oversized hint and solution values', () => {
  const draft = learningPolicyDraft(policy());
  draft.hints[0].content = '   ';
  assert.throws(() => serializeLearningPolicy(draft), /Completa/);
  draft.hints[0].content = 'x'.repeat(4001);
  assert.throws(() => serializeLearningPolicy(draft), /4000/);
  const fresh = learningPolicyDraft(policy());
  assert.throws(() => serializeLearningPolicy({ ...fresh, solution_text: 'x'.repeat(12001) }), /12000/);
});
