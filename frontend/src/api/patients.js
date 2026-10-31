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
const attachmentRequestKeys = new WeakMap();
export const uploadAttachment = (patientId, file) => {
    if (!attachmentRequestKeys.has(file)) attachmentRequestKeys.set(file, globalThis.crypto.randomUUID());
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/v1/upload', formData, {
        params: { patient_id: patientId },
        headers: { 'Content-Type': 'multipart/form-data', 'Idempotency-Key': attachmentRequestKeys.get(file) },
    });
};
export const deleteAttachment = (id) => api.delete(`/api/v1/attachments/${id}`);
export const getDriveImageStatus = (filePath) => {
    if (!/^\/api\/v1\/upload\/drive\/[a-f0-9-]+\/content$/i.test(filePath)) throw new Error('Invalid attachment path');
    return api.get(filePath.replace(/\/content$/, '/status'));
};

export const getPatientClinicalPlans = (patientId) => api.get(`/api/v1/patients/${patientId}/clinical-plans`);
export const createPatientClinicalPlan = (patientId, data) => api.post(`/api/v1/patients/${patientId}/clinical-plans`, data);
export const getPatientClinicalPlanCandidates = (patientId, planId) =>
    api.get(`/api/v1/patients/${patientId}/clinical-plans/${planId}/candidate-work-items`);
export const addPatientClinicalPlanPhase = (patientId, planId, data) =>
    api.post(`/api/v1/patients/${patientId}/clinical-plans/${planId}/phases`, data);
export const updatePatientClinicalPlanPhase = (patientId, planId, phaseId, data) =>
    api.patch(`/api/v1/patients/${patientId}/clinical-plans/${planId}/phases/${phaseId}`, data);
export const reorderPatientClinicalPlanPhases = (patientId, planId, phaseIds) =>
    api.post(`/api/v1/patients/${patientId}/clinical-plans/${planId}/phases/reorder`, { phase_ids: phaseIds });
export const deletePatientClinicalPlanPhase = (patientId, planId, phaseId) =>
    api.delete(`/api/v1/patients/${patientId}/clinical-plans/${planId}/phases/${phaseId}`);
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

// Care Session APIs (Slices S18, S19, S20, S21)
export const getActiveCareSession = (patientId) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions/active`);
export const getResumableCareSessionContext = (patientId) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions/resumable`);
export const getPatientCareSessions = (patientId, params = {}) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions`, { params });
export const getCareSession = (patientId, sessionId) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions/${sessionId}`);
export const startCareSession = (patientId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions`, data);
export const finishCareSession = (patientId, sessionId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/finish`, data);
export const transitionCareSession = (patientId, sessionId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/transition`, data);
export const addCareSessionStep = (patientId, sessionId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/steps`, data);
export const updateCareSessionStep = (patientId, sessionId, stepId, data) =>
    api.patch(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/steps/${stepId}`, data);
export const applyCareSessionTemplate = (patientId, sessionId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/steps/from-template`, data);
export const getCareSessionSteps = (patientId, sessionId) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/steps`);
export const recordCareObservation = (patientId, sessionId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/observations`, data);
export const getCareObservations = (patientId, sessionId, params = {}) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/observations`, { params });

// Appointment Integration & Next-Visit Requests (Slice S22 / G11)
export const linkCareSessionAppointment = (patientId, sessionId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/link-appointment`, data);
export const suggestNextVisit = (patientId, sessionId) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/suggest-next-visit`);
export const createNextVisitRequest = (patientId, sessionId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/next-visit-requests`, data);
export const getNextVisitRequests = (patientId, params = {}) =>
    api.get(`/api/v1/patients/${patientId}/next-visit-requests`, { params });

// Clinical Attachment Context Links (Slice S23 / G15)
export const createClinicalAttachmentLink = (patientId, data) =>
    api.post(`/api/v1/patients/${patientId}/clinical-attachment-links`, data);
export const getClinicalAttachmentLinks = (patientId, params = {}) =>
    api.get(`/api/v1/patients/${patientId}/clinical-attachment-links`, { params });
export const getClinicalAttachmentLink = (patientId, linkId) =>
    api.get(`/api/v1/patients/${patientId}/clinical-attachment-links/${linkId}`);
export const deleteClinicalAttachmentLink = (patientId, linkId) =>
    api.delete(`/api/v1/patients/${patientId}/clinical-attachment-links/${linkId}`);

// Status-Only Procedure Command (Slice S25 / G10-M16)
export const updateClinicalWorkItemStatus = (patientId, workItemId, data, options = {}) =>
    api.patch(`/api/v1/patients/${patientId}/clinical-work-items/${workItemId}/status`, data, options);

// Care Session Server Drafts (Slice S25 / G10-M17)
export const getCareSessionDraft = (patientId) =>
    api.get(`/api/v1/patients/${patientId}/care-sessions/draft`);
export const saveCareSessionDraft = (patientId, data) =>
    api.put(`/api/v1/patients/${patientId}/care-sessions/draft`, data);
export const deleteCareSessionDraft = (patientId) =>
    api.delete(`/api/v1/patients/${patientId}/care-sessions/draft`);

// Care Observation Amendment (Slice S25 / G10-M18)
export const amendCareObservation = (patientId, sessionId, observationId, data) =>
    api.post(`/api/v1/patients/${patientId}/care-sessions/${sessionId}/observations/${observationId}/amend`, data);

// Next-Visit Request Lifecycle Actions (Slice S25 / G11-M10..M13)
export const stopNextVisitRequest = (patientId, requestId, data) =>
    api.post(`/api/v1/patients/${patientId}/next-visit-requests/${requestId}/stop`, data);
export const postponeNextVisitRequest = (patientId, requestId, data) =>
    api.post(`/api/v1/patients/${patientId}/next-visit-requests/${requestId}/postpone`, data);
export const resumeNextVisitRequest = (patientId, requestId) =>
    api.post(`/api/v1/patients/${patientId}/next-visit-requests/${requestId}/resume`);
export const handoffNextVisitRequest = (patientId, requestId, data) =>
    api.post(`/api/v1/patients/${patientId}/next-visit-requests/${requestId}/handoff`, data);


