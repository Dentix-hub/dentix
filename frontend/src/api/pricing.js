import { api } from './apiClient';

export const getPriceLists = () => api.get('/api/v1/price-lists');
export const getDefaultPriceList = () => api.get('/api/v1/price-lists/default');
export const getPriceList = (id) => api.get(`/api/v1/price-lists/${id}`);
export const createPriceList = (data) => api.post('/api/v1/price-lists', data);
export const updatePriceList = (id, data) => api.put(`/api/v1/price-lists/${id}`, data);
export const deactivatePriceList = (id) => api.delete(`/api/v1/price-lists/${id}`);
export const addPriceListItem = (listId, data) => api.post(`/api/v1/price-lists/${listId}/items`, data);
export const getProcedurePrices = (procedureId) => api.get(`/api/v1/price-lists/procedure/${procedureId}/prices`);

export const getInsuranceProviders = () => api.get('/api/v1/insurance-providers');
export const getInsuranceProvider = (id) => api.get(`/api/v1/insurance-providers/${id}`);
export const createInsuranceProvider = (data) => api.post('/api/v1/insurance-providers', data);
export const updateInsuranceProvider = (id, data) => api.put(`/api/v1/insurance-providers/${id}`, data);
export const deactivateInsuranceProvider = (id) => api.delete(`/api/v1/insurance-providers/${id}`);
