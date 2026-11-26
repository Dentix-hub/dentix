import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

const apiPostMock = vi.hoisted(() => vi.fn());
const clearSessionCookieHintMock = vi.hoisted(() => vi.fn());

vi.mock('../api/apiClient', () => ({
    api: { post: apiPostMock },
}));

vi.mock('../api/authSession', () => ({
    clearSessionCookieHint: clearSessionCookieHintMock,
}));

import { parseJwt, getToken, getRefreshToken, setToken, removeToken, getAdminToken, setAdminToken, removeAdminToken, logout } from '../utils';

describe('utils', () => {
    const originalLocation = window.location;

    beforeEach(() => {
        localStorage.clear();
        sessionStorage.clear();
        vi.clearAllMocks();
    });

    afterEach(() => {
        Object.defineProperty(window, 'location', {
            value: originalLocation,
            writable: true,
            configurable: true,
        });
    });

    describe('parseJwt', () => {
        it('returns null for empty/null token', () => {
            expect(parseJwt(null)).toBeNull();
            expect(parseJwt('')).toBeNull();
            expect(parseJwt(undefined)).toBeNull();
        });
        it('parses a valid JWT payload', () => {
            const payload = { sub: 'doctor1', tenant_id: 1, role: 'admin' };
            const base64 = btoa(JSON.stringify(payload));
            const fakeToken = `header.${base64}.signature`;
            const result = parseJwt(fakeToken);
            expect(result).toEqual(payload);
        });
        it('returns null for malformed token', () => {
            expect(parseJwt('not-a-jwt')).toBeNull();
            expect(parseJwt('only.two')).toBeNull();
        });
    });

    describe('Main auth tokens (httpOnly cookies - not stored in sessionStorage)', () => {
        it('getToken returns null (cannot read httpOnly cookie)', () => {
            expect(getToken()).toBeNull();
        });
        it('getRefreshToken returns null (cannot read httpOnly cookie)', () => {
            expect(getRefreshToken()).toBeNull();
        });
        it('setToken is no-op for main auth tokens', () => {
            setToken('access123', 'refresh456');
            // Should not store in sessionStorage
            expect(sessionStorage.getItem('token')).toBeNull();
            expect(sessionStorage.getItem('refresh_token')).toBeNull();
        });
        it('removeToken is no-op for main auth tokens', () => {
            removeToken();
            // Should not throw
        });
    });

    describe('Admin impersonation token (sessionStorage - temporary)', () => {
        it('stores admin token in sessionStorage', () => {
            setAdminToken('admin-token-123');
            expect(sessionStorage.getItem('admin_token')).toBe('admin-token-123');
        });
        it('getAdminToken retrieves from sessionStorage', () => {
            sessionStorage.setItem('admin_token', 'ss-admin-token');
            expect(getAdminToken()).toBe('ss-admin-token');
        });
        it('removeAdminToken clears from sessionStorage', () => {
            sessionStorage.setItem('admin_token', 'to-remove');
            removeAdminToken();
            expect(sessionStorage.getItem('admin_token')).toBeNull();
        });
        it('setAdminToken with null removes the token', () => {
            sessionStorage.setItem('admin_token', 'to-remove');
            setAdminToken(null);
            expect(sessionStorage.getItem('admin_token')).toBeNull();
        });
    });

    describe('logout()', () => {
        it('clears session cookie hints BEFORE redirecting to /login when API logout succeeds', async () => {
            const callOrder = [];
            let currentHref = '';
            apiPostMock.mockResolvedValueOnce({ status: 200 });
            clearSessionCookieHintMock.mockImplementation(() => callOrder.push('clear_hint'));

            Object.defineProperty(window, 'location', {
                value: {
                    get href() { return currentHref; },
                    set href(val) {
                        currentHref = val;
                        callOrder.push(`set_href:${val}`);
                    },
                },
                writable: true,
                configurable: true,
            });

            await logout();

            expect(apiPostMock).toHaveBeenCalledWith('/api/v1/auth/logout');
            expect(callOrder).toEqual(['clear_hint', 'set_href:/login']);
        });

        it('still clears session cookie hints BEFORE redirecting to /login when API logout fails (401/offline)', async () => {
            const callOrder = [];
            let currentHref = '';
            apiPostMock.mockRejectedValueOnce({ response: { status: 401 } });
            clearSessionCookieHintMock.mockImplementation(() => callOrder.push('clear_hint'));

            Object.defineProperty(window, 'location', {
                value: {
                    get href() { return currentHref; },
                    set href(val) {
                        currentHref = val;
                        callOrder.push(`set_href:${val}`);
                    },
                },
                writable: true,
                configurable: true,
            });

            await logout();

            expect(callOrder).toEqual(['clear_hint', 'set_href:/login']);
        });
    });
});