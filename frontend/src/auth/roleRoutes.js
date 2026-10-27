export const DASHBOARD_PATHS = Object.freeze({
  member: '/member',
  trainer: '/trainer',
  admin: '/admin',
});

export function getDashboardPath(role) {
  return DASHBOARD_PATHS[role] || null;
}
