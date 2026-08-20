import { afterEach, describe, expect, it } from 'vitest';
import { hasSessionCookieHint } from './authSession';

describe('hasSessionCookieHint', () => {
    afterEach(() => {
        document.cookie = 'csrf_token=; Max-Age=0; path=/';
    });

    it('avoids an unauthenticated session probe when no auth cookies were issued', () => {
        expect(hasSessionCookieHint()).toBe(false);
    });

    it('detects the non-sensitive CSRF companion cookie for an active session', () => {
        document.cookie = 'csrf_token=session-hint; path=/';
        expect(hasSessionCookieHint()).toBe(true);
    });
});
