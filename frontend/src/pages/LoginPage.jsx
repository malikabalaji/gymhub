import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Dumbbell, Lock, User, AlertCircle, ArrowRight, Shield, Award, Users } from 'lucide-react';
import { getDashboardPath } from '../auth/roleRoutes';

export function LoginPage() {
  const [username, setUsername] = useState('MEM1001');
  const [password, setPassword] = useState('Member@1001');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e?.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const user = await login(username, password);
      navigate(getDashboardPath(user.role) || '/login');
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const quickFill = (u, p) => {
    setUsername(u);
    setPassword(p);
    setError('');
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      background: 'radial-gradient(circle at 50% 20%, #1e293b 0%, #0b0f19 80%)'
    }}>
      <div style={{ width: '100%', maxWidth: '440px' }}>
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            backgroundColor: 'var(--primary)',
            color: '#fff',
            marginBottom: '16px',
            boxShadow: '0 0 24px var(--primary-glow)'
          }}>
            <Dumbbell size={30} />
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
            Gym<span style={{ color: 'var(--primary)' }}>Hub</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginTop: '4px' }}>
            Your fitness journey, all in one place.
          </p>
        </div>

        {/* Login Form Card */}
        <div className="glass-panel" style={{ padding: '32px' }}>
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Welcome back</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Sign in with your Member ID, Trainer ID, or Email
            </p>
          </div>

          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '12px 14px',
              backgroundColor: 'var(--danger-bg)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              color: '#f87171',
              fontSize: '0.85rem',
              marginBottom: '20px'
            }}>
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <div>{error}</div>
            </div>
          )}

          <form onSubmit={handleLogin}>
            {/* Username/Email Input */}
            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                User Identifier / Email
              </label>
              <div style={{ position: 'relative' }}>
                <User size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. MEM1001 or admin@gym.com"
                  required
                  style={{
                    width: '100%',
                    padding: '12px 14px 12px 42px',
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '0.92rem',
                    outline: 'none',
                    transition: 'border-color 0.2s'
                  }}
                  onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                  onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'}
                />
              </div>
            </div>

            {/* Password Input */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={18} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  style={{
                    width: '100%',
                    padding: '12px 14px 12px 42px',
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '0.92rem',
                    outline: 'none',
                    transition: 'border-color 0.2s'
                  }}
                  onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                  onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'}
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '12px 20px',
                backgroundColor: 'var(--primary)',
                color: '#fff',
                fontWeight: 700,
                fontSize: '0.95rem',
                borderRadius: '8px',
                boxShadow: '0 4px 12px var(--primary-glow)',
                opacity: isSubmitting ? 0.7 : 1,
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => !isSubmitting && (e.currentTarget.style.backgroundColor = 'var(--primary-hover)')}
              onMouseLeave={(e) => !isSubmitting && (e.currentTarget.style.backgroundColor = 'var(--primary)')}
            >
              <span>{isSubmitting ? 'Signing in...' : 'Sign in to Dashboard'}</span>
              <ArrowRight size={18} />
            </button>
          </form>

          {/* Quick Fill Demo Credentials */}
          <div style={{ marginTop: '28px', paddingTop: '20px', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-dim)', marginBottom: '10px' }}>
              Demo Accounts:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button
                type="button"
                onClick={() => quickFill('MEM1001', 'Member@1001')}
                className="glass-panel-subtle"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 10px',
                  color: 'var(--text-muted)',
                  fontSize: '0.78rem',
                  textAlign: 'left',
                }}
              >
                <Award size={14} color="#f59e0b" />
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>MEM1001</div>
                  <div style={{ fontSize: '0.7rem' }}>VIP Member</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => quickFill('MEM1012', 'Member@1012')}
                className="glass-panel-subtle"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 10px',
                  color: 'var(--text-muted)',
                  fontSize: '0.78rem',
                  textAlign: 'left',
                }}
              >
                <Award size={14} color="#3b82f6" />
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>MEM1012</div>
                  <div style={{ fontSize: '0.7rem' }}>VIP Member</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => quickFill('TRN01', 'Trainer@01')}
                className="glass-panel-subtle"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 10px',
                  color: 'var(--text-muted)',
                  fontSize: '0.78rem',
                  textAlign: 'left',
                }}
              >
                <Users size={14} color="#8b5cf6" />
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>TRN01</div>
                  <div style={{ fontSize: '0.7rem' }}>Trainer</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => quickFill('admin@gym.com', 'Admin@123')}
                className="glass-panel-subtle"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 10px',
                  color: 'var(--text-muted)',
                  fontSize: '0.78rem',
                  textAlign: 'left',
                }}
              >
                <Shield size={14} color="#10b981" />
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>Admin</div>
                  <div style={{ fontSize: '0.7rem' }}>Administrator</div>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
