import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Dumbbell, Users, Calendar, Clock, LogOut, Info, ArrowRight } from 'lucide-react';

export function TrainerDashboard() {
  const { user, logout } = useAuth();

  return (
    <div style={{ maxWidth: '900px', margin: '40px auto', padding: '0 24px' }}>
      {/* Header Banner */}
      <div className="glass-panel" style={{ padding: '32px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-tier-premium">Trainer Workspace</span>
              <span className="badge badge-active">Active Session</span>
            </div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
              Welcome, {user?.name || 'Trainer'}
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
              Trainer ID: <strong style={{ color: '#fff' }}>{user?.id}</strong> • Account: <strong style={{ color: '#fff' }}>{user?.email}</strong>
            </p>
          </div>

          <button
            onClick={logout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              color: '#f87171',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '0.88rem'
            }}
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Stage Roadmap Notice */}
      <div className="glass-panel" style={{ padding: '28px', borderLeft: '4px solid var(--purple)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
          <div style={{
            padding: '10px',
            borderRadius: '10px',
            backgroundColor: 'var(--purple-bg)',
            color: 'var(--purple)',
            flexShrink: 0
          }}>
            <Info size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
              Trainer Dashboard — Scheduled for Stage 2
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', lineHeight: 1.6, marginBottom: '20px' }}>
              Your authentication as a certified trainer has succeeded. In Stage 1, the end-to-end flow is focused on member authentication and the member dashboard. Trainer management modules will be enabled in the upcoming Stage 2.
            </p>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '14px',
              marginBottom: '20px'
            }}>
              <div className="glass-panel-subtle" style={{ padding: '16px' }}>
                <Users size={20} color="var(--purple)" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.95rem' }}>Assigned Members</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                  View assigned athletes, member progress, and active subscriptions.
                </div>
              </div>

              <div className="glass-panel-subtle" style={{ padding: '16px' }}>
                <Dumbbell size={20} color="var(--purple)" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.95rem' }}>Workout Routines</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Create and adjust personalized training plans and progressive overload.
                </div>
              </div>

              <div className="glass-panel-subtle" style={{ padding: '16px' }}>
                <Clock size={20} color="var(--purple)" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.95rem' }}>Class Attendance</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Conduct scheduled session roll calls with atomic commits (T2 transaction).
                </div>
              </div>
            </div>

            <div style={{
              fontSize: '0.82rem',
              color: 'var(--text-dim)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <span>Server-side RBAC protection active • Member resources are isolated</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
