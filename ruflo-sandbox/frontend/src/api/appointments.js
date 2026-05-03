import { api } from './apiClient';

export const getAppointments = () => api.get('/api/v1/appointments');
export const createAppointment = (data) => api.post('/api/v1/appointments', data);
export const updateAppointmentStatus = (id, status) => api.put(`/api/v1/appointments/${id}/status?status=${status}`);
export const updateAppointment = (id, data) => api.put(`/api/v1/appointments/${id}`, data);
export const deleteAppointment = (id) => api.delete(`/api/v1/appointments/${id}`);
