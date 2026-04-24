import { api } from './apiClient';

export const getProcedures = () => api.get('/api/v1/procedures');
export const createProcedure = (data) => api.post('/api/v1/procedures', data);
export const updateProcedure = (id, data) => api.put(`/api/v1/procedures/${id}`, data);
export const deleteProcedure = (id) => api.delete(`/api/v1/procedures/${id}`);
