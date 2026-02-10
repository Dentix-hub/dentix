import { describe, it, expect, beforeEach } from 'vitest';
import { parseJwt, getToken, getRefreshToken, setToken, removeToken } from '../utils';
describe('utils', () => {
    beforeEach(() => {
        localStorage.clear();
        sessionStorage.clear();
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
    describe('setToken / getToken / getRefreshToken', () => {
        it('stores token in localStorage when remember=true', () => {
            setToken('access123', 'refresh456', true);
            expect(localStorage.getItem('token')).toBe('access123');
            expect(localStorage.getItem('refresh_token')).toBe('refresh456');
        });
        it('stores token in sessionStorage when remember=false', () => {
            setToken('access789', 'refresh012', false);
            expect(sessionStorage.getItem('token')).toBe('access789');
            expect(sessionStorage.getItem('refresh_token')).toBe('refresh012');
        });
        it('getToken retrieves from localStorage first', () => {
            localStorage.setItem('token', 'ls-token');
            sessionStorage.setItem('token', 'ss-token');
            expect(getToken()).toBe('ls-token');
        });
        it('getToken falls back to sessionStorage', () => {
            sessionStorage.setItem('token', 'ss-token');
            expect(getToken()).toBe('ss-token');
        });
        it('getRefreshToken retrieves from localStorage first', () => {
            localStorage.setItem('refresh_token', 'ls-refresh');
            sessionStorage.setItem('refresh_token', 'ss-refresh');
            expect(getRefreshToken()).toBe('ls-refresh');
        });
        it('getRefreshToken falls back to sessionStorage', () => {
            sessionStorage.setItem('refresh_token', 'ss-refresh');
            expect(getRefreshToken()).toBe('ss-refresh');
        });
        it('setToken without refreshToken skips refresh storage', () => {
            setToken('access-only');
            expect(localStorage.getItem('token')).toBe('access-only');
            expect(localStorage.getItem('refresh_token')).toBeNull();
        });
    });
    describe('removeToken', () => {
        it('clears tokens from both storages', () => {
            localStorage.setItem('token', 'a');
            localStorage.setItem('refresh_token', 'b');
            sessionStorage.setItem('token', 'c');
            sessionStorage.setItem('refresh_token', 'd');
            removeToken();
            expect(localStorage.getItem('token')).toBeNull();
            expect(localStorage.getItem('refresh_token')).toBeNull();
            expect(sessionStorage.getItem('token')).toBeNull();
            expect(sessionStorage.getItem('refresh_token')).toBeNull();
        });
        it('does not throw when no tokens exist', () => {
            expect(() => removeToken()).not.toThrow();
        });
    });
});
