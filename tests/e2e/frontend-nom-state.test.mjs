import assert from 'node:assert/strict';
import test from 'node:test';

import { NOM_STATES, nomAnnexState } from '../../frontend/src/nom-state.js';

const listed = { annex: { status: 'available' }, requirements: [{ nom: 'NOM-024-SCFI-2013' }] };

test('a fraction or NICO with NOM rows is listed, whatever the annex status', () => {
  assert.equal(nomAnnexState(listed, '85171301'), 'listed');
  assert.equal(nomAnnexState(listed, '8517130100'), 'listed');
  assert.equal(nomAnnexState({ ...listed, annex: { status: 'carried_forward', carried_from: '2026.11.19' } }, '8517.13.01'), 'listed');
});

test('an empty list only means "not listed" when the annex was read', () => {
  assert.equal(nomAnnexState({ annex: { status: 'available' }, requirements: [] }, '85171301'), 'not_listed');
  assert.equal(nomAnnexState({ annex: { status: 'carried_forward', carried_from: '2026.11.19' }, requirements: [] }, '85171301'), 'not_listed_carried');
  assert.equal(nomAnnexState({ annex: { status: 'unavailable' }, requirements: [] }, '85171301'), 'unavailable');
});

test('a missing or unrecognised annex status is unknown, never "not listed"', () => {
  assert.equal(nomAnnexState({ requirements: [] }, '85171301'), 'unknown');
  assert.equal(nomAnnexState({ annex: null, requirements: [] }, '85171301'), 'unknown');
  assert.equal(nomAnnexState({ annex: { status: 'something-new' }, requirements: [] }, '85171301'), 'unknown');
  assert.equal(nomAnnexState(null, '85171301'), 'unknown');
});

test('headings and subheadings are not fractions, so the annex question does not apply', () => {
  assert.equal(nomAnnexState({ annex: { status: 'available' }, requirements: [] }, '8517'), 'not_a_fraction');
  assert.equal(nomAnnexState({ annex: { status: 'available' }, requirements: [] }, '851713'), 'not_a_fraction');
});

test('every state the function returns is declared', () => {
  const seen = new Set([
    nomAnnexState(listed, '85171301'),
    nomAnnexState({ annex: { status: 'available' }, requirements: [] }, '85171301'),
    nomAnnexState({ annex: { status: 'carried_forward' }, requirements: [] }, '85171301'),
    nomAnnexState({ annex: { status: 'unavailable' }, requirements: [] }, '85171301'),
    nomAnnexState({ requirements: [] }, '85171301'),
    nomAnnexState({}, '85'),
  ]);
  assert.deepEqual([...seen].sort(), [...NOM_STATES].sort());
});
