import { beforeEach, describe, expect, it } from 'vitest';

import { clearSessionCookieHint, hasSessionCookieHint } from './authSession';

function clearReadableCookies() {
    for (const cookie of document.cookie.split(';')) {
        const name = cookie.split('=')[0]?.trim();
        if (name) {
            document.cookie = `${name}=; Max-Age=0; path=/`;
        }
    }
}

describe('PWA auth session hint', () => {
    beforeEach(() => {
        clearReadableCookies();
    });

    it('recognizes the dedicated refresh-lifetime hint', () => {
        document.cookie = 'dentix_session_hint=1; path=/; SameSite=Lax';
        expect(hasSessionCookieHint()).toBe(true);
    });

    it('accepts the legacy CSRF cookie during the rollout transition', () => {
        document.cookie = 'csrf_token=legacy; path=/; SameSite=Lax';
        expect(hasSessionCookieHint()).toBe(true);
    });

    it('returns false for a genuinely anonymous browser', () => {
        expect(hasSessionCookieHint()).toBe(false);
    });

    it('clears both the dedicated hint and stale legacy CSRF hint', () => {
        document.cookie = 'dentix_session_hint=1; path=/; SameSite=Lax';
        document.cookie = 'csrf_token=legacy; path=/; SameSite=Lax';

        clearSessionCookieHint();

        expect(hasSessionCookieHint()).toBe(false);
        expect(document.cookie).not.toContain('dentix_session_hint=');
        expect(document.cookie).not.toContain('csrf_token=');
    });
});
