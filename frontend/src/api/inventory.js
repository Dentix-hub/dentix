import api from './index';

// Warehouses
export const getWarehouses = () => api.get('/api/v1/inventory/warehouses');
export const createWarehouse = (data) => api.post('/api/v1/inventory/warehouses', data);
export const deleteWarehouse = (id) => api.delete(`/api/v1/inventory/warehouses/${id}`);

// Materials
export const getMaterials = () => api.get('/api/v1/inventory/materials');
export const createMaterial = (data) => api.post('/api/v1/inventory/materials', data);
export const updateMaterial = (id, data) => api.put(`/api/v1/inventory/materials/${id}`, data);
export const deleteMaterial = (id) => api.delete(`/api/v1/inventory/materials/${id}`);

// Stock
export const getStockSummary = () => api.get('/api/v1/inventory/stock');
export const receiveStock = (data) => api.post('/api/v1/inventory/receive', data);
export const consumeStock = (items) => api.post('/api/v1/inventory/consume', items);

// Alerts
// Alerts
// Alerts
export const getExpiryAlerts = (days = 30) => api.get('/api/v1/inventory/alerts/expiry?days=' + days);

// Smart Learning
export const openSession = (data) => api.post('/api/v1/inventory/sessions', data);
export const closeSession = (sessionId, data) => api.post(`/api/v1/inventory/sessions/${sessionId}/close`, data);
export const getActiveSessions = () => api.get('/api/v1/inventory/sessions/active');
export const getMaterialStock = (materialId) => api.get(`/api/v1/inventory/materials/${materialId}/stock`);
export const getProcedureWeights = (arg) => {
    const params = typeof arg === 'object' ? arg : { material_id: arg };
    return api.get('/api/v1/inventory/weights', { params });
};
export const setProcedureWeight = (data) => api.post('/api/v1/inventory/weights', data);
export const deleteProcedureWeight = (id) => api.delete(`/api/v1/inventory/weights/${id}`);
