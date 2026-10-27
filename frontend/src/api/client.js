/**
 * API client helper with automatic Bearer token injection and error parsing.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '/api';

export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem('gym_auth_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const url = `${BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
      // Clear token if expired or unauthorized
      localStorage.removeItem('gym_auth_token');
      localStorage.removeItem('gym_auth_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      throw new Error('Session expired or unauthorized. Please log in again.');
    }

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMsg = data?.detail || `HTTP ${res.status}: ${res.statusText}`;
      throw new Error(errorMsg);
    }

    return data;
  } catch (err) {
    throw err;
  }
}

export const authApi = {
  login: (username, password) =>
    apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  getMe: () => apiRequest('/auth/me'),
  getMeta: () => apiRequest('/meta'),
};

export const membersApi = {
  getMyDashboard: () => apiRequest('/members/me/dashboard'),
};

export const trainersApi = {
  getMyDashboard: () => apiRequest('/trainers/me/dashboard'),
  createPlan: (memberId, plan) => apiRequest(`/trainers/me/members/${encodeURIComponent(memberId)}/plans`, { method: 'POST', body: JSON.stringify(plan) }),
  addExercise: (planId, exercise) => apiRequest(`/trainers/me/plans/${encodeURIComponent(planId)}/exercises`, { method: 'POST', body: JSON.stringify(exercise) }),
  progressExercise: (planId, name, addKg) => apiRequest(`/trainers/me/plans/${encodeURIComponent(planId)}/exercises/${encodeURIComponent(name)}/progress`, { method: 'PATCH', body: JSON.stringify({ add_kg: addKg }) }),
  removeExercise: (planId, name) => apiRequest(`/trainers/me/plans/${encodeURIComponent(planId)}/exercises/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  deletePlan: (planId) => apiRequest(`/trainers/me/plans/${encodeURIComponent(planId)}`, { method: 'DELETE' }),
  getAttendance: (sessionId) => apiRequest(`/trainers/me/sessions/${encodeURIComponent(sessionId)}/attendance`),
  recordAttendance: (sessionId, memberId, attendance) => apiRequest(`/trainers/me/sessions/${encodeURIComponent(sessionId)}/attendance/${encodeURIComponent(memberId)}`, { method: 'POST', body: JSON.stringify(attendance) }),
  deleteAttendance: (sessionId, memberId) => apiRequest(`/trainers/me/sessions/${encodeURIComponent(sessionId)}/attendance/${encodeURIComponent(memberId)}`, { method: 'DELETE' }),
};

export const adminApi = {
  dashboard: (page = 1) => apiRequest(`/admin/dashboard?page=${page}`),
  analytics: () => apiRequest('/admin/analytics'),
  referralNetwork: (memberId) => apiRequest(`/admin/analytics/referrals/${encodeURIComponent(memberId)}`),
  createMember: (body) => apiRequest('/admin/members', { method: 'POST', body: JSON.stringify(body) }),
  updateMembership: (id, body) => apiRequest(`/admin/members/${encodeURIComponent(id)}/membership`, { method: 'PATCH', body: JSON.stringify(body) }),
  assignTrainer: (id, trainer_id) => apiRequest(`/admin/members/${encodeURIComponent(id)}/trainer`, { method: 'PUT', body: JSON.stringify({ trainer_id }) }),
  createTrainer: (body) => apiRequest('/admin/trainers', { method: 'POST', body: JSON.stringify(body) }),
  setAvailability: (id, body) => apiRequest(`/admin/trainers/${encodeURIComponent(id)}/availability`, { method: 'PUT', body: JSON.stringify(body) }),
  createClass: (body) => apiRequest('/admin/classes', { method: 'POST', body: JSON.stringify(body) }),
  createSession: (id, body) => apiRequest(`/admin/classes/${encodeURIComponent(id)}/sessions`, { method: 'POST', body: JSON.stringify(body) }),
  cancelSession: (id) => apiRequest(`/admin/sessions/${encodeURIComponent(id)}/cancel`, { method: 'POST' }),
  createInvoice: (body) => apiRequest('/admin/invoices', { method: 'POST', body: JSON.stringify(body) }),
  recordPayment: (id, body) => apiRequest(`/admin/invoices/${encodeURIComponent(id)}/record-payment`, { method: 'POST', body: JSON.stringify(body) }),
  flagOverdue: () => apiRequest('/admin/invoices/flag-overdue', { method: 'POST' }),
};
