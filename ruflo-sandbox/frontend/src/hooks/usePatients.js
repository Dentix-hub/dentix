import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getPatients,
    getPatient,
    createPatient,
    updatePatient,
    deletePatient,
    searchPatients
} from '@/api';
import { queryKeys } from '@/lib/queryClient';

/**
 * Hook for fetching all patients with caching
 */
export function usePatients() {
    return useQuery({
        queryKey: queryKeys.patients,
        queryFn: async () => {
            const res = await getPatients();
            return res.data;
        },
        staleTime: 60 * 1000, // Patients list stays fresh for 1 minute
    });
}

/**
 * Hook for fetching a single patient
 */
export function usePatient(patientId) {
    return useQuery({
        queryKey: queryKeys.patient(patientId),
        queryFn: async () => {
            const res = await getPatient(patientId);
            return res.data;
        },
        enabled: !!patientId,
    });
}

/**
 * Hook for searching patients
 */
export function useSearchPatients(query) {
    return useQuery({
        queryKey: ['patients', 'search', query],
        queryFn: async () => {
            const res = await searchPatients(query);
            return res.data;
        },
        enabled: query?.length >= 2,
        staleTime: 10 * 1000,
    });
}

/**
 * Hook for creating a patient
 */
export function useCreatePatient() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: createPatient,
        onSuccess: () => {
            // Invalidate patients list to refetch
            queryClient.invalidateQueries({ queryKey: queryKeys.patients });
        },
    });
}

/**
 * Hook for updating a patient
 */
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

/**
 * Hook for deleting a patient
 */
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

/**
 * Prefetch patients for instant navigation
 */
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
