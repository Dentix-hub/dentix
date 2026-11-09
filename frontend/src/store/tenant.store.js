import { create } from 'zustand';
import logger from '@/utils/logger';
import { api } from '@/api';

export const useTenantStore = create((set, get) => ({
    tenant: null,
    entitlements: null,
    loading: false,
    error: null,
    features: {},

    // Actions
    setTenant: (data) => {
        const features = deriveFeatures(data?.plan);
        set({ tenant: data, features });
    },

    setEntitlements: (entitlementsData) => {
        if (!entitlementsData || typeof entitlementsData !== 'object') {
            set({ entitlements: null, features: {} });
            return;
        }

        const features = {};
        if (entitlementsData.capabilities) {
            for (const [key, cap] of Object.entries(entitlementsData.capabilities)) {
                features[key] = !!cap.effective_allowed;
            }
        }

        // Direct clinical/appointment/billing operational capabilities
        if (entitlementsData.can_read_clinical || entitlementsData.can_write_clinical) {
            features['PATIENTS'] = true;
        }
        if (entitlementsData.can_create_appointments || entitlementsData.can_read_clinical) {
            features['APPOINTMENTS'] = true;
        }
        if (entitlementsData.can_write_billable || entitlementsData.capabilities?.BILLING?.effective_allowed) {
            features['BILLING'] = true;
        }
        if (entitlementsData.capabilities?.LABORATORIES?.effective_allowed) {
            features['LABORATORIES'] = true;
            features['LAB_INTEGRATION'] = true;
        }
        if (entitlementsData.capabilities?.INVENTORY?.effective_allowed) {
            features['INVENTORY'] = true;
        }
        if (entitlementsData.capabilities?.AI_ASSISTANT?.effective_allowed) {
            features['AI_ASSISTANT'] = !!entitlementsData.capacities?.ai?.is_enabled;
        }
        if (entitlementsData.capabilities?.EXPORT_REPORTS?.effective_allowed) {
            features['EXPORT_REPORTS'] = true;
        }
        if (entitlementsData.capabilities?.TENANT_BACKUPS?.effective_allowed) {
            features['TENANT_BACKUPS'] = true;
        }

        set({ entitlements: entitlementsData, features });
    },

    clearTenant: () => set({
        tenant: null,
        entitlements: null,
        loading: false,
        error: null,
        features: {},
    }),

    fetchTenant: async () => {
        set({ loading: true, error: null });
        try {
            const res = await api.get('/api/v1/users/me');
            const tenantData = res.data?.tenant || res.data;

            // Strict, fail-closed feature set: unknown plan NEVER grants commercial features
            let features = deriveFeatures(tenantData?.plan);

            // Attempt to fetch canonical entitlements snapshot
            try {
                const entRes = await api.get('/api/v1/settings/entitlements');
                const entData = entRes.data?.data || entRes.data;
                if (entData && typeof entData === 'object') {
                    get().setEntitlements(entData);
                    set({ tenant: tenantData, loading: false });
                    return;
                }
            } catch (entErr) {
                logger.warn("[TenantStore] Entitlements endpoint unavailable or failed; maintaining strict fail-closed state:", entErr);
            }

            set({ tenant: tenantData, features, loading: false });
        } catch (err) {
            logger.error("Failed to fetch tenant settings", err);
            // Snapshot error is NOT an all-access state: fail-closed with empty features
            set({ error: err, features: {}, loading: false });
        }
    },

    updateTenant: async (data) => {
        set({ loading: true });
        try {
            const res = await api.put('/settings/tenant', data);
            set({ tenant: res.data, loading: false });
            return res.data;
        } catch (err) {
            set({ loading: false });
            throw err;
        }
    },

    // Selectors
    hasFeature: (featureKey) => {
        const { features } = get();
        return !!features[featureKey];
    },

    getAIQuota: () => {
        const { entitlements } = get();
        return entitlements?.capacities?.ai || null;
    },

    getSeatsQuota: () => {
        const { entitlements } = get();
        return entitlements?.capacities?.seats || null;
    },

    getEffectiveStatus: () => {
        const { entitlements, tenant } = get();
        return entitlements?.effective_subscription_status || (tenant?.plan ? 'UNKNOWN' : 'NONE');
    },
}));

// Helper to derive baseline features for offline/pre-snapshot states
// Strictly fail-closed: unknown plans or missing plans NEVER grant commercial access
const deriveFeatures = (planName) => {
    // Only non-commercial clinical viewing/entry is allowed offline without snapshot
    const baseline = {
        'PATIENTS': true,
        'APPOINTMENTS': true,
        'DASHBOARD': true,
        'BILLING': false,
        'INVENTORY': false,
        'LAB_INTEGRATION': false,
        'LABORATORIES': false,
        'AI_ASSISTANT': false,
        'REPORTS_ADVANCED': false,
        'EXPORT_REPORTS': false,
        'TENANT_BACKUPS': false,
    };

    if (!planName) {
        return baseline;
    }

    const normalizedPlan = planName.toLowerCase();
    // Only known verified plans can receive initial baseline hints prior to snapshot
    if (normalizedPlan === 'basic' || normalizedPlan === 'starter') {
        return {
            ...baseline,
            'BILLING': true,
        };
    }
    if (normalizedPlan === 'premium' || normalizedPlan === 'enterprise' || normalizedPlan === 'professional') {
        return {
            ...baseline,
            'BILLING': true,
            'INVENTORY': true,
            'LAB_INTEGRATION': true,
            'LABORATORIES': true,
            'AI_ASSISTANT': true,
            'REPORTS_ADVANCED': true,
            'EXPORT_REPORTS': true,
            'TENANT_BACKUPS': true,
        };
    }

    // Default Fallback: STRICTLY FAIL-CLOSED (Unknown Plan Name -> Baseline Only)
    return baseline;
};
