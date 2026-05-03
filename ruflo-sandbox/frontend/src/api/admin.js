import { api } from './apiClient';

export const getUsers = () => api.get('/api/v1/users');
export const updateFcmToken = (token) => api.post('/api/v1/users/me/fcm-token', { token });
export const getDoctors = () => api.get('/api/v1/users/doctors');
export const registerUser = (data) => api.post('/api/v1/users/register', null, { params: { username: data.username, password: data.password, role: data.role || 'doctor', permissions: data.permissions || '' } });
export const updateUser = (id, data) => api.put(`/api/v1/users/${id}`, data);
export const deleteUser = (id) => api.delete(`/api/v1/users/${id}`);

export const getSubscriptionPlans = () => api.get('/api/v1/admin/subscriptions/plans');
export const createSubscriptionPlan = (data) => api.post('/api/v1/admin/subscriptions/plans', data);
export const updateSubscriptionPlan = (id, data) => api.put(`/api/v1/admin/subscriptions/plans/${id}`, data);
export const deleteSubscriptionPlan = (id) => api.delete(`/api/v1/admin/subscriptions/plans/${id}`);

export const getAIStats = (period = 'month') => api.get(`/api/v1/ai/admin/stats?period=${period}`);
export const getAILogs = (skip = 0, limit = 20) => api.get(`/api/v1/ai/admin/logs?skip=${skip}&limit=${limit}`);

export const purgeDeletedPatients = (tenantId) => api.delete(`/api/v1/admin/tenants/${tenantId}/purge-deleted-patients`);

export const downloadBackup = () => api.get('/api/v1/settings/backup/download', { responseType: 'blob' });
export const exportTenantBackup = () => api.get('/api/v1/settings/backup/export', { responseType: 'blob' });
export const uploadBackup = (formData) => api.post('/api/v1/settings/backup/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
});
export const getGoogleAuthUrl = () => api.get('/api/v1/settings/backup/auth');
export const disconnectGoogleDrive = () => api.delete('/api/v1/settings/backup/auth');
export const sendGoogleAuthCode = (code) => {
    const formData = new FormData();
    formData.append('code', code);
    return api.post('/api/v1/settings/backup/callback', formData);
};
export const updateBackupSchedule = (frequency) => {
    const formData = new FormData();
    formData.append('frequency', frequency);
    return api.put('/api/v1/settings/backup/schedule', formData);
};
export const getBackupStatus = () => api.get('/api/v1/settings/backup/status');
export const triggerManualBackup = () => api.post('/api/v1/settings/backup/now');
