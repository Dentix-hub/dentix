import { api } from './apiClient';

export const sendAIQuery = (text, options = {}) => {
    const { context = null, last_patient_name = null, scribe_mode = false } = options;
    return api.post('/api/v1/ai/query', {
        text,
        context,
        last_patient_name,
        scribe_mode
    }, { skipUnwrap: true });
};
export const getAITools = () => api.get('/api/v1/ai/tools');
