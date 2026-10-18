import { api } from './apiClient';

export const searchPatients = (query) => api.get('/api/v1/patients/search', { params: { q: query } });
export const getPatients = () => api.get('/api/v1/patients');
export const getPatientDirectory = ({ q = '', cursor = null, limit = 30, scope = 'all' } = {}) =>
    api.get('/api/v1/patients/directory', {
        params: {
            q: q || undefined,
            cursor: cursor || undefined,
            limit,
            scope,
        },
    });
export const getRecentPatientDirectory = ({ ids = [], q = '' } = {}) =>
    api.get('/api/v1/patients/directory/recent', {
        params: {
            ids: ids.join(','),
            q: q || undefined,
        },
    });
export const getPatient = (id) => api.get(`/api/v1/patients/${id}`);
export const createPatient = (data) => api.post('/api/v1/patients', data);
export const updatePatient = (id, data) => api.put(`/api/v1/patients/${id}`, data);
export const deletePatient = (id) => api.delete(`/api/v1/patients/${id}`);

export const getPatientTeeth = (patientId) => api.get(`/api/v1/patients/${patientId}/tooth_status`);
export const getPatientClinicalWorkspace = (patientId) => api.get(`/api/v1/patients/${patientId}/clinical-workspace`);
export const getPatientPayments = (patientId) => api.get(`/api/v1/patients/${patientId}/payments`);
export const getPatientInvoice = (patientId) => api.get(`/api/v1/patients/${patientId}/invoice`);

export const getPrescriptions = (patientId) => api.get(`/api/v1/patients/${patientId}/prescriptions`);
export const getPrescriptionPrint = (prescriptionId) => api.get(`/api/v1/prescriptions/${prescriptionId}/print`);
export const createPrescription = (data) => api.post('/api/v1/prescriptions', data);
export const deletePrescription = (id) => api.delete(`/api/v1/prescriptions/${id}`);

export const getAttachments = (patientId) => api.get(`/api/v1/patients/${patientId}/attachments`);
export const uploadAttachment = (patientId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/v1/upload', formData, {
        params: { patient_id: patientId },
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};
export const deleteAttachment = (id) => api.delete(`/api/v1/attachments/${id}`);

export const getPatientClinicalPlans = (patientId) => api.get(`/api/v1/patients/${patientId}/clinical-plans`);
export const createPatientClinicalPlan = (patientId, data) => api.post(`/api/v1/patients/${patientId}/clinical-plans`, data);
export const getPatientClinicalPlanCandidates = (patientId, planId) =>
    api.get(`/api/v1/patients/${patientId}/clinical-plans/${planId}/candidate-work-items`);
export const addPatientClinicalPlanPhase = (patientId, planId, data) =>
    api.post(`/api/v1/patients/${patientId}/clinical-plans/${planId}/phases`, data);
export const addPatientClinicalPlanItem = (patientId, planId, phaseId, data) =>
    api.post(`/api/v1/patients/${patientId}/clinical-plans/${planId}/phases/${phaseId}/items`, data);
export const removePatientClinicalPlanItem = (patientId, planId, phaseId, itemId) =>
    api.delete(`/api/v1/patients/${patientId}/clinical-plans/${planId}/phases/${phaseId}/items/${itemId}`);
export const transitionPatientClinicalPlan = (patientId, planId, data) =>
    api.post(`/api/v1/patients/${patientId}/clinical-plans/${planId}/transition`, data);

export const getPatientClinicalWorkItems = (patientId, { includeCorrected = false } = {}) =>
    api.get(`/api/v1/patients/${patientId}/clinical-work-items`, { params: { include_corrected: includeCorrected } });
export const createPatientClinicalFinding = (patientId, data, headers = {}) =>
    api.post(`/api/v1/patients/${patientId}/clinical-findings`, data, { headers });
export const createPatientClinicalFindingsBulk = (patientId, data, headers = {}) =>
    api.post(`/api/v1/patients/${patientId}/clinical-findings/bulk`, data, { headers });
export const createPatientClinicalProcedure = (patientId, data, headers = {}) =>
    api.post(`/api/v1/patients/${patientId}/clinical-procedures`, data, { headers });
export const createPatientClinicalProceduresBulk = (patientId, data, headers = {}) =>
    api.post(`/api/v1/patients/${patientId}/clinical-procedures/bulk`, data, { headers });
export const updatePatientClinicalWorkItem = (patientId, workItemId, data) =>
    api.patch(`/api/v1/patients/${patientId}/clinical-work-items/${workItemId}`, data);
export const correctPatientClinicalWorkItem = (patientId, workItemId, data, headers = {}) =>
    api.post(`/api/v1/patients/${patientId}/clinical-work-items/${workItemId}/correct`, data, { headers });

