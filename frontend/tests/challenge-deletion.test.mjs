import assert from 'node:assert/strict';
import { test } from 'node:test';
import { canPermanentlyDeleteChallenge } from '../src/lib/challengeDeletion.ts';

const ready = () => ({ isAdmin: true, code: 'CONDOR-01', confirmation: 'CONDOR-01',
  preview: { code: 'CONDOR-01', name: 'Operación Cóndor', counts: {}, blockers: [], can_delete: true },
  loading: false, busy: false });

test('permanent deletion requires exact confirmation with matching fresh preview', () => {
  assert.equal(canPermanentlyDeleteChallenge(ready()), true);
  for (const confirmation of ['', 'condor-01', 'CONDOR-01 ', ' CONDOR-01', 'OTHER-01']) {
    assert.equal(canPermanentlyDeleteChallenge({ ...ready(), confirmation }), false);
  }
  assert.equal(canPermanentlyDeleteChallenge({ ...ready(), code: '', confirmation: '' }), false);
  assert.equal(canPermanentlyDeleteChallenge({ ...ready(), preview: null }), false);
  assert.equal(canPermanentlyDeleteChallenge({ ...ready(), preview: { ...ready().preview, code: 'OTHER-01' } }), false);
});

test('role, active runs and pending requests prevent a permanent delete submission', () => {
  for (const change of [{ isAdmin: false }, { loading: true }, { busy: true }]) {
    assert.equal(canPermanentlyDeleteChallenge({ ...ready(), ...change }), false);
  }
  assert.equal(canPermanentlyDeleteChallenge({ ...ready(), preview: { ...ready().preview, can_delete: false } }), false);
  // A contradictory preview must still fail closed if a blocker is present.
  assert.equal(canPermanentlyDeleteChallenge({ ...ready(), preview: { ...ready().preview,
    blockers: [{ type: 'active_runs', message: 'Hay corridas activas', count: 1 }] } }), false);
});
