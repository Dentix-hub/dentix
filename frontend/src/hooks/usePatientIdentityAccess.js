import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';
import { queryKeys } from '@/lib/queryClient';

/**
 * Terminal identity failures must not be hidden by React Query retries, because
 * retrying can keep stale patient data on screen while access is being denied.
 */
export function isTerminalPatientIdentityError(error) {
    const status = Number(error?.response?.status ?? error?.status);
    return status >= 400 && status < 500 && status !== 408 && status !== 429;
}

/**
 * A denial marker lives in the query cache so a later transient error, error
 * retry or remount cannot resurrect previously loaded clinical content.
 */
export function usePatientIdentityDenial(patientId, tenantKey) {
    const queryClient = useQueryClient();
    const queryKey = useMemo(() => queryKeys.patientIdentityDenial(patientId, tenantKey), [patientId, tenantKey]);
    const query = useQuery({
        queryKey,
        queryFn: () => ({ denied: false }),
        initialData: { denied: false },
        staleTime: Infinity,
        enabled: false,
    });

    const setDenied = useCallback((denied, status = null) => {
        queryClient.setQueryData(queryKey, { denied: Boolean(denied), status });
    }, [queryClient, queryKey]);

    return {
        isDenied: Boolean(query.data?.denied),
        denialStatus: query.data?.status,
        setDenied,
    };
}

/**
 * Remove patient-scoped cached data after a definitive identity denial. The
 * denial marker itself is kept outside this patient key namespace.
 */
export function purgePatientIdentityScopeCache(queryClient, patientId) {
    if (!queryClient || !patientId) return;

    const patientKey = String(patientId);
    const matchesPatient = (query) => Array.isArray(query.queryKey)
        && query.queryKey[0] === 'patient'
        && String(query.queryKey[1]) === patientKey;

    for (const query of queryClient.getQueryCache().findAll({ predicate: matchesPatient })) {
        if (query.queryKey[2] === 'identity') {
            // Keep the observer's failure state without retaining patient data or refetching.
            if (query.state.data !== undefined) {
                query.setState({ data: undefined, dataUpdatedAt: 0 });
            }
        } else {
            queryClient.removeQueries({ queryKey: query.queryKey, exact: true });
        }
    }
    queryClient.removeQueries({ queryKey: ['patientPlanOverlay', patientKey] });
}
