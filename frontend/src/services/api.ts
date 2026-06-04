import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  login: (email: string, password: string, mfaCode?: string) =>
    api.post('/auth/login', { email, password, mfa_code: mfaCode }),
  register: (data: { email: string; password: string; full_name: string; role?: string }) =>
    api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  updateMe: (data: object) => api.put('/auth/me', data),
  logout: () => api.post('/auth/logout'),
  mfaSetup: () => api.post('/auth/mfa/setup'),
  mfaVerify: (code: string) => api.post('/auth/mfa/verify', { code }),
  mfaDisable: (code: string) => api.post('/auth/mfa/disable', { code }),
  passwordResetRequest: (email: string) => api.post('/auth/password-reset/request', { email }),
  passwordResetConfirm: (token: string, newPassword: string) =>
    api.post('/auth/password-reset/confirm', { token, new_password: newPassword }),
};

// Clients
export const clientsApi = {
  createProfile: (data: object) => api.post('/clients/profile', data),
  getMyProfile: () => api.get('/clients/profile/me'),
  updateMyProfile: (data: object) => api.put('/clients/profile/me', data),
  listClients: (params?: object) => api.get('/clients/', { params }),
  getClient: (id: number) => api.get(`/clients/${id}`),
  triggerRiskScore: (id: number) => api.post(`/clients/${id}/risk-score`),
  getRiskAssessment: (id: number) => api.get(`/clients/${id}/risk-assessment`),
};

// Documents
export const documentsApi = {
  upload: (formData: FormData) =>
    api.post('/documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getMyDocuments: () => api.get('/documents/my'),
  getClientDocuments: (clientId: number) => api.get(`/documents/client/${clientId}`),
  reviewDocument: (id: number, data: object) => api.put(`/documents/${id}/review`, data),
  download: (id: number) => api.get(`/documents/${id}/download`, { responseType: 'blob' }),
};

// Transactions
export const transactionsApi = {
  create: (data: object) => api.post('/transactions/', data),
  getMyTransactions: (params?: object) => api.get('/transactions/my', { params }),
  getClientTransactions: (clientId: number, params?: object) =>
    api.get(`/transactions/client/${clientId}`, { params }),
  getSummary: () => api.get('/transactions/stats/summary'),
};

// AML
export const amlApi = {
  listAlerts: (params?: object) => api.get('/aml/alerts', { params }),
  getAlert: (id: number) => api.get(`/aml/alerts/${id}`),
  updateAlert: (id: number, data: object) => api.put(`/aml/alerts/${id}`, data),
  getStats: () => api.get('/aml/stats'),
};

// Reviews
export const reviewsApi = {
  createReview: (data: object) => api.post('/reviews/', data),
  decide: (id: number, data: object) => api.put(`/reviews/${id}/decide`, data),
  getPending: () => api.get('/reviews/pending'),
};

// Analytics
export const analyticsApi = {
  getDashboard: () => api.get('/analytics/dashboard'),
  getMonthlyTrend: () => api.get('/analytics/monthly-trend'),
  getIncidentMetrics: () => api.get('/analytics/incidents'),
  getFalsePositiveMetrics: () => api.get('/analytics/false-positives'),
  getRiskMetrics: () => api.get('/analytics/risk'),
};

// Incident Management
export const incidentsApi = {
  list: (params?: object) => api.get('/incidents/', { params }),
  get: (id: number) => api.get(`/incidents/${id}`),
  listAnalysts: () => api.get('/incidents/meta/analysts'),
  assign: (id: number, data: { assigned_to: number; note?: string }) =>
    api.post(`/incidents/${id}/assign`, data),
  updateStatus: (id: number, data: { status: string; resolution_notes?: string }) =>
    api.put(`/incidents/${id}/status`, data),
  escalate: (id: number) => api.post(`/incidents/${id}/escalate`),
  addComment: (id: number, comment: string) =>
    api.post(`/incidents/${id}/comments`, { comment }),
  addRiskAssessment: (id: number, data: object) =>
    api.post(`/incidents/${id}/risk-assessment`, data),
  classify: (id: number, data: object) => api.post(`/incidents/${id}/classify`, data),
};

// Detection Rule Tuning
export const detectionRulesApi = {
  list: () => api.get('/detection-rules/'),
  get: (id: number) => api.get(`/detection-rules/${id}`),
  falsePositives: (id: number) => api.get(`/detection-rules/${id}/false-positives`),
  history: (id: number) => api.get(`/detection-rules/${id}/history`),
  tune: (id: number, data: { new_parameters: object; change_description: string; is_active?: boolean }) =>
    api.post(`/detection-rules/${id}/tune`, data),
};

// Privacy & GDPR
export const privacyApi = {
  exportMyData: () => api.get('/privacy/my-data/export'),
  listConsents: () => api.get('/privacy/consents'),
  upsertConsent: (data: { purpose: string; granted: boolean; policy_version?: string }) =>
    api.post('/privacy/consents', data),
  createRequest: (data: { request_type: string; details?: string }) =>
    api.post('/privacy/requests', data),
  myRequests: () => api.get('/privacy/requests'),
  allRequests: () => api.get('/privacy/requests/all'),
  processRequest: (id: number, data: { status: string; resolution_notes?: string }) =>
    api.post(`/privacy/requests/${id}/process`, data),
  runRetentionPurge: () => api.post('/privacy/retention/purge'),
  auditIntegrity: () => api.get('/privacy/audit/integrity'),
};

// Admin
export const adminApi = {
  listUsers: (params?: object) => api.get('/admin/users', { params }),
  createUser: (data: object) => api.post('/admin/users', data),
  updateUser: (id: number, data: object) => api.put(`/admin/users/${id}`, data),
  deactivateUser: (id: number) => api.delete(`/admin/users/${id}`),
  getAuditLogs: (params?: object) => api.get('/admin/audit-logs', { params }),
  getStats: () => api.get('/admin/stats'),
};

export default api;
