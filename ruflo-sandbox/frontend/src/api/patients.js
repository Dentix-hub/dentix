import { api } from './apiClient';

export const searchPatients = (query) => api.get(`/api/v1/patients/search?q=${query}`);
export const getPatients = () => api.get('/api/v1/patients');
export const getPatient = (id) => api.get(`/api/v1/patients/${id}`);
export const createPatient = (data) => api.post('/api/v1/patients', data);
export const updatePatient = (id, data) => api.put(`/api/v1/patients/${id}`, data);
export const deletePatient = (id) => api.delete(`/api/v1/patients/${id}`);

export const getPatientTeeth = (patientId) => api.get(`/api/v1/patients/${patientId}/tooth_status`);

export const getPatientPayments = (patientId) => api.get(`/api/v1/patients/${patientId}/payments`);


export const getPrescriptions = (patientId) => api.get(`/api/v1/patients/${patientId}/prescriptions`);
export const createPrescription = (data) => api.post('/api/v1/prescriptions', data);
export const deletePrescription = (id) => api.delete(`/api/v1/prescriptions/${id}`);

export const getAttachments = (patientId) => api.get(`/patients/${patientId}/attachments`);
export const uploadAttachment = (patientId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/api/v1/upload?patient_id=${patientId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
export const deleteAttachment = (id) => api.delete(`/api/v1/attachments/${id}`);
