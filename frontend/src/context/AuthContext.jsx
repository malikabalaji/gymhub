import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('gym_auth_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('gym_auth_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function verifySession() {
      const savedToken = localStorage.getItem('gym_auth_token');
      if (savedToken) {
        try {
          const freshUser = await authApi.getMe();
          setUser(freshUser);
          localStorage.setItem('gym_auth_user', JSON.stringify(freshUser));
        } catch (err) {
          console.warn('Session verification failed:', err.message);
          logout();
        }
      }
      setLoading(false);
    }
    verifySession();
  }, []);

  const login = async (username, password) => {
    const data = await authApi.login(username, password);
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('gym_auth_token', data.access_token);
    localStorage.setItem('gym_auth_user', JSON.stringify(data.user));
    return data.user;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('gym_auth_token');
    localStorage.removeItem('gym_auth_user');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
