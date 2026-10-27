import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';

test('trainer dashboard renders API-backed member, plan, class, and attendance data', async () => {
  const vite = await createServer({ configFile: fileURLToPath(new URL('../vite.config.js', import.meta.url)), server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { TrainerDashboardView } = await vite.ssrLoadModule('/src/pages/TrainerDashboard.jsx');
    const markup = renderToStaticMarkup(React.createElement(TrainerDashboardView, { data: {
      trainer: { id: 'TRN01', name: 'Priya Menon', email: 'priya@example.test', specialization: ['Strength'] },
      members: [{ member_id: 'MEM1001', name: 'Ravi Member', email: 'ravi@example.test', active_plan: { plan_id: 'WP0123', goal: 'Strength', exercises: [{ day: 'Mon', exercise_name: 'Squat', sets: 3, reps: 8, weight_kg: 30 }] } }],
      classes: [{ class_id: 'CLS01', class_name: 'Strength Lab', category: 'Strength', capacity: 12, enrollment_count: 1, schedule: [] }],
      sessions: [{ session_id: 'SES0123', class_name: 'Strength Lab', date: '2026-10-27', status: 'scheduled', attendance: [{ member_id: 'MEM1001', member_name: 'Ravi Member', status: 'present' }] }],
    } }));
    for (const value of ['Priya Menon', 'MEM1001', 'Strength', 'Squat', 'Strength Lab', 'SES0123', 'present']) assert.ok(markup.includes(value), `renders ${value}`);
    assert.ok(markup.includes('Record attendance'));
  } finally { await vite.close(); }
});

test('trainer dashboard presents explicit loading, empty, and error states', async () => {
  const vite = await createServer({ configFile: fileURLToPath(new URL('../vite.config.js', import.meta.url)), server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { TrainerDashboardView } = await vite.ssrLoadModule('/src/pages/TrainerDashboard.jsx');
    const render = (props) => renderToStaticMarkup(React.createElement(TrainerDashboardView, props));
    assert.match(render({ loading: true }), /Loading trainer dashboard/);
    assert.match(render({ error: 'Network unavailable' }), /Network unavailable/);
    assert.match(render({ data: { trainer: { name: 'A Trainer' }, members: [], classes: [], sessions: [] } }), /No members are currently assigned/);
    assert.match(render({ data: { trainer: { name: 'A Trainer' }, members: [], classes: [], sessions: [] } }), /No classes or sessions are currently assigned/);
  } finally { await vite.close(); }
});
