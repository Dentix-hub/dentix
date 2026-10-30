import { describe, expect, it } from 'vitest';
import { resolveApiBaseUrl, shouldUseSameOriginApi } from './apiOrigin';

const locationFor = (url) => new URL(url);

describe('resolveApiBaseUrl', () => {
    it('uses same-origin API for hosted clinic image cookies', () => {
        expect(shouldUseSameOriginApi('dentix-staging.vercel.app')).toBe(true);
        expect(shouldUseSameOriginApi('www.dentixs.app')).toBe(true);
        expect(shouldUseSameOriginApi('other.example.com')).toBe(false);
    });

    it('keeps production API calls same-origin across apex/www aliases', () => {
        expect(resolveApiBaseUrl('https://www.dentixs.app', locationFor('https://dentixs.app/admin'))).toBe('');
        expect(resolveApiBaseUrl('https://dentixs.app', locationFor('https://www.dentixs.app/admin'))).toBe('');
    });

    it('preserves a genuinely separate API host', () => {
        expect(resolveApiBaseUrl('https://api.dentixs.app', locationFor('https://dentixs.app/admin')))
            .toBe('https://api.dentixs.app');
    });

    it('uses the local backend during development', () => {
        expect(resolveApiBaseUrl(undefined, locationFor('http://localhost:5173/admin')))
            .toBe('http://localhost:8000');
    });
});
