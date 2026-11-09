import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { getTenantEntitlements } from '@/api/settings';
import { useTenantStore } from '@/store/tenant.store';
import { queryKeys } from '@/lib/queryClient';

/**
 * Hook for tenant commercial entitlements snapshot.
 * Authoritative source of commercial status, quotas, and capabilities.
 */
export function useTenantEntitlements({ enabled = true } = {}) {
    const query = useQuery({
        queryKey: queryKeys.tenantEntitlements,
        queryFn: async () => {
            const res = await getTenantEntitlements();
            return res.data?.data || res.data;
        },
        enabled,
        staleTime: 30 * 1000,
        retry: 1,
    });

    useEffect(() => {
        if (query.data) {
            useTenantStore.getState().setEntitlements(query.data);
        }
    }, [query.data]);

    const entitlements = query.data || null;

    return {
        ...query,
        entitlements,
        effectiveStatus: entitlements?.effective_subscription_status || 'UNKNOWN',
        isPastEnd: !!entitlements?.is_past_end,
        isInGrace: !!entitlements?.is_in_grace,
        canReadClinical: entitlements?.can_read_clinical ?? false,
        canWriteClinical: entitlements?.can_write_clinical ?? false,
        canWriteBillable: entitlements?.can_write_billable ?? false,
        canCreateAppointments: entitlements?.can_create_appointments ?? false,
        aiQuota: entitlements?.capacities?.ai || null,
        seatsQuota: entitlements?.capacities?.seats || null,
        hasCapability: (key) => !!entitlements?.capabilities?.[key]?.effective_allowed,
        getReasonCode: (key) => entitlements?.capabilities?.[key]?.reason_code || 'UNAVAILABLE',
    };
}
