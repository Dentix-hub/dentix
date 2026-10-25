import { api } from './apiClient';

export const getOnboardingStatus = async () => {
    const res = await api.get('/api/v1/onboarding/status');
    return res.data;
};

export const dismissOnboarding = async (dismissed = true) => {
    const res = await api.post('/api/v1/onboarding/dismiss', { dismissed });
    return res.data;
};

export const restoreOnboarding = async () => {
    const res = await api.post('/api/v1/onboarding/restore');
    return res.data;
};

export const recordTipSeen = async (tipKey) => {
    const res = await api.post(`/api/v1/onboarding/tips/${encodeURIComponent(tipKey)}`);
    return res.data;
};

export const recordOnboardingEvent = async (eventKey) => {
    const res = await api.post('/api/v1/onboarding/events', { event_key: eventKey });
    return res.data;
};
