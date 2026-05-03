import { api } from './apiClient';

export const getPatientTreatments = (patientId) => api.get(`/api/v1/patients/${patientId}/treatments`);
export const createTreatment = (data) => api.post('/api/v1/treatments', data);
export const updateTreatment = (id, data) => api.put(`/api/v1/treatments/${id}`, data);
export const deleteTreatment = (id) => api.delete(`/api/v1/treatments/${id}`);
export const updateToothStatus = (data) => api.post('/api/v1/treatments/tooth_status', data);

export const addTreatmentSession = (treatmentId, data) => api.post(`/api/v1/treatments/${treatmentId}/sessions`, data);

export const deleteTreatmentSession = (treatmentId, sessionId) => api.delete(`/api/v1/treatments/${treatmentId}/sessions/${sessionId}`);
