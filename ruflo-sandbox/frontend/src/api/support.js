import { api } from './apiClient';

export const submitFeedback = (data) => api.post('/api/v1/support/feedback', data);
export const getSupportMessages = () => api.get('/api/v1/support/messages');
export const updateMessageStatus = (id, status) => api.put(`/api/v1/support/messages/${id}/status?status=${status}`);
export const deleteSupportMessage = (id) => api.delete(`/api/v1/support/messages/${id}`);
