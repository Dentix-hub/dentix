import { describe, it, expect } from 'vitest';
import { queryClient, queryKeys } from './queryClient';

describe('Admin Request Efficiency & Query Keys MS-34', () => {
    it('defines canonical admin query keys for targeted invalidation without collision', () => {
        expect(queryKeys.admin.stats).toEqual(['admin', 'stats']);
        expect(queryKeys.admin.health).toEqual(['admin', 'health', 'alerts']);
        expect(queryKeys.admin.security).toEqual(['admin', 'security']);
        expect(queryKeys.admin.sessions).toEqual(['admin', 'sessions']);
        expect(queryKeys.admin.tenants({ status: 'active' })).toEqual(['admin', 'tenants', { status: 'active' }]);
        expect(queryKeys.admin.tenant(12)).toEqual(['admin', 'tenant', 12]);
        expect(queryKeys.admin.users({ query: 'dr' })).toEqual(['admin', 'users', { query: 'dr' }]);
        expect(queryKeys.admin.finance('year')).toEqual(['admin', 'finance', 'year']);
        expect(queryKeys.admin.aiStats('today')).toEqual(['admin', 'ai', 'stats', 'today']);
        expect(queryKeys.admin.logs(2, 50)).toEqual(['admin', 'system', 'logs', 2, 50]);
    });

    it('configures query client with 30s stale time to prevent redundant duplicate background calls', () => {
        const defaultOptions = queryClient.getDefaultOptions();
        expect(defaultOptions.queries.staleTime).toBe(30000);
        expect(defaultOptions.queries.refetchOnWindowFocus).toBe(false);
        expect(defaultOptions.mutations.retry).toBe(false);
    });
});
