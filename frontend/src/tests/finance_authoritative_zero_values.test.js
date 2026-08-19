import { describe, expect, it } from 'vitest';

import { authoritativeNumber } from '../features/finance/utils/financialTruth';

describe('Finance authoritative numeric values', () => {
    it('preserves an explicit backend zero instead of using a frontend fallback', () => {
        expect(authoritativeNumber(0, 500)).toBe(0);
        expect(authoritativeNumber('0', -250)).toBe(0);
    });

    it('uses the fallback only when the backend value is actually absent or invalid', () => {
        expect(authoritativeNumber(null, 125)).toBe(125);
        expect(authoritativeNumber(undefined, -75)).toBe(-75);
        expect(authoritativeNumber('not-a-number', 40)).toBe(40);
    });
});
