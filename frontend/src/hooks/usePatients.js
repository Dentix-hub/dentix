import { useEffect } from 'react';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    createPatient,
    deletePatient,
    getPatient,
    getPatientDirectory,
    getPatients,
    getRecentPatientDirectory,
    updatePatient,
} from '@/api';
import { rememberRecentPatientId } from '@/features/patients/recentPatients';
import { queryKeys } from '@/lib/queryClient';

export function usePatients(options = {}) {
    return useQuery({
        queryKey: queryKeys.patients,
        queryFn: async () => {
            const res = await getPatients();
            return res.data;
        },
        staleTime: 60 * 1000,
        ...options,
    });
}

export function usePatientDirectory({ query = '', limit = 30, scope = 'all', enabled = true } = {}) {
    return useInfiniteQuery({
        queryKey: queryKeys.patientDirectory({ query, limit, scope }),
        initialPageParam: null,
        queryFn: async ({ pageParam }) => {
            const res = await getPatientDirectory({
                q: query,
                cursor: pageParam,
                limit,
                scope,
            });
            const items = res.data || [];
            return {
                items,
                pagination: items._pagination || {
                    next_cursor: null,
                    has_more: false,
                    limit,
                },
            };
        },
        getNextPageParam: (lastPage) =>
            lastPage.pagination?.has_more
                ? lastPage.pagination.next_cursor
                : undefined,
        enabled,
        staleTime: 30 * 1000,
    });
}

export function useRecentPatients(ids, query = '', options = {}) {
    const stableIds = Array.isArray(ids) ? ids : [];
    return useQuery({
        queryKey: queryKeys.patientRecent({ ids: stableIds.join(','), query }),
        queryFn: async () => {
            const res = await getRecentPatientDirectory({ ids: stableIds, q: query });
            return res.data || [];
        },
        enabled: stableIds.length > 0,
        staleTime: 10 * 1000,
        ...options,
    });
}

export function usePatient(patientId) {
    const query = useQuery({
        queryKey: queryKeys.patient(patientId),
        queryFn: async () => {
            const res = await getPatient(patientId);
            return res.data;
        },
        enabled: !!patientId,
    });

    useEffect(() => {
        if (query.data?.id) rememberRecentPatientId(query.data.id);
    }, [query.data?.id]);

    return query;
}

export function useSearchPatients(query, options = {}) {
    const normalizedQuery = query?.trim() || '';
    return useQuery({
        queryKey: queryKeys.patientSearch(normalizedQuery),
        queryFn: async () => {
            const res = await getPatientDirectory({ q: normalizedQuery, limit: 20, scope: 'all' });
            return res.data || [];
        },
        enabled: normalizedQuery.length >= 2,
        staleTime: 15 * 1000,
        ...options,
    });
}

export function useCreatePatient() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: createPatient,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.patients });
        },
    });
}

export function useUpdatePatient() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }) => updatePatient(id, data),
        onSuccess: (_, { id }) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.patients });
            queryClient.invalidateQueries({ queryKey: queryKeys.patient(id) });
        },
    });
}

export function useDeletePatient() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: deletePatient,
        onMutate: async () => {
            await queryClient.cancelQueries({ queryKey: queryKeys.dashboardStats });
            const prev = queryClient.getQueryData(queryKeys.dashboardStats);
            queryClient.setQueryData(queryKeys.dashboardStats, (old) => {
                if (!old) return old;
                return { ...old, total_patients: Math.max(0, (old.total_patients ?? 0) - 1) };
            });
            return { prev };
        },
        onError: (_err, _vars, ctx) => {
            if (ctx?.prev) queryClient.setQueryData(queryKeys.dashboardStats, ctx.prev);
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.patients });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
            queryClient.invalidateQueries({ queryKey: queryKeys.todayPayments });
            queryClient.invalidateQueries({ queryKey: queryKeys.todayDebtors });
        },
    });
}

export function usePrefetchPatients() {
    const queryClient = useQueryClient();
    return () => {
        queryClient.prefetchQuery({
            queryKey: queryKeys.patients,
            queryFn: async () => {
                const res = await getPatients();
                return res.data;
            },
            staleTime: 60 * 1000,
        });
    };
}
