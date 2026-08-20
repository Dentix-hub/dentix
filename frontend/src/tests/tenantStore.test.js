import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('tenant store', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('clears tenant identity, feature flags, loading, and errors', async () => {
        const { useTenantStore } = await import('@/store/tenant.store');
        useTenantStore.setState({
            tenant: { id: 11, name: 'Sensitive Clinic' },
            loading: true,
            error: new Error('sensitive tenant error'),
            features: { BILLING: true },
        });

        useTenantStore.getState().clearTenant();

        expect(useTenantStore.getState()).toMatchObject({
            tenant: null,
            loading: false,
            error: null,
            features: {},
        });
    });
});
