import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function UnauthorizedPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div style={{
      minHeight: '80vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      textAlign: 'center'
    }}>
      <div className="glass-panel" style={{ maxWidth: '440px', padding: '36px 28px' }}>
        <div style={{
          display: 'inline-flex',
          padding: '16px',
          borderRadius: '50%',
          backgroundColor: 'var(--danger-bg)',
          color: '#f87171',
          marginBottom: '20px'
        }}>
          <ShieldAlert size={40} />
        </div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
          Access Forbidden (403)
        </h1>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: '24px' }}>
          Your current role (<strong style={{ color: '#fff' }}>{user?.role || 'Guest'}</strong>) is not authorized to access this resource. Server-side role protection prevented this request.
        </p>
        <button
          onClick={() => navigate('/login')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            backgroundColor: 'var(--primary)',
            color: '#fff',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '0.9rem'
          }}
        >
          <ArrowLeft size={16} />
          <span>Return to Login</span>
        </button>
      </div>
    </div>
  );
}
