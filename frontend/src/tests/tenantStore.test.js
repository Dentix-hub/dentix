import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('tenant store commercial controls (PR-10)', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('clears tenant identity, entitlements, feature flags, loading, and errors', async () => {
        const { useTenantStore } = await import('@/store/tenant.store');
        useTenantStore.setState({
            tenant: { id: 11, name: 'Sensitive Clinic', plan: 'enterprise' },
            entitlements: { effective_subscription_status: 'ACTIVE', capacities: { ai: { remaining_quota: 10 } } },
            loading: true,
            error: new Error('sensitive tenant error'),
            features: { BILLING: true, AI_ASSISTANT: true },
        });

        useTenantStore.getState().clearTenant();

        expect(useTenantStore.getState()).toMatchObject({
            tenant: null,
            entitlements: null,
            loading: false,
            error: null,
            features: {},
        });
    });

    it('unknown plan name never enables commercial features (fail-closed contract)', async () => {
        const { useTenantStore } = await import('@/store/tenant.store');
        useTenantStore.getState().clearTenant();

        // Simulate setTenant with an unknown plan name
        useTenantStore.getState().setTenant({ id: 42, plan: 'unrecognized_gold_super_tier' });

        const state = useTenantStore.getState();
        // Baseline clinical navigation may exist, but all commercial capabilities MUST be false
        expect(state.hasFeature('BILLING')).toBe(false);
        expect(state.hasFeature('INVENTORY')).toBe(false);
        expect(state.hasFeature('LABORATORIES')).toBe(false);
        expect(state.hasFeature('AI_ASSISTANT')).toBe(false);
        expect(state.hasFeature('EXPORT_REPORTS')).toBe(false);
        expect(state.hasFeature('TENANT_BACKUPS')).toBe(false);
    });

    it('null/missing plan name defaults to fail-closed baseline, not full access', async () => {
        const { useTenantStore } = await import('@/store/tenant.store');
        useTenantStore.getState().clearTenant();

        useTenantStore.getState().setTenant({ id: 50, plan: null });

        const state = useTenantStore.getState();
        expect(state.hasFeature('BILLING')).toBe(false);
        expect(state.hasFeature('INVENTORY')).toBe(false);
        expect(state.hasFeature('LABORATORIES')).toBe(false);
        expect(state.hasFeature('AI_ASSISTANT')).toBe(false);
    });

    it('canonical entitlements snapshot correctly enables granted capabilities and quotas', async () => {
        const { useTenantStore } = await import('@/store/tenant.store');
        useTenantStore.getState().clearTenant();

        const mockSnapshot = {
            tenant_id: 101,
            tenant_name: 'Cairo Dental Center',
            effective_subscription_status: 'ACTIVE',
            can_read_clinical: true,
            can_write_clinical: true,
            can_write_billable: true,
            can_create_appointments: true,
            capacities: {
                seats: { limit: 5, used: 2, remaining: 3, is_exhausted: false },
                ai: { is_enabled: true, daily_limit: 10, remaining_quota: 8, window_reset: 'clinic_local_midnight', timezone: 'Africa/Cairo' },
            },
            capabilities: {
                BILLING: { effective_allowed: true, reason_code: 'ACTIVE_PLAN_GRANT' },
                INVENTORY: { effective_allowed: true, reason_code: 'ACTIVE_PLAN_GRANT' },
                LABORATORIES: { effective_allowed: false, reason_code: 'FEATURE_DISABLED_IN_PLAN' },
                AI_ASSISTANT: { effective_allowed: true, reason_code: 'ACTIVE_PLAN_GRANT' },
                EXPORT_REPORTS: { effective_allowed: false, reason_code: 'COMMERCIAL_UPGRADE_REQUIRED' },
            },
        };

        useTenantStore.getState().setEntitlements(mockSnapshot);

        const state = useTenantStore.getState();
        expect(state.hasFeature('BILLING')).toBe(true);
        expect(state.hasFeature('INVENTORY')).toBe(true);
        expect(state.hasFeature('LABORATORIES')).toBe(false);
        expect(state.hasFeature('AI_ASSISTANT')).toBe(true);
        expect(state.hasFeature('EXPORT_REPORTS')).toBe(false);

        expect(state.getAIQuota()).toMatchObject({
            daily_limit: 10,
            remaining_quota: 8,
            is_enabled: true,
        });
        expect(state.getSeatsQuota()).toMatchObject({
            limit: 5,
            used: 2,
            remaining: 3,
        });
        expect(state.getEffectiveStatus()).toBe('ACTIVE');
    });

    it('expired or read-only subscription disables write capabilities while preserving clinical read', async () => {
        const { useTenantStore } = await import('@/store/tenant.store');
        useTenantStore.getState().clearTenant();

        const mockExpiredSnapshot = {
            tenant_id: 102,
            effective_subscription_status: 'EXPIRED',
            is_past_end: true,
            is_in_grace: false,
            can_read_clinical: true,
            can_write_clinical: false,
            can_write_billable: false,
            can_create_appointments: false,
            capacities: {
                seats: { limit: 2, used: 2, remaining: 0, is_exhausted: true },
                ai: { is_enabled: false, daily_limit: 0, remaining_quota: 0 },
            },
            capabilities: {
                BILLING: { effective_allowed: false, reason_code: 'SUBSCRIPTION_EXPIRED' },
                INVENTORY: { effective_allowed: false, reason_code: 'SUBSCRIPTION_EXPIRED' },
                LABORATORIES: { effective_allowed: false, reason_code: 'SUBSCRIPTION_EXPIRED' },
                AI_ASSISTANT: { effective_allowed: false, reason_code: 'SUBSCRIPTION_EXPIRED' },
            },
        };

        useTenantStore.getState().setEntitlements(mockExpiredSnapshot);

        const state = useTenantStore.getState();
        // Clinical reading remains true under Clinical History Invariant
        expect(state.hasFeature('PATIENTS')).toBe(true);
        // All mutations/commercial capabilities are false
        expect(state.hasFeature('BILLING')).toBe(false);
        expect(state.hasFeature('INVENTORY')).toBe(false);
        expect(state.hasFeature('LABORATORIES')).toBe(false);
        expect(state.hasFeature('AI_ASSISTANT')).toBe(false);
        expect(state.getEffectiveStatus()).toBe('EXPIRED');
    });
});
