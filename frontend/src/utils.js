import logger from '@/utils/logger';
export function parseJwt(token) {
    try {
        if (!token) return null;
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

// SECURITY: Main auth tokens are stored in httpOnly cookies (set by backend).
// JavaScript cannot read httpOnly cookies - they are sent automatically with requests.
// This prevents XSS token theft completely.
// sessionStorage is ONLY used for admin_token during super-admin impersonation (temporary, admin-only feature).

// MAIN AUTH TOKENS (httpOnly cookies - not readable from JS)
export function getToken() {
    // Cannot read httpOnly cookie from JS. Return null.
    // The cookie is sent automatically with each request.
    return null;
}

export function getRefreshToken() {
    // Cannot read httpOnly cookie from JS. Return null.
    return null;
}

export function setToken(token, __refreshToken = null) {
    // Main auth tokens are set via httpOnly cookies by the backend on login/refresh.
    // The login response returns tokens in the body for immediate use (e.g., parseJwt),
    // but persistent storage is cookie-based.
    // No-op for sessionStorage - kept for API compatibility with existing calls.
}

export function removeToken() {
    // Main auth tokens are cleared by calling the backend /logout endpoint,
    // which deletes the httpOnly cookies.
    // No-op for sessionStorage.
}

// ADMIN IMPERSONATION TOKEN (sessionStorage - temporary, admin-only)
// Used to store original admin token when impersonating a tenant user
export function getAdminToken() {
    return sessionStorage.getItem('admin_token');
}

export function setAdminToken(token) {
    if (token) {
        sessionStorage.setItem('admin_token', token);
    } else {
        sessionStorage.removeItem('admin_token');
    }
}

export function removeAdminToken() {
    sessionStorage.removeItem('admin_token');
}

// Call this on logout to clear httpOnly cookies via backend
export async function logout() {
    try {
        // Import api dynamically to avoid circular dependency
        const { api } = await import('./api/apiClient');
        await api.post('/api/v1/auth/logout');
    } catch (e) {
        // Even if the request fails, clear any potential local state
        logger.warn('Logout request failed:', e);
    }
    // Force reload to clear any cached state
    window.location.href = '/';
}