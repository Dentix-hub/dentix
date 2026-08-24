const SESSION_HINT_COOKIE = 'dentix_session_hint=';
const LEGACY_CSRF_COOKIE = 'csrf_token=';

export const hasSessionCookieHint = () => {
    if (typeof document === 'undefined') return false;
    const cookies = document.cookie.split(';').map(cookie => cookie.trim());
    return cookies.some(cookie => cookie.startsWith(SESSION_HINT_COOKIE))
        || cookies.some(cookie => cookie.startsWith(LEGACY_CSRF_COOKIE));
};

export const clearSessionCookieHint = () => {
    if (typeof document === 'undefined') return;
    // Both cookies are non-sensitive/readable hints. Clearing the legacy CSRF
    // cookie after a confirmed 401 prevents an expired 30-day hint from forcing
    // a pointless auth/refresh round-trip on every future cold start.
    document.cookie = 'dentix_session_hint=; Max-Age=0; path=/; SameSite=Lax';
    document.cookie = 'csrf_token=; Max-Age=0; path=/; SameSite=Lax';
};
