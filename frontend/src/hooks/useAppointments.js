import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getAppointments,
    createAppointment,
    updateAppointmentStatus,
    updateAppointment,
    deleteAppointment,
    getReceptionNextVisitRequests,
    scheduleNextVisitRequest,
    cancelNextVisitRequest
} from '@/api';
import { queryKeys } from '@/lib/queryClient';
import { useTenantFeatures } from '@/hooks/usePatientDetails';

/**
 * Hook for fetching appointments with caching
 */
export function useAppointments(options = {}) {
    return useQuery({
        queryKey: queryKeys.appointments,
        queryFn: async () => {
            const res = await getAppointments();
            return res.data;
        },
        staleTime: 30 * 1000, // 30 seconds
        ...options
    });
}

/**
 * Hook for creating an appointment
 */
export function useCreateAppointment() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: createAppointment,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.appointments });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
        },
    });
}

/**
 * Hook for updating appointment status
 */
export function useUpdateAppointmentStatus() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, status }) => updateAppointmentStatus(id, status),
        onMutate: async ({ id, status }) => {
            await queryClient.cancelQueries({ queryKey: queryKeys.appointments });
            const previousAppointments = queryClient.getQueryData(queryKeys.appointments);
            
            if (previousAppointments) {
                queryClient.setQueryData(queryKeys.appointments, old => 
                    old.map(app => app.id === id ? { ...app, status } : app)
                );
            }
            return { previousAppointments };
        },
        onError: (err, variables, context) => {
            if (context?.previousAppointments) {
                queryClient.setQueryData(queryKeys.appointments, context.previousAppointments);
            }
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.appointments });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
        },
    });
}

/**
 * Hook for general appointment update (rescheduling, notes, etc.)
 */
export function useUpdateAppointment() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, data }) => updateAppointment(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.appointments });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
        },
    });
}

/**
 * Hook for deleting an appointment
 */
export function useDeleteAppointment() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: deleteAppointment,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.appointments });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
        },
    });
}

/**
 * Prefetch appointments
 */
export function usePrefetchAppointments() {
    const queryClient = useQueryClient();

    return () => {
        queryClient.prefetchQuery({
            queryKey: queryKeys.appointments,
            queryFn: async () => {
                const res = await getAppointments();
                return res.data;
            },
            staleTime: 30 * 1000,
        });
    };
}

/**
 * Hook for fetching next-visit requests queue (G11-M04)
 */
export function useNextVisitRequests(filters = {}, options = {}) {
    const { data: tenantFeatures = [] } = useTenantFeatures();
    const isNativeWritesEnabled = Array.isArray(tenantFeatures) && tenantFeatures.includes('clinical_vnext_native_writes');

    return useQuery({
        queryKey: queryKeys.nextVisitRequests(filters),
        queryFn: async () => {
            const res = await getReceptionNextVisitRequests(filters);
            return res.data;
        },
        enabled: isNativeWritesEnabled && (options.enabled !== false),
        staleTime: 15 * 1000,
        ...options
    });
}

/**
 * Hook for converting next-visit request to appointment (G11-M05)
 */
export function useScheduleNextVisitRequest() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ requestId, data }) => scheduleNextVisitRequest(requestId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.appointments });
            queryClient.invalidateQueries({ queryKey: ['next-visit-requests'] });
            queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
        },
    });
}

/**
 * Hook for cancelling a next-visit request
 */
export function useCancelNextVisitRequest() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ requestId, data }) => cancelNextVisitRequest(requestId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['next-visit-requests'] });
        },
    });
}
