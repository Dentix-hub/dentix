import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
    getDashboardStats,
    getAppointments,
    getTodayPayments,
    getTodayDebtors
} from '@/api';
import { queryKeys } from '@/lib/queryClient';

/**
 * Prefetch hook for dashboard (used by sidebar hover)
 */
export function usePrefetchDashboard() {
    const queryClient = useQueryClient();

    return () => {
        queryClient.prefetchQuery({
            queryKey: queryKeys.dashboardStats,
            queryFn: async () => {
                const res = await getDashboardStats();
                return res.data;
            },
            staleTime: 30 * 1000,
        });
    };
}

/**
 * Hook for dashboard statistics
 */
export function useDashboardStats() {
    return useQuery({
        queryKey: queryKeys.dashboardStats,
        queryFn: async () => {
            const res = await getDashboardStats();
            return res.data;
        },
        staleTime: 30 * 1000, // 30 seconds
    });
}

/**
 * Hook for today's revenue payments
 */
export function useTodayPayments() {
    return useQuery({
        queryKey: queryKeys.todayPayments,
        queryFn: async () => {
            const res = await getTodayPayments();
            return res.data;
        },
        staleTime: 30 * 1000,
    });
}

/**
 * Hook for today's debtors
 */
export function useTodayDebtors() {
    return useQuery({
        queryKey: queryKeys.todayDebtors,
        queryFn: async () => {
            const res = await getTodayDebtors();
            return res.data;
        },
        staleTime: 30 * 1000,
    });
}

/**
 * Combined hook for all dashboard data
 */
export function useDashboard() {
    const stats = useDashboardStats();
    const todayPayments = useTodayPayments();
    const todayDebtors = useTodayDebtors();

    return {
        stats: stats.data,
        todayPayments: todayPayments.data,
        todayDebtors: todayDebtors.data,
        isLoading: stats.isLoading || todayPayments.isLoading || todayDebtors.isLoading,
        isError: stats.isError || todayPayments.isError || todayDebtors.isError,
        refetchAll: () => {
            stats.refetch();
            todayPayments.refetch();
            todayDebtors.refetch();
        }
    };
}
