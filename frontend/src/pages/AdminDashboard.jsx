import React, { useCallback, useEffect, useState } from 'react';
import { Activity, AlertCircle, CreditCard, Database, LogOut, RefreshCw, Users } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { adminApi } from '../api/client';
import { useAuth } from '../context/AuthContext';

const panel = { padding: 22, marginBottom: 20 };
const control = { background: 'var(--bg-main)', color: '#fff', border: '1px solid var(--border-color)', borderRadius: 7, padding: '9px 10px', minWidth: 0 };

export function AdminDashboardView({ data, analytics, analyticsLoading = false, analyticsError = '', loading = false, error = '', onRetry = () => {}, onAction = async () => {}, logout = () => {} }) {
  if (loading) return <div role="status" style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)' }}><Activity /> Loading administration data…</div>;
  if (error && !data) return <div role="alert" className="glass-panel" style={panel}><AlertCircle /> Unable to load administration data: {error} <button onClick={onRetry}>Try again</button></div>;
  if (!data) return null;
  return <main style={{ maxWidth: 1250, margin: '0 auto', padding: '30px 20px', color: '#fff' }}>
    <header className="glass-panel" style={{ ...panel, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
      <div><span className="badge badge-tier-vip">Administrator Portal</span><h1 style={{ margin: '10px 0 4px' }}>Management Console</h1><p style={{ margin: 0, color: 'var(--text-muted)' }}>Operational records loaded from the GymHub API.</p></div>
      <div style={{ display: 'flex', gap: 10 }}><button type="button" onClick={onRetry}><RefreshCw size={15} /> Refresh</button><button type="button" onClick={logout}><LogOut size={15} /> Sign out</button></div>
    </header>
    {error && <p role="alert" style={{ color: '#fca5a5' }}>{error}</p>}
    <section className="glass-panel" style={panel}><h2><Database size={19} /> Collection overview</h2><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 10 }}>{Object.entries(data.summary || {}).map(([name, count]) => <div className="glass-panel-subtle" key={name} style={{ padding: 14 }}><div style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{name.replace('_', ' ')}</div><strong style={{ fontSize: 22 }}>{count}</strong></div>)}</div></section>
    <section className="glass-panel" style={panel}><h2><Users size={19} /> Members ({data.member_count})</h2>
      <Form title="Create member" onSubmit={(v) => onAction(() => adminApi.createMember({ ...v, dob: v.dob, tier: v.tier || 'Basic' }))} fields={[
        ['name','Name'],['email','Email','email'],['phone','10-digit phone'],['dob','Date of birth','date'],['gender','Gender','select',['Male','Female','Other']],['password','Temporary password','password'],['tier','Membership tier','select',['Basic','Premium','VIP']],['city','City'],['pincode','Pincode'],
      ]} />
      <RecordTable columns={['Member','Membership','Trainer','City']} rows={(data.members || []).map((m) => [<><b>{m.name}</b><small>{m.member_id}</small></>, `${m.membership?.type || ''} · ${m.membership?.status || ''}`, m.trainer_id || 'Unassigned', m.address?.city || '—'])} />
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}><QuickAction label="Update membership" fields={['member_id','tier','membership_status']} run={([id,tier,membership_status]) => onAction(() => adminApi.updateMembership(id, { ...(tier && {tier}), ...(membership_status && {membership_status}) }))} /><QuickAction label="Assign trainer" fields={['member_id','trainer_id']} run={([id,trainer]) => onAction(() => adminApi.assignTrainer(id, trainer))} /><QuickAction label="Create invoice" fields={['member_id','billing_period_start','billing_period_end','due_date']} run={([member_id,billing_period_start,billing_period_end,due_date]) => onAction(() => adminApi.createInvoice({member_id,billing_period_start,billing_period_end,due_date}))} /></div>
    </section>
    <section className="glass-panel" style={panel}><h2>Trainers ({data.trainers?.length || 0})</h2>
      <Form title="Create trainer" onSubmit={(v) => onAction(() => adminApi.createTrainer({ ...v, experience_years: Number(v.experience_years), specialization: v.specialization.split(',').map((s) => s.trim()).filter(Boolean) }))} fields={[
        ['name','Name'],['email','Email','email'],['phone','10-digit phone'],['password','Temporary password','password'],['specialization','Specialization (comma separated)'],['certification','Certification'],['experience_years','Years experience','number'],
      ]} />
      <RecordTable columns={['Trainer','Specialization','Experience']} rows={(data.trainers || []).map((t) => [<><b>{t.name}</b><small>{t.trainer_id}</small></>, (t.specialization || []).join(', '), `${t.experience_years ?? 0} years`])} />
      <QuickAction label="Set trainer availability" fields={['trainer_id','day','start_time','end_time']} run={([id,day,start_time,end_time]) => onAction(() => adminApi.setAvailability(id,{day,start_time,end_time}))} />
    </section>
    <section className="glass-panel" style={panel}><h2>Classes & sessions ({data.classes?.length || 0} classes · {data.sessions?.length || 0} sessions)</h2>
      <Form title="Create class" onSubmit={(v) => onAction(() => adminApi.createClass({class_name:v.class_name,category:v.category,trainer_id:v.trainer_id,capacity:Number(v.capacity),schedule:[{day_of_week:v.day_of_week,start_time:v.start_time,end_time:v.end_time,room:v.room}]}))} fields={[
        ['class_name','Class name'],['category','Category'],['trainer_id','Trainer ID'],['capacity','Capacity','number'],['day_of_week','Day','select',['Mon','Tue','Wed','Thu','Fri','Sat','Sun']],['start_time','Start time','time'],['end_time','End time','time'],['room','Room'],
      ]} />
      <RecordTable columns={['Class','Trainer','Capacity','Weekly schedule']} rows={(data.classes || []).map((c) => [<><b>{c.class_name}</b><small>{c.class_id} · {c.category}</small></>, c.trainer_name || c.trainer_id || '—', `${c.enrollment_count}/${c.capacity}`, (c.schedule || []).map((s) => `${s.day_of_week} ${s.start_time}-${s.end_time}`).join(', ') || 'No recurring schedule'])} />
      <QuickAction label="Schedule class session" fields={['class_id','date','start_time','end_time']} run={([id,date,start_time,end_time]) => onAction(() => adminApi.createSession(id,{date,start_time,end_time}))} />
      <RecordTable columns={['Session','Date','Time','Status','Action']} rows={(data.sessions || []).map((s) => [<><b>{s.class_name}</b><small>{s.session_id} · {s.class_id}</small></>, s.date?.slice(0,10), `${s.start_time || ''}–${s.end_time || ''}`, s.status, s.status === 'scheduled' ? <button type="button" onClick={() => onAction(() => adminApi.cancelSession(s.session_id))}>Cancel</button> : '—'])} />
    </section>
    <section className="glass-panel" style={panel}><h2><CreditCard size={19} /> Invoices ({data.payments?.length || 0})</h2><button type="button" onClick={() => onAction(() => adminApi.flagOverdue())}>Flag overdue invoices</button>
      <RecordTable columns={['Invoice','Member','Amount','Due','Status','Action']} rows={(data.payments || []).map((p) => [p.payment_id, p.member_name || '—', `₹${p.amount}`, p.due_date?.slice(0,10), p.status, p.status === 'pending' || p.status === 'overdue' ? <button type="button" onClick={() => confirmManualPaymentUpdate(p.payment_id, (message) => window.confirm(message), (id) => onAction(() => adminApi.recordPayment(id,{mode:'UPI'})))}>Manually mark paid</button> : 'Paid'])} />
    </section>
    <AnalyticsSection data={analytics} loading={analyticsLoading} error={analyticsError} />
  </main>;
}

const chartColors = ['#8b5cf6', '#22d3ee', '#f59e0b', '#34d399', '#f472b6', '#60a5fa'];
export function AnalyticsSection({ data, loading, error }) {
  if (loading) return <section className="glass-panel" style={panel} aria-label="Analytics"><h2>Analytics & reports</h2><p role="status" style={{color:'var(--text-muted)'}}>Loading analytics from database reports…</p></section>;
  if (error) return <section className="glass-panel" style={panel} aria-label="Analytics"><h2>Analytics & reports</h2><p role="alert" style={{color:'#fca5a5'}}>Unable to load analytics: {error}</p></section>;
  if (!data) return null;
  const byTier = (data.membership?.by_tier || []).map((x) => ({name:x._id || 'Unspecified', members:x.count}));
  const revenue = (data.revenue || []).map((x) => ({month:x.month, revenue:x.total_revenue, payments:x.payments}));
  const classes = (data.class_participation || []).map((x) => ({name:x.class_name, attendance:x.attendance_rate_pct, turnout:x.avg_turnout, fill:x.fill_rate_pct}));
  const hours = (data.peak_hours || []).map((x) => ({hour:x.hour, check_ins:x.check_ins}));
  const chartCard = { padding:16, minWidth:0, overflow:'hidden' };
  return <section className="glass-panel" style={panel} aria-label="Analytics"><h2>Analytics & reports</h2><p style={{color:'var(--text-muted)'}}>Computed from existing aggregation pipelines A1–A8 and referral query G2.</p>
    <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,390px),1fr))', gap:14}}>
      <article className="glass-panel-subtle" style={chartCard}><h3>Membership distribution by tier</h3>{byTier.length ? <ResponsiveContainer width="100%" height={260}><PieChart><Pie data={byTier} dataKey="members" nameKey="name" outerRadius={82} label>{byTier.map((entry,i)=><Cell key={entry.name} fill={chartColors[i%chartColors.length]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer> : <EmptyChart />}</article>
      <article className="glass-panel-subtle" style={chartCard}><h3>Monthly collected revenue (₹)</h3>{revenue.length ? <ResponsiveContainer width="100%" height={260}><BarChart data={revenue}><CartesianGrid strokeDasharray="3 3" stroke="#334155"/><XAxis dataKey="month" stroke="#cbd5e1"/><YAxis stroke="#cbd5e1"/><Tooltip/><Bar dataKey="revenue" name="Revenue (₹)" fill="#8b5cf6"/></BarChart></ResponsiveContainer> : <EmptyChart />}</article>
      <article className="glass-panel-subtle" style={chartCard}><h3>Attendance rate by class (%)</h3>{classes.length ? <ResponsiveContainer width="100%" height={260}><BarChart data={classes}><CartesianGrid strokeDasharray="3 3" stroke="#334155"/><XAxis dataKey="name" stroke="#cbd5e1" interval={0} angle={-15} textAnchor="end" height={65}/><YAxis stroke="#cbd5e1"/><Tooltip/><Bar dataKey="attendance" name="Attendance rate (%)" fill="#22d3ee"/></BarChart></ResponsiveContainer> : <EmptyChart />}</article>
      <article className="glass-panel-subtle" style={chartCard}><h3>Peak check-in hours</h3>{hours.length ? <ResponsiveContainer width="100%" height={260}><BarChart data={hours}><CartesianGrid strokeDasharray="3 3" stroke="#334155"/><XAxis dataKey="hour" stroke="#cbd5e1"/><YAxis allowDecimals={false} stroke="#cbd5e1"/><Tooltip/><Bar dataKey="check_ins" name="Check-ins" fill="#34d399"/></BarChart></ResponsiveContainer> : <EmptyChart />}</article>
    </div>
    <div style={{marginTop:18}}><h3>Class participation details</h3><RecordTable columns={['Class','Trainer','Sessions','Average turnout','Fill rate']} rows={classes.map((c) => [c.name, (data.class_participation || []).find((r) => r.class_name === c.name)?.trainer || '—', (data.class_participation || []).find((r) => r.class_name === c.name)?.sessions_held ?? 0, c.turnout, `${c.fill}%`])} /></div>
    <div style={{marginTop:18}}><h3>Members at risk of churning</h3><RecordTable columns={['Member','Tier','Sessions marked','Attendance rate']} rows={(data.at_risk_members || []).map((m) => [`${m.name} (${m.member_id})`,m.tier,m.sessions_marked,`${m.rate_pct}%`])} /></div>
    <div style={{marginTop:18}}><h3>Outstanding dues report</h3><RecordTable columns={['Member','Tier','Bills','Amount due (₹)','Days overdue']} rows={(data.outstanding_dues || []).map((m) => [`${m.name} (${m.member_id})`,m.tier,m.bills,m.amount_due,m.max_days_overdue])} /></div>
    <div style={{marginTop:18}}><h3>Top prescribed exercises</h3><RecordTable columns={['Exercise','Active plans','Average sets','Average weight (kg)']} rows={(data.top_exercises || []).map((x) => [x.exercise,x.plans,x.avg_sets,x.avg_weight_kg ?? '—'])} /></div>
    <div style={{marginTop:18}}><h3>Referral leaders</h3><RecordTable columns={['Member','Direct referrals','Network size','Levels']} rows={(data.top_referrers || []).map((x) => [`${x.name} (${x.member_id})`,x.direct,x.network_size,x.levels])} /></div>
    <ReferralNetwork />
  </section>;
}
function EmptyChart(){return <div style={{height:260,display:'grid',placeItems:'center',color:'var(--text-muted)'}}>No data available for this report.</div>;}

export function confirmManualPaymentUpdate(paymentId, confirmAction, updateAction) {
  const confirmed = confirmAction(`Manually mark invoice ${paymentId} as paid and record payment mode as UPI? This only updates GymHub's invoice record. It does not process or verify a UPI transaction.`);
  if (!confirmed) return false;
  updateAction(paymentId);
  return true;
}

function ReferralNetwork() {
  const [memberId,setMemberId] = useState(''); const [network,setNetwork] = useState(null); const [loading,setLoading] = useState(false); const [error,setError] = useState('');
  const submit = async (event) => { event.preventDefault(); setLoading(true); setError(''); try { setNetwork(await adminApi.referralNetwork(memberId.trim())); } catch (e) { setError(e.message || 'Unable to load referral network'); setNetwork(null); } finally { setLoading(false); } };
  return <div style={{marginTop:18}}><h3>Referral network lookup (G1)</h3><form onSubmit={submit} style={{display:'flex',gap:8,flexWrap:'wrap'}}><label htmlFor="referral-member-id" style={{color:'var(--text-muted)'}}>Member ID</label><input id="referral-member-id" value={memberId} onChange={(e)=>setMemberId(e.target.value)} pattern="MEM[0-9]{4}" required placeholder="MEM1001" style={control}/><button type="submit" disabled={loading}>{loading?'Loading…':'View network'}</button></form>{error && <p role="alert" style={{color:'#fca5a5'}}>{error}</p>}{network && <div style={{marginTop:10}}><p>{network.name} ({network.member_id}) · {network.network_size} referred members</p>{network.network?.length ? <ul>{network.network.map((member)=><li key={member.member_id}>{member.name} ({member.member_id}) · level {member.level}</li>)}</ul> : <p style={{color:'var(--text-muted)'}}>No referral descendants are recorded for this member.</p>}</div>}</div>;
}

function RecordTable({ columns, rows }) {
  if (!rows.length) return <p style={{ color: 'var(--text-muted)' }}>No records returned by the API.</p>;
  return <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}><thead><tr>{columns.map((c) => <th key={c} style={{ padding: 10, color: 'var(--text-muted)', borderBottom: '1px solid var(--border-color)' }}>{c}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j} style={{ padding: 10, borderBottom: '1px solid var(--border-color)' }}>{cell}</td>)}</tr>)}</tbody></table></div>;
}

function Form({ title, fields, onSubmit }) {
  const [values, setValues] = useState({});
  return <details style={{ marginBottom: 14 }}><summary style={{ cursor: 'pointer', color: 'var(--primary)' }}>{title}</summary><form onSubmit={async (e) => { e.preventDefault(); await onSubmit(values); setValues({}); }} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,190px),1fr))', gap: 10, padding: '14px 0' }}>{fields.map(([key,label,type='text',options]) => <label key={key} style={{ display:'grid', gap:5, color:'var(--text-muted)' }}>{label}{type === 'select' ? <select required value={values[key] || ''} onChange={(e) => setValues({...values,[key]:e.target.value})} style={control}><option value="">Select…</option>{options.map((o) => <option key={o}>{o}</option>)}</select> : <input required type={type} min={type === 'number' ? 0 : undefined} value={values[key] || ''} onChange={(e) => setValues({...values,[key]:e.target.value})} style={control} />}</label>)}<button type="submit" style={{ alignSelf:'end' }}>Save</button></form></details>;
}

function QuickAction({ label, fields, run }) {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState({});
  return <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)} style={{ display:'inline-block', margin:'6px 8px 6px 0' }}><summary style={{ cursor:'pointer', color:'var(--primary)' }}>{label}</summary><form onSubmit={async (e) => { e.preventDefault(); await run(fields.map((f) => values[f] || '')); setValues({}); setOpen(false); }} style={{ display:'flex', flexWrap:'wrap', gap:8, padding:10 }}>{fields.map((f) => <input key={f} required placeholder={f.replaceAll('_',' ')} aria-label={f} type={f === 'date' || f.includes('period') || f === 'due_date' ? 'date' : f.includes('time') ? 'time' : 'text'} value={values[f] || ''} onChange={(e) => setValues({...values,[f]:e.target.value})} style={control} />)}<button type="submit">Apply</button></form></details>;
}

export function AdminDashboard() {
  const { logout } = useAuth();
  const [data,setData] = useState(null); const [analytics,setAnalytics] = useState(null); const [loading,setLoading] = useState(true); const [analyticsLoading,setAnalyticsLoading] = useState(true); const [error,setError] = useState(''); const [analyticsError,setAnalyticsError] = useState(''); const [revision,setRevision] = useState(0);
  const load = useCallback(async () => { setLoading(true); setAnalyticsLoading(true); setError(''); setAnalyticsError(''); const [dashboardResult, analyticsResult] = await Promise.allSettled([adminApi.dashboard(), adminApi.analytics()]); if (dashboardResult.status === 'fulfilled') setData(dashboardResult.value); else setError(dashboardResult.reason.message || 'Request failed'); if (analyticsResult.status === 'fulfilled') setAnalytics(analyticsResult.value); else setAnalyticsError(analyticsResult.reason.message || 'Request failed'); setLoading(false); setAnalyticsLoading(false); }, []);
  useEffect(() => { load(); }, [load,revision]);
  const action = async (operation) => { setError(''); try { await operation(); setRevision((n) => n + 1); } catch (e) { setError(e.message || 'Action failed'); } };
  return <AdminDashboardView data={data} analytics={analytics} analyticsLoading={analyticsLoading} analyticsError={analyticsError} loading={loading} error={error} onRetry={() => setRevision((n) => n + 1)} onAction={action} logout={logout} />;
}
