import axios from 'axios';
import { getToken, getRefreshToken, setToken, removeToken } from '../utils';

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
    console.log(`%c[API_DIAGNOSTIC] Active API URL: ${API_URL || 'Same Origin (' + window.location.origin + ')'}`, 'color: #00ff00; font-weight: bold;');
}

export const api = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    withCredentials: true,
});

api.interceptors.request.use(config => {
    if (config._retry && config.headers.Authorization) {
        return config;
    }

    const token = getToken();
    if (token) {
        if (config.headers && typeof config.headers.set === 'function') {
            config.headers.set('Authorization', `Bearer ${token}`);
        } else {
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
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
            console.error('[API] Request failed:', error.response.status, originalRequest.url);
        }

        if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/api/v1/auth/token') && !originalRequest.url?.includes('/api/v1/auth/refresh')) {
            const debugMsg = error.response?.data?.detail || "Unknown Auth Error";

            if (isRefreshing) {
                return new Promise(function (resolve, reject) {
                    failedQueue.push({ resolve, reject });
                }).then(token => {
                    originalRequest.headers['Authorization'] = 'Bearer ' + token;
                    return api(originalRequest);
                }).catch(err => {
                    return Promise.reject(err);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const refreshToken = getRefreshToken();

            if (!refreshToken) {
                removeToken();
                window.location.href = '/';
                return Promise.reject(error);
            }

            try {
                const formData = new FormData();
                formData.append('refresh_token', refreshToken);

                const response = await axios.post(`${API_URL}/api/v1/auth/refresh`, formData, { withCredentials: true });

                const { access_token, refresh_token: newRefreshToken } = response.data;
                setToken(access_token, newRefreshToken);
                api.defaults.headers.common['Authorization'] = 'Bearer ' + access_token;
                originalRequest.headers['Authorization'] = 'Bearer ' + access_token;

                processQueue(null, access_token);
                return api(originalRequest);
            } catch (err) {
                processQueue(err, null);
                removeToken();

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
            console.error('[API] Server Error:', error.response?.data?.detail || 'Internal Server Error');
        }

        return Promise.reject(error);
    }
);
