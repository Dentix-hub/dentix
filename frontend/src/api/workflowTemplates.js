import { api } from './apiClient';

export const getWorkflowTemplates = (params) => api.get('/api/v1/workflow-templates', { params });
export const getWorkflowTemplate = (codeOrId) => api.get(`/api/v1/workflow-templates/${codeOrId}`);
export const createWorkflowTemplate = (data) => api.post('/api/v1/workflow-templates', data);
export const updateWorkflowTemplate = (codeOrId, data) => api.put(`/api/v1/workflow-templates/${codeOrId}`, data);
export const updateWorkflowTemplateStatus = (id, data) => api.patch(`/api/v1/workflow-templates/${id}/status`, data);
