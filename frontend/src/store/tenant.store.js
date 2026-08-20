import { create } from 'zustand';
import logger from '@/utils/logger';
import { api } from '@/api';

export const useTenantStore = create((set, get) => ({
    tenant: null,
    loading: false,
    error: null,
    features: {},

    // Actions
    setTenant: (data) => {
        const features = deriveFeatures(data?.plan);
        set({ tenant: data, features });
    },

    clearTenant: () => set({
        tenant: null,
        loading: false,
        error: null,
        features: {},
    }),

    fetchTenant: async () => {
        set({ loading: true });
        try {
            // Fetching from /users/me is safer as it guarantees context
            const res = await api.get('/api/v1/users/me');
            const tenantData = res.data.tenant;

            // PRIORITY: Check for DB-configured features first
            let features = {};
            if (tenantData?.subscription_plan?.features) {
                try {
                    // It assumes features is a JSON string or array, we need to handle format
                    // Backend returns string usually, check Plan definition. 
                    // schemas/tenant.py says features: Optional[str]
                    const rawFeatures = tenantData.subscription_plan.features;
                    let parsed = rawFeatures;
                    
                    if (typeof rawFeatures === 'string' && (rawFeatures.startsWith('[') || rawFeatures.startsWith('{'))) {
                        try {
                            parsed = JSON.parse(rawFeatures);
                        } catch (e) {
                            logger.warn("Invalid JSON in features string, using as-is:", e);
                        }
                    }

                    if (Array.isArray(parsed)) {
                        // Convert array ["BILLING", "LABS"] to object { BILLING: true, LABS: true }
                        features = parsed.reduce((acc, feat) => ({ ...acc, [feat]: true }), {});
                        // Ensure base features are present
                        features = { ...features, 'PATIENTS': true, 'APPOINTMENTS': true, 'DASHBOARD': true };
                    } else if (typeof parsed === 'object' && parsed !== null) {
                        features = parsed;
                    } else {
                        // If it's a plain string or something else, use legacy derivation
                        features = deriveFeatures(tenantData?.plan);
                    }
                } catch (err) {
                    logger.error("Critical error parsing features:", err);
                    features = deriveFeatures(tenantData?.plan);
                }
            } else {
                features = deriveFeatures(tenantData?.plan);
            }

            set({ tenant: tenantData, features, loading: false });
        } catch (err) {
            logger.error("Failed to fetch tenant settings", err);
            set({ error: err, loading: false });
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
    }
}));

// Helper to derive features from plan
// In a real app, this should come from the backend's Plan definition
const deriveFeatures = (planName) => {
    // Defines features available to all plans
    const baseFeatures = {
        'PATIENTS': true,
        'APPOINTMENTS': true,
        'DASHBOARD': true,
        'BILLING': true,          // Always Enabled
        'LAB_INTEGRATION': true,  // Always Enabled
    };

    // Default "Full Access" set (used for Premium, Enterprise, Trial, and Unknown plans)
    const fullAccess = {
        ...baseFeatures,
        'AI_ASSISTANT': true,
        'REPORTS_ADVANCED': true,
        'MULTI_USER': true,
    };

    if (!planName) {
        logger.warn("[TenantStore] No plan name found, defaulting to Full Access (Trial Mode)");
        return fullAccess;
    }

    const normalizedPlan = planName.toLowerCase();

    // Restricted Plans
    if (normalizedPlan === 'basic' || normalizedPlan === 'starter') {
        return {
            ...baseFeatures,
            'BILLING': true, // Basic billing allowed
            'REPORTS_BASIC': true,
            'LAB_INTEGRATION': false, // Explicitly false for basic
            'AI_ASSISTANT': false,    // Explicitly false for basic
        };
    }

    // Known Premium Plans
    if (normalizedPlan === 'premium' || normalizedPlan === 'enterprise' || normalizedPlan === 'gold' || normalizedPlan === 'platinum') {
        return fullAccess;
    }

    // Default Fallback (Unknown Plan Name -> Full Access)
    return fullAccess;
};
