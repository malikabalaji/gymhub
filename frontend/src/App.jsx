import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { MemberDashboard } from './pages/MemberDashboard';
import { TrainerDashboard } from './pages/TrainerDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { UnauthorizedPage } from './pages/UnauthorizedPage';
import { getDashboardPath } from './auth/roleRoutes';

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={getDashboardPath(user.role) || '/login'} replace />;
}

function Layout({ children }) {
  const { user } = useAuth();
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {user && <Navbar />}
      <main style={{ flex: 1 }}>{children}</main>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Layout>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />
            <Route
              path="/member"
              element={
                <ProtectedRoute allowedRoles={['member']}>
                  <MemberDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/trainer"
              element={
                <ProtectedRoute allowedRoles={['trainer']}>
                  <TrainerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRoles={['admin']}>
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<RootRedirect />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
