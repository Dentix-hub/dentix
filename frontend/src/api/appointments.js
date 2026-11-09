import { api } from './apiClient';

export const getAppointments = () => api.get('/api/v1/appointments');
export const createAppointment = (data) => api.post('/api/v1/appointments', data);
export const updateAppointmentStatus = (id, status) => api.put(`/api/v1/appointments/${id}/status?status=${status}`);
export const updateAppointment = (id, data) => api.put(`/api/v1/appointments/${id}`, data);
export const deleteAppointment = (id) => api.delete(`/api/v1/appointments/${id}`);

export const getReceptionNextVisitRequests = (params) => api.get('/api/v1/next-visit-requests', { params });
export const getFollowUpDashboard = (params) => api.get('/api/v1/next-visit-requests/dashboard', { params });
export const scheduleNextVisitRequest = (requestId, data) => api.post(`/api/v1/next-visit-requests/${requestId}/schedule`, data);
export const cancelNextVisitRequest = (requestId, data) => api.post(`/api/v1/next-visit-requests/${requestId}/cancel`, data);
