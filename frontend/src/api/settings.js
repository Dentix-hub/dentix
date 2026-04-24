import { api } from './apiClient';

export const getTenantSettings = () => api.get('/api/v1/settings/tenant');
export const updateTenantSettings = (data) => api.put('/api/v1/settings/tenant', data);
