import { api } from './apiClient';

export const getPatientClinicalCharges = (patientId) =>
    api.get(`/api/v1/patients/${patientId}/clinical-charges`);

export const invoiceClinicalCharge = (chargeId, data = {}) =>
    api.post(`/api/v1/clinical-charges/${chargeId}/invoice`, data);

export const voidClinicalCharge = (chargeId, data = {}) =>
    api.post(`/api/v1/clinical-charges/${chargeId}/void`, data);
