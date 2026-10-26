import React, { useEffect, useState } from 'react';
import { membersApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  User, Award, AlertCircle, Dumbbell, Calendar, Clock,
  CreditCard, CheckCircle2, XCircle, ArrowUpRight, Activity, MapPin, Phone
} from 'lucide-react';

export function MemberDashboard() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        const data = await membersApi.getMyDashboard();
        setDashboard(data);
      } catch (err) {
        setError(err.message || 'Failed to fetch member dashboard data');
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', color: 'var(--text-muted)' }}>
        <Activity size={24} style={{ animation: 'spin 1s linear infinite', marginRight: '10px' }} />
        <span>Loading member dashboard data from backend...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ maxWidth: '800px', margin: '40px auto', padding: '24px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '16px 20px',
          backgroundColor: 'var(--danger-bg)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '10px',
          color: '#f87171'
        }}>
          <AlertCircle size={22} />
          <div>
            <div style={{ fontWeight: 700 }}>Unable to load dashboard</div>
            <div style={{ fontSize: '0.88rem', opacity: 0.9 }}>{error}</div>
          </div>
        </div>
      </div>
    );
  }

  const { profile, summary, active_plan, enrolled_classes, recent_attendance, unpaid_dues } = dashboard;
  const tier = profile?.membership?.type || 'Basic';
  const status = profile?.membership?.status || 'active';

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
      {/* Top Banner / Welcome */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px',
        marginBottom: '28px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <h1 style={{ fontSize: '1.85rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
              Welcome back, {profile.name}
            </h1>
            <span className={`badge ${
              tier === 'VIP' ? 'badge-tier-vip' : tier === 'Premium' ? 'badge-tier-premium' : 'badge-tier-basic'
            }`}>
              {tier} Member
            </span>
            <span className={`badge badge-${status}`}>
              {status}
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>ID: <strong style={{ color: '#fff' }}>{profile.member_id}</strong></span>
            <span>•</span>
            <MapPin size={14} style={{ display: 'inline', verticalAlign: '-2px' }} />
            <span>{profile.address?.city || 'Vellore'}</span>
          </p>
        </div>

        {summary?.unpaid_amount > 0 && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '10px 16px',
            backgroundColor: 'var(--warning-bg)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: '10px',
            color: '#fbbf24',
            fontSize: '0.88rem'
          }}>
            <AlertCircle size={18} />
            <span>Outstanding Dues: <strong>₹{summary.unpaid_amount.toLocaleString('en-IN')}</strong></span>
          </div>
        )}
      </div>

      {/* 4 Summary Stat Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '18px',
        marginBottom: '28px'
      }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Membership Tier</span>
            <Award size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff' }}>{tier}</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Valid to {profile.membership?.end_date ? new Date(profile.membership.end_date).toLocaleDateString() : 'N/A'}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Assigned Trainer</span>
            <User size={18} color="#3b82f6" />
          </div>
          <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {summary?.trainer || 'Not Assigned'}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Personal Fitness Coach
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Current Goal</span>
            <Dumbbell size={18} color="#8b5cf6" />
          </div>
          <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fff' }}>
            {active_plan?.goal || 'General Fitness'}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {active_plan ? `${active_plan.duration_weeks}-week prescription` : 'No active plan'}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-dim)', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Outstanding Dues</span>
            <CreditCard size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: summary?.unpaid_amount > 0 ? '#fbbf24' : '#34d399' }}>
            ₹{(summary?.unpaid_amount || 0).toLocaleString('en-IN')}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {unpaid_dues?.length ? `${unpaid_dues.length} pending bill(s)` : 'All accounts settled'}
          </div>
        </div>
      </div>

      {/* Main Grid: Workout Plan & Classes */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
        gap: '24px',
        marginBottom: '28px'
      }}>
        {/* Workout Plan Card */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Dumbbell size={20} color="var(--primary)" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>Active Workout Routine</h2>
            </div>
            {active_plan && (
              <span className="badge badge-active">{active_plan.status}</span>
            )}
          </div>

          {active_plan ? (
            <div>
              <div style={{ display: 'flex', gap: '16px', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                <span>Prescribed by: <strong style={{ color: '#fff' }}>{active_plan.trainer_name}</strong></span>
                <span>•</span>
                <span>Plan ID: <strong style={{ color: '#fff' }}>{active_plan.plan_id}</strong></span>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-dim)' }}>
                      <th style={{ padding: '8px 12px' }}>Day</th>
                      <th style={{ padding: '8px 12px' }}>Exercise</th>
                      <th style={{ padding: '8px 12px', textAlign: 'center' }}>Sets</th>
                      <th style={{ padding: '8px 12px', textAlign: 'center' }}>Reps</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {active_plan.exercises?.map((ex, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: 'var(--primary)' }}>{ex.day}</td>
                        <td style={{ padding: '10px 12px', color: '#fff', fontWeight: 500 }}>{ex.exercise_name}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>{ex.sets}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>{ex.reps}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 600, color: '#f8fafc' }}>
                          {ex.weight_kg ? `${ex.weight_kg} kg` : 'Bodyweight'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No active workout plan assigned. Please speak to your trainer.
            </div>
          )}
        </div>

        {/* Enrolled Classes */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
            <Calendar size={20} color="var(--primary)" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>Enrolled Group Classes</h2>
          </div>

          {enrolled_classes && enrolled_classes.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {enrolled_classes.map((c) => (
                <div key={c.class_id} className="glass-panel-subtle" style={{ padding: '14px 18px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ fontSize: '0.98rem', fontWeight: 700, color: '#fff' }}>{c.class_name}</div>
                    <span style={{ fontSize: '0.78rem', color: 'var(--primary)', fontWeight: 600 }}>{c.class_id}</span>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    Trainer: <span style={{ color: '#f1f5f9' }}>{c.trainer_name}</span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {c.schedule?.map((slot, sIdx) => (
                      <span key={sIdx} style={{
                        fontSize: '0.75rem',
                        padding: '4px 8px',
                        backgroundColor: 'var(--bg-card)',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)',
                        color: 'var(--text-muted)'
                      }}>
                        {slot.day_of_week} • {slot.start_time} - {slot.end_time} ({slot.room})
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
              You are not currently enrolled in any group fitness classes.
            </div>
          )}
        </div>
      </div>

      {/* Secondary Grid: Attendance & Invoices */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '24px'
      }}>
        {/* Attendance History */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
            <Clock size={20} color="var(--primary)" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>Recent Check-in History</h2>
          </div>

          {recent_attendance && recent_attendance.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {recent_attendance.map((att, i) => (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  fontSize: '0.85rem'
                }}>
                  <div>
                    <div style={{ color: '#fff', fontWeight: 600 }}>
                      {att.date ? new Date(att.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'N/A'}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      Check-in: {att.check_in_time || 'No timestamp'}
                    </div>
                  </div>
                  <span className={`badge badge-${att.status}`}>
                    {att.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No recent attendance recorded.
            </div>
          )}
        </div>

        {/* Invoices and Dues */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
            <CreditCard size={20} color="var(--primary)" />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>Pending & Overdue Bills</h2>
          </div>

          {unpaid_dues && unpaid_dues.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {unpaid_dues.map((d, i) => (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  backgroundColor: 'var(--bg-main)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px'
                }}>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>
                      Invoice {d.payment_id}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Due: {d.due_date ? new Date(d.due_date).toLocaleDateString() : 'N/A'}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f87171' }}>
                      ₹{d.amount.toLocaleString('en-IN')}
                    </div>
                    <span className={`badge badge-${d.status}`} style={{ marginTop: '4px' }}>
                      {d.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              padding: '30px',
              textAlign: 'center',
              color: 'var(--text-muted)'
            }}>
              <CheckCircle2 size={36} color="#10b981" style={{ marginBottom: '10px' }} />
              <div style={{ fontWeight: 600, color: '#fff' }}>Account in Good Standing</div>
              <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>No pending or overdue membership dues.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
