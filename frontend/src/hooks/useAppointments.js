import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    getAppointments,
    createAppointment,
    updateAppointmentStatus,
    updateAppointment,
    deleteAppointment
} from '@/api';
import { queryKeys } from '@/lib/queryClient';

/**
 * Hook for fetching appointments with caching
 */
export function useAppointments() {
    return useQuery({
        queryKey: queryKeys.appointments,
        queryFn: async () => {
            const res = await getAppointments();
            return res.data;
        },
        staleTime: 30 * 1000, // 30 seconds
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
