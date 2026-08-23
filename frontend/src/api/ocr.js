import { api } from './apiClient';

// HIGH-05: the backend registers NO OCR route (/api/v1/ocr -> 404).
// This client stays disabled behind an explicit opt-in flag until a
// secured, tenant-aware endpoint exists; otherwise every scan attempt
// would surface a broken feature to users.
export const OCR_ENABLED = import.meta.env.VITE_ENABLE_OCR === 'true';

export const performOCR = (base64Image) => {
    if (!OCR_ENABLED) {
        return Promise.reject(new Error('ميزة اسكان الكارت غير مفعلة في هذه البيئة'));
    }
    return api.post('/api/v1/ocr', { base64Image }, { timeout: 60000 });
};
