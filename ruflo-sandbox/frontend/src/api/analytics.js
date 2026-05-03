import { api } from './apiClient';

export const getProfitability = async (period = '30d') => {
    const response = await api.get('/metrics/profitability', { params: { period } });
    return response.data;
};

export const analyzeClinic = async (stats) => {
    const response = await api.post('/api/v1/admin/ai/analyze-clinic', stats, { timeout: 60000 });
    return response.data;
};
