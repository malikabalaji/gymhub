import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';

test('admin dashboard renders API records and management controls', async () => {
  const vite = await createServer({ configFile: fileURLToPath(new URL('../vite.config.js', import.meta.url)), server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { AdminDashboardView } = await vite.ssrLoadModule('/src/pages/AdminDashboard.jsx');
    const html = renderToStaticMarkup(React.createElement(AdminDashboardView, { data: {
      summary: { members: 1, trainers: 1, classes: 1 }, member_count: 1,
      members: [{ member_id: 'MEM4001', name: 'API Member', membership: { type: 'Premium', status: 'active' }, address: { city: 'Vellore' }, trainer_id: 'TRN01' }],
      trainers: [{ trainer_id: 'TRN01', name: 'API Trainer', specialization: ['Strength'], experience_years: 3 }],
      classes: [{ class_id: 'CLS01', class_name: 'API Class', trainer_name: 'API Trainer', capacity: 10, enrollment_count: 2, schedule: [] }],
      sessions: [{ session_id: 'SES0001', class_id: 'CLS01', class_name: 'API Class', date: '2027-01-01', status: 'scheduled' }],
      payments: [{ payment_id: 'PAY0001', amount: 4000, status: 'pending', due_date: '2027-01-01', member_name: 'API Member' }],
    }, analytics: { membership: { by_tier: [{ _id: 'Premium', count: 1 }], by_status: [], age_groups: [], by_city: [] }, revenue: [{ month: '2026-10', total_revenue: 4000, payments: 1 }], class_participation: [{ class_name: 'API Class', trainer: 'API Trainer', attendance_rate_pct: 80, avg_turnout: 4, fill_rate_pct: 20, sessions_held: 2 }], peak_hours: [{ hour: '09:00', check_ins: 2 }], at_risk_members: [], outstanding_dues: [], top_exercises: [], top_referrers: [] } }));
    for (const text of ['API Member', 'API Trainer', 'API Class', 'MEM4001', 'PAY0001', '₹4000', 'Create member', 'Create class', 'Manually mark paid', 'Analytics &amp; reports', 'Membership distribution by tier', 'Monthly collected revenue', 'Attendance rate by class', 'Peak check-in hours', 'Referral network lookup (G1)']) assert.ok(html.includes(text), `renders ${text}`);
  } finally { await vite.close(); }
});

test('manual invoice status update explains the limit and requires confirmation', async () => {
  const vite = await createServer({ configFile: fileURLToPath(new URL('../vite.config.js', import.meta.url)), server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { confirmManualPaymentUpdate } = await vite.ssrLoadModule('/src/pages/AdminDashboard.jsx');
    let updated = null;
    let prompt = '';
    const cancelled = confirmManualPaymentUpdate('PAY0001', (message) => { prompt = message; return false; }, (id) => { updated = id; });
    assert.equal(cancelled, false);
    assert.equal(updated, null);
    assert.match(prompt, /does not process or verify a UPI transaction/);
    const confirmed = confirmManualPaymentUpdate('PAY0001', () => true, (id) => { updated = id; });
    assert.equal(confirmed, true);
    assert.equal(updated, 'PAY0001');
  } finally { await vite.close(); }
});

test('analytics charts show an explicit empty state when reports have no records', async () => {
  const vite = await createServer({ configFile: fileURLToPath(new URL('../vite.config.js', import.meta.url)), server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { AnalyticsSection } = await vite.ssrLoadModule('/src/pages/AdminDashboard.jsx');
    const html = renderToStaticMarkup(React.createElement(AnalyticsSection, { data: { membership: { by_tier: [] }, revenue: [], class_participation: [], peak_hours: [], at_risk_members: [], outstanding_dues: [], top_exercises: [], top_referrers: [] } }));
    assert.match(html, /No data available for this report/);
    assert.match(html, /Top prescribed exercises/);
    const loading = renderToStaticMarkup(React.createElement(AnalyticsSection, { loading: true }));
    assert.match(loading, /Loading analytics from database reports/);
    const error = renderToStaticMarkup(React.createElement(AnalyticsSection, { error: 'Report unavailable' }));
    assert.match(error, /Report unavailable/);
  } finally { await vite.close(); }
});

test('admin dashboard exposes loading and error states', async () => {
  const vite = await createServer({ configFile: fileURLToPath(new URL('../vite.config.js', import.meta.url)), server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { AdminDashboardView } = await vite.ssrLoadModule('/src/pages/AdminDashboard.jsx');
    const render = (props) => renderToStaticMarkup(React.createElement(AdminDashboardView, props));
    assert.match(render({ loading: true }), /Loading administration data/);
    assert.match(render({ error: 'API offline' }), /API offline/);
  } finally { await vite.close(); }
});
