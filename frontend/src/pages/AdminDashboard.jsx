import React from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, Database, CreditCard, BarChart3, LogOut, Info } from 'lucide-react';

export function AdminDashboard() {
  const { user, logout } = useAuth();

  return (
    <div style={{ maxWidth: '900px', margin: '40px auto', padding: '0 24px' }}>
      {/* Header Banner */}
      <div className="glass-panel" style={{ padding: '32px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className="badge badge-tier-vip">Administrator Portal</span>
              <span className="badge badge-active">Privileged Session</span>
            </div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
              Welcome, {user?.name || 'Administrator'}
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
              Admin ID: <strong style={{ color: '#fff' }}>{user?.id}</strong> • Email: <strong style={{ color: '#fff' }}>{user?.email}</strong>
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
      <div className="glass-panel" style={{ padding: '28px', borderLeft: '4px solid #f59e0b' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
          <div style={{
            padding: '10px',
            borderRadius: '10px',
            backgroundColor: 'var(--warning-bg)',
            color: 'var(--warning)',
            flexShrink: 0
          }}>
            <Info size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
              Admin Management Console — Scheduled for Stage 3
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', lineHeight: 1.6, marginBottom: '20px' }}>
              Your administrator credentials have been successfully authenticated using bcrypt and JWT. In Stage 1, the focus is on member services. Administrative management controls and analytics will be enabled in Stage 3 and Stage 4.
            </p>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '14px',
              marginBottom: '20px'
            }}>
              <div className="glass-panel-subtle" style={{ padding: '16px' }}>
                <Database size={20} color="#f59e0b" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.95rem' }}>Collection CRUD</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Manage members, trainers, group classes, and session schedules.
                </div>
              </div>

              <div className="glass-panel-subtle" style={{ padding: '16px' }}>
                <CreditCard size={20} color="#f59e0b" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.95rem' }}>Billing & Overdue</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Execute nightly overdue sweeps and process membership renewals (T1 transaction).
                </div>
              </div>

              <div className="glass-panel-subtle" style={{ padding: '16px' }}>
                <BarChart3 size={20} color="#f59e0b" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 700, color: '#fff', fontSize: '0.95rem' }}>Analytics & Reports</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Pipelines A1–A8 and G1–G2 referral network graph visualizations.
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
