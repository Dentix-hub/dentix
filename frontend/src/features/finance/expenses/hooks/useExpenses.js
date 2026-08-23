import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getExpenses, createExpense, deleteExpense } from '@/api/billing';
import { getFinanceSummary } from '@/api/financials';
import { financeKeys } from '../../queryKeys';

/**
 * Hook for managing Expenses V2 data, server search, category filters, and targeted invalidation.
 */
export function useExpenses(pageSize = 25) {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();

    const search = searchParams.get('q') || '';
    const category = searchParams.get('category') || '';
    const from = searchParams.get('from') || '';
    const to = searchParams.get('to') || '';
    const pageParam = parseInt(searchParams.get('page') || '1', 10);
    const currentPage = isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;

    const skip = (currentPage - 1) * pageSize;

    const expensesQuery = useQuery({
        queryKey: financeKeys.expenses({ search, category, from, to, skip, limit: pageSize }),
        queryFn: async () => {
            const params = {
                skip,
                limit: pageSize,
            };
            if (search.trim()) params.search = search.trim();
            if (category.trim()) params.category = category.trim();
            if (from) params.start_date = from;
            if (to) params.end_date = to;

            const res = await getExpenses(params);
            const data = res.data?.data || res.data || {};
            if (Array.isArray(data)) {
                return { items: data, total: data.length };
            }
            return {
                items: Array.isArray(data.items) ? data.items : [],
                total: Number(data.total || 0),
                source: data.source || 'manual_expense',
                provenance: data.provenance || null,
            };
        },
        staleTime: 30 * 1000,
    });

    // Summary cards are server-owned. Never sum the current page and present it
    // as a clinic/period aggregate.
    const statsQuery = useQuery({
        queryKey: financeKeys.summary({ from, to }),
        queryFn: async () => {
            const res = await getFinanceSummary(from, to);
            return res.data?.data || res.data;
        },
        enabled: Boolean(from && to),
        staleTime: 60 * 1000,
    });

    const items = expensesQuery.data?.items || [];
    const totalItems = expensesQuery.data?.total || 0;
    const stats = statsQuery.data;

    const manualExpensesTotal = Number(stats?.deductions?.expenses ?? 0);
    const labExpensesTotal = Number(stats?.deductions?.lab_costs ?? 0);
    const totalDeductions = Number(stats?.deductions?.total_deductions ?? 0);

    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        if (newSearch) params.set('q', newSearch);
        else params.delete('q');
        params.set('page', '1');
        setSearchParams(params);
    };

    const updateCategory = (newCat) => {
        const params = new URLSearchParams(searchParams);
        if (newCat) params.set('category', newCat);
        else params.delete('category');
        params.set('page', '1');
        setSearchParams(params);
    };

    const updateDateRange = ({ from: newFrom, to: newTo }) => {
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

    const invalidateExpenseTruth = () => {
        queryClient.invalidateQueries({ queryKey: financeKeys.expensesRoot() });
        queryClient.invalidateQueries({ queryKey: financeKeys.summaryRoot() });
        queryClient.invalidateQueries({ queryKey: financeKeys.activityRoot() });
        queryClient.invalidateQueries({ queryKey: financeKeys.reportsRoot() });
    };

    const createMutation = useMutation({
        mutationFn: (data) => createExpense(data),
        onSuccess: invalidateExpenseTruth,
    });

    const deleteMutation = useMutation({
        mutationFn: (id) => deleteExpense(id),
        onSuccess: invalidateExpenseTruth,
    });

    return {
        items,
        totalItems,
        manualExpensesTotal,
        labExpensesTotal,
        totalDeductions,
        search,
        category,
        from,
        to,
        currentPage,
        pageSize,
        isLoading: expensesQuery.isLoading,
        isError: expensesQuery.isError,
        refetch: () => {
            expensesQuery.refetch();
            if (from && to) statsQuery.refetch();
        },
        updateSearch,
        updateCategory,
        updateDateRange,
        setPage,
        createExpense: createMutation.mutateAsync,
        isCreating: createMutation.isPending,
        deleteExpense: deleteMutation.mutateAsync,
        isDeleting: deleteMutation.isPending,
    };
}
