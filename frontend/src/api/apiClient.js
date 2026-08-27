import axios from 'axios';
import { logger } from '../utils/logger';
import { useAuthStore } from '../store/auth.store';
import { queryClient } from '../lib/queryClient';
import { resolveApiBaseUrl } from './apiOrigin';
import {
    CONNECTION_STATES,
    useConnectivityStore,
} from '../pwa/connectivity/connectivityStore';

const getApiUrl = () => {
    const hostname = window.location.hostname;
    const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;

    if (configuredBaseUrl) {
        return resolveApiBaseUrl(configuredBaseUrl, window.location);
    }

    if (hostname.includes('vercel.app')) {
        if (hostname.toLowerCase().includes('staging') ||
            hostname.toLowerCase().includes('preview') ||
            hostname.toLowerCase().includes('-git-')) {
            return 'https://dentix-dentix-staging.hf.space';
        }
        return 'https://dentix-dentix.hf.space';
    }

    return resolveApiBaseUrl(undefined, window.location);
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

// Offline write safety (plan §10.4): while the backend is confirmed
// unreachable, state-changing requests fail immediately with a clear error
// instead of hanging or appearing to succeed. Form state is preserved because
// mutations simply reject; nothing is ever queued for silent replay.
export const OFFLINE_WRITE_BLOCKED_EVENT = 'dentix:offline-write-blocked';

export function createOfflineWriteError() {
    const error = new Error('OFFLINE_WRITE_BLOCKED');
    error.code = 'OFFLINE_WRITE_BLOCKED';
    error.isOfflineWriteBlock = true;
    return error;
}

const OFFLINE_EXEMPT_PATHS = [
    '/api/v1/auth/token',
    '/api/v1/auth/refresh',
    '/api/v1/auth/logout',
    '/api/v1/auth/login/2fa',
];

// Request interceptor: Add CSRF token to state-changing requests
api.interceptors.request.use(config => {
    const method = (config.method || 'get').toUpperCase();

    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)
        && useConnectivityStore.getState().state === CONNECTION_STATES.OFFLINE
        && !config._allowOffline) {
        const url = config.url || '';
        const isExempt = OFFLINE_EXEMPT_PATHS.some(p => url.includes(p));
        if (!isExempt) {
            logger.warn('[API] Write blocked while offline:', method, url);
            // The user-facing toast is shown by the globally mounted
            // NetworkStatusBanner (keeps i18n out of the api import chain).
            window.dispatchEvent(new CustomEvent(OFFLINE_WRITE_BLOCKED_EVENT));
            return Promise.reject(createOfflineWriteError());
        }
    }

    // Only add CSRF token for state-changing methods
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

    // Attach temporary Impersonation Bearer token when active
    const impersonationToken = typeof window !== 'undefined' && window.sessionStorage
        ? window.sessionStorage.getItem('dentix_impersonation_token') || window.sessionStorage.getItem('admin_token')
        : null;

    if (impersonationToken && impersonationToken !== 'impersonating' && !config.headers?.Authorization) {
        config.headers = config.headers || {};
        config.headers['Authorization'] = `Bearer ${impersonationToken}`;
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
        const isAuthRequest = originalRequest?.url?.includes('/api/v1/auth/token')
            || originalRequest?.url?.includes('/api/v1/auth/refresh');

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
        if (error.response?.status === 401 && !originalRequest?._retry && !isAuthRequest) {
            if (isRefreshing) {
                // Ensure a queued request cannot start a second refresh loop if its
                // retry is also rejected after the active refresh completes.
                originalRequest._retry = true;
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
                    useAuthStore.getState().setLoading(true);

                    try {
                        await axios.post(`${API_URL}/api/v1/auth/logout`, null, {
                            withCredentials: true,
                            timeout: 5000,
                        });
                    } catch (logoutError) {
                        logger.warn('[API] Best-effort logout failed after session mismatch', logoutError);
                    }

                    try {
                        await queryClient.cancelQueries();
                    } catch (queryCancellationError) {
                        logger.warn('[API] Query cancellation failed during session cleanup', queryCancellationError);
                    }
                    queryClient.clear();

                    try {
                        const { useTenantStore } = await import('../store/tenant.store');
                        useTenantStore.getState().clearTenant();
                    } catch (tenantCleanupError) {
                        logger.warn('[API] Tenant cleanup failed after session mismatch', tenantCleanupError);
                    }

                    sessionStorage.removeItem('dentix_impersonation_token');
                    sessionStorage.removeItem('dentix_impersonation_tenant');
                    sessionStorage.removeItem('dentix_impersonation_user');
                    sessionStorage.removeItem('dentix_impersonation_scope');
                    sessionStorage.removeItem('admin_token');
                    sessionStorage.removeItem('print_rx_data');
                    useAuthStore.getState().clearAuth();
                    window.location.replace('/login?reason=session_mismatch');
                    return Promise.reject(err);
                }

                // The in-memory user can outlive expired/revoked httpOnly cookies.
                // Clear it immediately so authenticated polling components unmount
                // instead of continuing to send requests with a stale session.
                useAuthStore.getState().clearAuth();
                if (originalRequest._silentAuth) {
                    return Promise.reject(err);
                }
                window.location.href = '/';
                return Promise.reject(err);
            } finally {
                isRefreshing = false;
            }
        }

        // A successful refresh followed by another 401 means the new cookie is
        // unusable for this session (for example, a revoked/mismatched session).
        // Stop authenticated polling instead of retrying forever while the UI
        // still believes the user is signed in.
        if (error.response?.status === 401 && originalRequest?._retry && !isAuthRequest) {
            useAuthStore.getState().clearAuth();
            if (!originalRequest._silentAuth) {
                window.location.href = '/';
            }
        }

        if (error.response?.status === 500) {
            logger.error('[API] Server Error:', error.response?.data?.detail || 'Internal Server Error');
        }

        return Promise.reject(error);
    }
);
