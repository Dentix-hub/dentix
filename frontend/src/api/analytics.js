import { api } from './apiClient';

/**
 * Deprecated compatibility adapter for the pre-Finance-V2 profitability
 * contract. Finance/Analytics UI must not use this for headline metrics.
 * Keep it temporarily for compatibility while the backend formula remains
 * unchanged during the deprecation window.
 */
export const getLegacyProfitabilityCompatibility = async (period = '30d') => {
    const response = await api.get('/api/v1/metrics/profitability', { params: { period } });
    return response.data;
};

/** @deprecated Use Finance V2 summary consumers for headline financial truth. */
export const getProfitability = getLegacyProfitabilityCompatibility;

export const getProfitabilityTrend = async (period = '30d') => {
    const response = await api.get('/api/v1/metrics/profitability/trend', { params: { period } });
    return response.data;
};

export const analyzeClinic = async (stats) => {
    const response = await api.post('/api/v1/admin/ai/analyze-clinic', stats, { timeout: 60000 });
    return response.data;
};
