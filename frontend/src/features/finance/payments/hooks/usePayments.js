import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getPayments, createPayment, deletePayment } from '@/api/billing';
import { financeKeys } from '../../queryKeys';

/**
 * Hook for managing Payments V2 data, server filters, pagination, and mutations.
 */
export function usePayments(pageSize = 20) {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();

    const search = searchParams.get('q') || '';
    const from = searchParams.get('from') || '';
    const to = searchParams.get('to') || '';
    const pageParam = parseInt(searchParams.get('page') || '1', 10);
    const currentPage = isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;

    const skip = (currentPage - 1) * pageSize;

    // 1. Fetch Paginated Payments
    const paymentsQuery = useQuery({
        queryKey: financeKeys.payments({ search, from, to, skip, limit: pageSize }),
        queryFn: async () => {
            const params = {
                skip,
                limit: pageSize + 1, // fetch 1 extra to determine if next page exists
            };
            if (search.trim()) params.search = search.trim();
            if (from) params.start_date = from;
            if (to) params.end_date = to;

            const res = await getPayments(params);
            const list = Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
            return list;
        },
        staleTime: 30 * 1000,
    });

    const rawData = paymentsQuery.data || [];
    const hasNextPage = rawData.length > pageSize;
    const items = hasNextPage ? rawData.slice(0, pageSize) : rawData;

    // Update URL Filter Helpers
    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        if (newSearch) params.set('q', newSearch);
        else params.delete('q');
        params.set('page', '1');
        setSearchParams(params);
    };

    const updateDateRange = (newFrom, newTo) => {
        const params = new URLSearchParams(searchParams);
        if (newFrom) params.set('from', newFrom);
        else params.delete('from');
        if (newTo) params.set('to', newTo);
        else params.delete('to');
        params.set('page', '1');
        setSearchParams(params);
    };

    const setPage = (newPage) => {
        const params = new URLSearchParams(searchParams);
        params.set('page', String(newPage));
        setSearchParams(params);
    };

    // 2. Record Payment Mutation
    const createMutation = useMutation({
        mutationFn: (data) => createPayment(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.all });
        },
    });

    // 3. Delete Payment Mutation
    const deleteMutation = useMutation({
        mutationFn: (id) => deletePayment(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.all });
        },
    });

    return {
        items,
        search,
        from,
        to,
        currentPage,
        pageSize,
        hasNextPage,
        hasPrevPage: currentPage > 1,
        isLoading: paymentsQuery.isLoading,
        isError: paymentsQuery.isError,
        refetch: paymentsQuery.refetch,
        updateSearch,
        updateDateRange,
        setPage,
        createPayment: createMutation.mutateAsync,
        isCreating: createMutation.isPending,
        deletePayment: deleteMutation.mutateAsync,
        isDeleting: deleteMutation.isPending,
    };
}
