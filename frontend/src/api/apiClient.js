import axios from 'axios';
import { logger } from '../utils/logger';

const getApiUrl = () => {
    if (import.meta.env.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL;
    }

    const hostname = window.location.hostname;
    const protocol = window.location.protocol;

    if (hostname.includes('vercel.app')) {
        if (hostname.toLowerCase().includes('staging') ||
            hostname.toLowerCase().includes('preview') ||
            hostname.toLowerCase().includes('-git-')) {
            return 'https://dentix-dentix-staging.hf.space';
        }
        return 'https://dentix-dentix.hf.space';
    }

    if (hostname === 'localhost' || hostname === '127.0.0.1' || /^(\d{1,3}\.){3}\d{1,3}$/.test(hostname)) {
        return `${protocol}//${hostname}:8000`;
    }

    return '';
};

export const API_URL = getApiUrl();

if (import.meta.env.DEV) {
    logger.log(`%c[API_DIAGNOSTIC] Active API URL: ${API_URL || 'Same Origin (' + window.location.origin + ')'}`, 'color: #00ff00; font-weight: bold;');
}

// withCredentials: true ensures httpOnly cookies are sent/received automatically
export const api = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    withCredentials: true,
});

// CSRF Token handling - read from cookie and add to state-changing requests
function getCsrfTokenFromCookie() {
    const name = 'csrf_token=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const ca = decodedCookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }
    return null;
}

// Request interceptor: Add CSRF token to state-changing requests
api.interceptors.request.use(config => {
    // Only add CSRF token for state-changing methods
    const method = (config.method || 'get').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        // Skip for auth endpoints (they are exempted on backend)
        const url = config.url || '';
        const exemptPaths = [
            '/api/v1/auth/token',
            '/api/v1/auth/refresh',
            '/api/v1/auth/logout',
            '/api/v1/auth/login/2fa',
            '/api/v1/auth/register',
            '/api/v1/auth/forgot-password',
            '/api/v1/auth/reset-password',
            '/api/v1/auth/verify-reset-token',
            '/api/v1/upload',
        ];
        const isExempt = exemptPaths.some(p => url.includes(p));

        if (!isExempt) {
            const csrfToken = getCsrfTokenFromCookie();
            if (csrfToken) {
                config.headers = config.headers || {};
                config.headers['X-CSRF-Token'] = csrfToken;
            }
        }
    }
    return config;
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });

    failedQueue = [];
};

api.interceptors.response.use(
    response => {
        if (response.data instanceof Blob) {
            return response;
        }

        if (response.config?.skipUnwrap) {
            return response;
        }

        if (response.data && typeof response.data === 'object' && 'success' in response.data && 'data' in response.data) {
            if (response.data.pagination && response.data.data !== null && typeof response.data.data === 'object') {
                try {
                    Object.defineProperty(response.data.data, '_pagination', {
                        value: response.data.pagination,
                        writable: true,
                        enumerable: false,
                        configurable: true
                    });
                } catch (e) {
                    response.data.data._pagination = response.data.pagination;
                }
            }
            response.data = response.data.data;
        }

        return response;
    },
    async error => {
        const originalRequest = error.config;

        if (error.response) {
            logger.error('[API] Request failed:', error.response.status, originalRequest.url);
        }

        // Handle 403 - CSRF token validation failed
        if (error.response?.status === 403 && error.response?.data?.detail?.includes?.('CSRF')) {
            logger.warn('[API] CSRF token validation failed, CSRF token may have expired');
            // Could attempt to refresh the page or get a new CSRF token
            // For now, just reject and let the UI handle it
            return Promise.reject(error);
        }

        // Handle 401 - attempt token refresh via httpOnly cookie
        if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/api/v1/auth/token') && !originalRequest.url?.includes('/api/v1/auth/refresh')) {
            // Silent auth mode: don't redirect, let the caller handle the error
            if (originalRequest._silentAuth) {
                return Promise.reject(error);
            }
            const debugMsg = error.response?.data?.detail || "Unknown Auth Error";

            if (isRefreshing) {
                return new Promise(function (resolve, reject) {
                    failedQueue.push({ resolve, reject });
                }).then(() => {
                    // Cookie will be sent automatically, just retry
                    return api(originalRequest);
                }).catch(err => {
                    return Promise.reject(err);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                logger.log('[API] Attempting token refresh via httpOnly cookie...');
                // Backend reads refresh_token from httpOnly cookie automatically
                const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, null, {
                    withCredentials: true,
                    timeout: 10000
                });

                // New access_token is set via httpOnly cookie by backend
                // No need to call setToken - cookies handle it

                processQueue(null, response.data.access_token);
                return api(originalRequest);
            } catch (err) {
                processQueue(err, null);

                const errorDetail = err.response?.data?.detail;
                if (errorDetail && typeof errorDetail === 'string' && (errorDetail.includes('جهاز آخر') || errorDetail.includes('Session Mismatch'))) {
                    window.location.href = '/login?reason=session_mismatch';
                    return new Promise(() => { });
                }

                window.location.href = '/';
                return Promise.reject(err);
            } finally {
                isRefreshing = false;
            }
        }

        if (error.response?.status === 500) {
            logger.error('[API] Server Error:', error.response?.data?.detail || 'Internal Server Error');
        }

        return Promise.reject(error);
    }
);