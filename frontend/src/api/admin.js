import { api } from './apiClient';

export const getUsers = () => api.get('/api/v1/users');
export const updateFcmToken = (token) => api.post('/api/v1/users/me/fcm-token', { token });
export const getDoctors = () => api.get('/api/v1/users/doctors');
export const registerUser = (data) =>
    api.post('/api/v1/users/register', {
        username: data.username,
        password: data.password,
        email: data.email ?? null,
        full_name: data.full_name ?? null,
        role: data.role || 'doctor',
        permissions: data.permissions || '',
        patient_visibility_mode: data.patient_visibility_mode || 'all_assigned',
    });
export const updateUser = (id, data) => api.put(`/api/v1/users/${id}`, data);
export const deleteUser = (id) => api.delete(`/api/v1/users/${id}`);

export const getSubscriptionPlans = () => api.get('/api/v1/admin/subscriptions/plans');
export const createSubscriptionPlan = (data) => api.post('/api/v1/admin/subscriptions/plans', data);
export const updateSubscriptionPlan = (id, data) => api.put(`/api/v1/admin/subscriptions/plans/${id}`, data);
export const deleteSubscriptionPlan = (id) => api.delete(`/api/v1/admin/subscriptions/plans/${id}`);
export const getSubscriptionPayments = () => api.get('/api/v1/admin/subscriptions/payments');
export const recordSubscriptionPayment = (data) => api.post('/api/v1/admin/subscriptions/payments', data);
export const deleteSubscriptionPayment = (id) => api.delete(`/api/v1/admin/subscriptions/payments/${id}`);

export const getAIStats = (period = 'month') => api.get(`/api/v1/ai/admin/stats?period=${period}`);
export const getAILogs = (skip = 0, limit = 20) => api.get(`/api/v1/ai/admin/logs?skip=${skip}&limit=${limit}`);

export const purgeDeletedPatients = (tenantId) => api.delete(`/api/v1/admin/tenants/${tenantId}/purge-deleted-patients`);

export const downloadBackup = () => api.get('/api/v1/settings/backup/download', { responseType: 'blob' });
export const exportTenantBackup = () => api.get('/api/v1/settings/backup/export', { responseType: 'blob' });
export const exportTenantBackupXlsx = () => api.get('/api/v1/settings/backup/export-xlsx', { responseType: 'blob' });
export const downloadClinicArchive = () => api.get('/api/v1/settings/backup/archive', { responseType: 'blob' });
export const previewClinicRestore = (file) => api.post('/api/v1/settings/backup/preview', file, {
    headers: { 'Content-Type': file.name.toLowerCase().endsWith('.json') ? 'application/json' : 'application/octet-stream' },
});
export const confirmClinicRestore = (payload) => api.post('/api/v1/settings/backup/confirm', payload);
export const getClinicRestoreStatus = (id) => api.get(`/api/v1/settings/backup/operations/${encodeURIComponent(id)}`);
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
