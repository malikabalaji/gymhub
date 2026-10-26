import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Dumbbell, LogOut, User, Calendar, ShieldCheck } from 'lucide-react';

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '16px 28px',
      backgroundColor: 'var(--bg-card)',
      borderBottom: '1px solid var(--border-color)',
      position: 'sticky',
      top: 0,
      zIndex: 50
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          backgroundColor: 'var(--primary)',
          color: '#fff',
          padding: '8px',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 12px var(--primary-glow)'
        }}>
          <Dumbbell size={22} />
        </div>
        <div>
          <div style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
            Gym<span style={{ color: 'var(--primary)' }}>Hub</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: 600 }}>
            Membership Management System
          </div>
        </div>
      </div>

      {/* Middle Pill: Fixed Reference Date */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 14px',
        backgroundColor: 'var(--bg-main)',
        borderRadius: '20px',
        border: '1px solid var(--border-color)',
        fontSize: '0.8rem',
        color: 'var(--text-muted)'
      }}>
        <Calendar size={14} color="var(--primary)" />
        <span>System Date: <strong style={{ color: '#fff' }}>24 Sep 2026</strong></span>
      </div>

      {/* User profile & Logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#fff' }}>
                {user.name}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                <span className={`badge ${
                  user.role === 'admin' ? 'badge-tier-vip' :
                  user.role === 'trainer' ? 'badge-tier-premium' : 'badge-tier-basic'
                }`}>
                  {user.role} ({user.id})
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              title="Logout"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: '#f87171',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: 600,
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.2)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)'}
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
