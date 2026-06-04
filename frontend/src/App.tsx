import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import { useDispatch } from 'react-redux';
import { fetchMe } from './store/slices/authSlice';
import type { AppDispatch } from './store';

import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/shared/ProtectedRoute';

import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ClientsPage from './pages/compliance/ClientsPage';
import ClientDetailPage from './pages/compliance/ClientDetailPage';
import AMLMonitoringPage from './pages/compliance/AMLMonitoringPage';
import KYCFormPage from './pages/client/KYCFormPage';
import DocumentsPage from './pages/client/DocumentsPage';
import AdminPage from './pages/admin/AdminPage';
import AnalyticsPage from './pages/analytics/AnalyticsPage';
import IncidentsPage from './pages/incidents/IncidentsPage';
import IncidentDetailPage from './pages/incidents/IncidentDetailPage';
import RuleTuningPage from './pages/rules/RuleTuningPage';
import IncidentDashboardPage from './pages/analytics/IncidentDashboardPage';
import PrivacyPage from './pages/privacy/PrivacyPage';
import PrivacyAdminPage from './pages/privacy/PrivacyAdminPage';
import SecurityPage from './pages/security/SecurityPage';
import MyActivityPage from './pages/monitoring/MyActivityPage';
import AuditDashboardPage from './pages/monitoring/AuditDashboardPage';

function AppRoutes() {
  const dispatch = useDispatch<AppDispatch>();

  useEffect(() => {
    if (localStorage.getItem('access_token')) {
      dispatch(fetchMe());
    }
  }, [dispatch]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />

        {/* Client routes */}
        <Route path="kyc" element={<ProtectedRoute allowedRoles={['client']}><KYCFormPage /></ProtectedRoute>} />
        <Route path="documents" element={<ProtectedRoute allowedRoles={['client']}><DocumentsPage /></ProtectedRoute>} />

        {/* Privacy — available to any authenticated user (self-service) */}
        <Route path="privacy" element={<PrivacyPage />} />
        {/* Account security (MFA) — any authenticated user */}
        <Route path="security" element={<SecurityPage />} />
        {/* My activity (devices/logins) — any authenticated user */}
        <Route path="my-activity" element={<MyActivityPage />} />

        {/* Staff routes */}
        <Route path="clients" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <ClientsPage />
          </ProtectedRoute>
        } />
        <Route path="clients/:id" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <ClientDetailPage />
          </ProtectedRoute>
        } />
        <Route path="aml" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <AMLMonitoringPage />
          </ProtectedRoute>
        } />
        <Route path="analytics" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <AnalyticsPage />
          </ProtectedRoute>
        } />

        {/* Incident Management */}
        <Route path="incidents" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <IncidentsPage />
          </ProtectedRoute>
        } />
        <Route path="incidents/:id" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <IncidentDetailPage />
          </ProtectedRoute>
        } />
        <Route path="rules" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <RuleTuningPage />
          </ProtectedRoute>
        } />
        <Route path="incident-analytics" element={
          <ProtectedRoute allowedRoles={['compliance_officer', 'risk_analyst', 'admin']}>
            <IncidentDashboardPage />
          </ProtectedRoute>
        } />

        {/* Admin */}
        <Route path="admin" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminPage />
          </ProtectedRoute>
        } />
        <Route path="privacy-admin" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <PrivacyAdminPage />
          </ProtectedRoute>
        } />
        <Route path="audit-dashboard" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AuditDashboardPage />
          </ProtectedRoute>
        } />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </Provider>
  );
}
