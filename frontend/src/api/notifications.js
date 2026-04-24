import { api } from './apiClient';

export const getNotifications = () => api.get('/api/v1/notifications');
export const markNotificationRead = (id) => api.post(`/api/v1/notifications/${id}/read`);
export const dismissNotification = (id) => api.post(`/api/v1/notifications/${id}/dismiss`);
export const broadcastNotification = (data) => api.post('/api/v1/notifications/broadcast', data);
export const deleteNotification = (id) => api.delete(`/api/v1/notifications/${id}`);
