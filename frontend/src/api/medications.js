import { api } from './apiClient';

export const getSavedMedications = () => api.get('/api/v1/medications/saved');
export const saveMedication = (data) => api.post('/api/v1/medications/saved', data);
export const deleteSavedMedication = (id) => api.delete(`/api/v1/medications/saved/${id}`);
