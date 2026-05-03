import { api } from './apiClient';

export const performOCR = (base64Image) => api.post('/api/v1/ocr', { base64Image }, { timeout: 60000 });
