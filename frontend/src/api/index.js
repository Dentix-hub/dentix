// Barrel file - re-export all API modules for backward compatibility
import { api, API_URL } from './apiClient';

// Export core client
export { api, API_URL };
export default api;

// Export all functional modules
export * from './auth';
export * from './patients';
export * from './appointments';
export * from './billing';
export * from './admin';
export * from './analytics';
export * from './financials';
export * from './inventory';
export * from './labs';
export * from './procedures';
export * from './notifications';
export * from './support';
export * from './medications';
export * from './settings';
export * from './pricing';
export * from './ocr';
export * from './ai';

