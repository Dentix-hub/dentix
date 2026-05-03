import { api } from './apiClient';

export const getLaboratories = () => api.get('/api/v1/laboratories');
export const createLaboratory = (data) => api.post('/api/v1/laboratories', data);
export const updateLaboratory = (id, data) => api.put(`/api/v1/laboratories/${id}`, data);
export const deleteLaboratory = (id) => api.delete(`/api/v1/laboratories/${id}`);

export const getLabOrders = (params = {}) => api.get('/api/v1/lab-orders', { params });
export const getPatientLabOrders = (patientId) => api.get(`/api/v1/patients/${patientId}/lab_orders`);
export const createLabOrder = (data) => api.post('/api/v1/lab-orders', data);
export const updateLabOrder = (id, data) => api.put(`/api/v1/lab-orders/${id}`, data);
export const deleteLabOrder = (id) => api.delete(`/api/v1/lab-orders/${id}`);
export const getLabOrdersStats = () => api.get('/api/v1/lab-orders/stats/summary');
export const getLabStats = (labId) => api.get(`/api/v1/laboratories/${labId}/stats`);
export const getLabPayments = (labId) => api.get(`/api/v1/laboratories/${labId}/payments`);
export const createLabPayment = (labId, data) => api.post(`/api/v1/laboratories/${labId}/payments`, data);
