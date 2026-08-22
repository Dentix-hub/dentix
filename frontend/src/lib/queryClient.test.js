import { describe, expect, it } from 'vitest';

import { queryClient } from './queryClient';


describe('queryClient mutation safety', () => {
    it('does not retry state-changing requests by default', () => {
        expect(queryClient.getDefaultOptions().mutations.retry).toBe(false);
    });
});
