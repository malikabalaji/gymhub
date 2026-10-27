import React, { useCallback, useEffect, useState } from 'react';
import { Activity, AlertCircle, Calendar, Dumbbell, LogOut, Users } from 'lucide-react';
import { trainersApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import './TrainerDashboard.css';

const panel = { padding: 22, marginBottom: 20 };
const input = { padding: '8px 10px', borderRadius: 7, border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: '#fff', maxWidth: '100%' };

export function TrainerDashboardView({ data, loading = false, error = '', onRetry = () => {}, onCreatePlan = () => {}, onAddExercise = () => {}, onProgress = () => {}, onRemoveExercise = () => {}, onDeletePlan = () => {}, onAttendance = () => {}, onDeleteAttendance = () => {}, logout = () => {} }) {
  if (loading) return <div role="status" style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)' }}><Activity /> Loading trainer dashboard…</div>;
  if (error) return <div role="alert" className="glass-panel trainer-dashboard" style={panel}><AlertCircle /> Unable to load trainer dashboard: {error} <button type="button" onClick={onRetry}>Try again</button></div>;
  if (!data) return null;
  const trainer = data.trainer || {};
  const members = data.members || [];
  const classes = data.classes || [];
  const sessions = data.sessions || [];
  return <main className="trainer-dashboard" style={{ maxWidth: 1200, margin: '0 auto', padding: '30px 20px' }}>
    <header className="glass-panel" style={{ ...panel, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
      <div><span className="badge badge-tier-premium">Trainer Workspace</span><h1 style={{ color: '#fff', margin: '10px 0 4px' }}>Welcome, {trainer.name}</h1><p style={{ color: 'var(--text-muted)', margin: 0 }}>{trainer.id} · {trainer.email}</p>{trainer.specialization?.length > 0 && <p style={{ color: 'var(--text-muted)' }}>Specialization: {trainer.specialization.join(', ')}</p>}</div>
      <button type="button" className="trainer-button-danger trainer-sign-out" onClick={logout}><LogOut size={16} /> Sign Out</button>
    </header>
    <section className="glass-panel" style={panel}><h2 style={{ color: '#fff' }}><Users size={19} /> Assigned Members ({members.length})</h2>
      {members.length ? <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,340px),1fr))', gap: 14 }}>{members.map((member) => <article className="glass-panel-subtle" key={member.member_id} style={{ padding: 16 }}><h3 style={{ color: '#fff', marginTop: 0 }}>{member.name}</h3><p style={{ color: 'var(--text-muted)' }}>{member.member_id} · {member.email}</p><p style={{ color: 'var(--text-muted)' }}>{member.membership?.type || 'Membership'} · {member.city || 'City unavailable'}</p>
        {member.active_plan ? <div><strong style={{ color: '#fff' }}>Plan: {member.active_plan.goal} ({member.active_plan.plan_id})</strong><ul className="trainer-exercise-list">{member.active_plan.exercises?.map((ex) => <li key={`${ex.day}-${ex.exercise_name}`}><span className="trainer-exercise-detail"><strong>{ex.day}</strong><span>{ex.exercise_name}</span><span>{ex.sets}×{ex.reps} · {ex.weight_kg || 0} kg</span></span><span className="trainer-row-actions"><button type="button" className="trainer-button-secondary" onClick={() => onProgress(member.active_plan.plan_id, ex.exercise_name)} aria-label={`Add load to ${ex.exercise_name}`}>+ load</button><button type="button" className="trainer-button-danger" onClick={() => onRemoveExercise(member.active_plan.plan_id, ex.exercise_name)}>Remove</button></span></li>)}</ul><div className="trainer-actions"><button type="button" className="trainer-button-secondary" onClick={() => onAddExercise(member.active_plan.plan_id)}>Add exercise</button><button type="button" className="trainer-button-danger" onClick={() => onDeletePlan(member.active_plan.plan_id)}>Delete plan</button></div></div> : <p style={{ color: 'var(--text-muted)' }}>No active workout plan.</p>}
        <details><summary style={{ color: 'var(--primary)', cursor: 'pointer' }}>{member.active_plan ? 'Replace active plan' : 'Create workout plan'}</summary><PlanForm memberId={member.member_id} onSubmit={onCreatePlan} /></details>
      </article>)}</div> : <p style={{ color: 'var(--text-muted)' }}>No members are currently assigned to this trainer.</p>}</section>
    <section className="glass-panel" style={panel}><h2 style={{ color: '#fff' }}><Calendar size={19} /> Classes & Sessions</h2>
      {!classes.length && !sessions.length ? <p style={{ color: 'var(--text-muted)' }}>No classes or sessions are currently assigned.</p> : <><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,250px),1fr))', gap: 12 }}>{classes.map((c) => <article className="glass-panel-subtle" key={c.class_id} style={{ padding: 14 }}><strong style={{ color: '#fff' }}>{c.class_name}</strong><div style={{ color: 'var(--text-muted)' }}>{c.class_id} · {c.category} · {c.enrollment_count}/{c.capacity} enrolled</div><div style={{ color: 'var(--text-muted)' }}>{c.schedule?.map((slot) => `${slot.day_of_week} ${slot.start_time}-${slot.end_time}`).join(' · ')}</div></article>)}</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,340px),1fr))', gap: 14, marginTop: 16 }}>{sessions.map((session) => <article className="glass-panel-subtle" key={session.session_id} style={{ padding: 16 }}><strong style={{ color: '#fff' }}>{session.class_name} · {session.session_id}</strong><p style={{ color: 'var(--text-muted)' }}>{session.date ? new Date(session.date).toLocaleDateString() : 'Date unavailable'} · {session.start_time || ''}–{session.end_time || ''} · {session.status}</p><AttendanceForm session={session} members={members} onSubmit={onAttendance} />{session.attendance?.length ? <ul className="trainer-attendance-list">{session.attendance.map((a) => <li key={a.member_id}><span>{a.member_name || a.member_id}: {a.status} {a.check_in_time || ''}</span><button type="button" className="trainer-button-danger" onClick={() => onDeleteAttendance(session.session_id, a.member_id)}>Remove</button></li>)}</ul> : <p style={{ color: 'var(--text-muted)' }}>No attendance recorded.</p>}</article>)}</div></>}</section>
  </main>;
}

function PlanForm({ memberId, onSubmit }) {
  const [goal, setGoal] = useState('');
  const [weeks, setWeeks] = useState(4);
  const [exercise, setExercise] = useState('');
  const submit = async (event) => { event.preventDefault(); await onSubmit(memberId, { goal, duration_weeks: Number(weeks), exercises: [{ day: 'Mon', exercise_name: exercise, sets: 3, reps: 10, weight_kg: 0, notes: '' }] }); setGoal(''); setExercise(''); };
  return <form onSubmit={submit} className="trainer-form"><label>Plan goal<input required minLength="2" maxLength="80" placeholder="e.g. Build strength" value={goal} onChange={(e) => setGoal(e.target.value)} style={input} /></label><label>First exercise<input required minLength="1" placeholder="e.g. Squat" value={exercise} onChange={(e) => setExercise(e.target.value)} style={input} /></label><label>Duration (weeks)<input aria-label="Duration in weeks" type="number" min="1" max="52" value={weeks} onChange={(e) => setWeeks(e.target.value)} style={input} /></label><button type="submit">Save workout plan</button></form>;
}

function AttendanceForm({ session, members, onSubmit }) {
  const [memberId, setMemberId] = useState('');
  const [attendanceStatus, setAttendanceStatus] = useState('present');
  return <form onSubmit={(e) => { e.preventDefault(); if (memberId) onSubmit(session.session_id, memberId, { status: attendanceStatus, check_in_time: null }); }} className="trainer-form trainer-attendance-form"><label>Member<select aria-label={`Member for ${session.session_id}`} value={memberId} onChange={(e) => setMemberId(e.target.value)} style={input}><option value="">Select assigned member</option>{members.map((m) => <option key={m.member_id} value={m.member_id}>{m.name}</option>)}</select></label><label>Status<select aria-label="Attendance status" value={attendanceStatus} onChange={(e) => setAttendanceStatus(e.target.value)} style={input}><option>present</option><option>absent</option><option>late</option></select></label><button type="submit" disabled={!memberId || session.status === 'cancelled'}>Record attendance</button></form>;
}

export function TrainerDashboard() {
  const { logout } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const load = useCallback(async () => { setLoading(true); setError(''); try { setData(await trainersApi.getMyDashboard()); } catch (e) { setError(e.message || 'Request failed'); } finally { setLoading(false); } }, []);
  useEffect(() => { load(); }, [load, retry]);
  const action = async (operation) => { try { await operation(); await load(); } catch (e) { setError(e.message || 'Action failed'); } };
  const ask = (label, initial = '') => { const value = window.prompt(label, initial); return value; };
  return <TrainerDashboardView data={data} loading={loading} error={error} onRetry={() => setRetry((n) => n + 1)} logout={logout}
    onCreatePlan={(member, plan) => action(() => trainersApi.createPlan(member, plan))}
    onAddExercise={(plan) => { const name = ask('Exercise name'); if (name) action(() => trainersApi.addExercise(plan, { day: 'Mon', exercise_name: name, sets: 3, reps: 10 })); }}
    onProgress={(plan, name) => { const kg = Number(ask(`Add weight in kg to ${name}`, '2.5')); if (kg > 0) action(() => trainersApi.progressExercise(plan, name, kg)); }}
    onRemoveExercise={(plan, name) => action(() => trainersApi.removeExercise(plan, name))}
    onDeletePlan={(plan) => action(() => trainersApi.deletePlan(plan))}
    onAttendance={(session, member, attendance) => action(() => trainersApi.recordAttendance(session, member, attendance))}
    onDeleteAttendance={(session, member) => action(() => trainersApi.deleteAttendance(session, member))} />;
}
