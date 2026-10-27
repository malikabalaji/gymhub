import test from 'node:test';
import assert from 'node:assert/strict';
import { getDashboardPath } from '../src/auth/roleRoutes.js';

test('each authenticated role is routed to its own dashboard', () => {
  assert.equal(getDashboardPath('member'), '/member');
  assert.equal(getDashboardPath('trainer'), '/trainer');
  assert.equal(getDashboardPath('admin'), '/admin');
});

test('unknown roles do not receive a dashboard route', () => {
  assert.equal(getDashboardPath('guest'), null);
  assert.equal(getDashboardPath(undefined), null);
});
