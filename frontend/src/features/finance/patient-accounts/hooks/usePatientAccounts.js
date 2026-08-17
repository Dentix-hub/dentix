import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getPatientsReport, getComprehensiveStats } from '@/api/financials';
import { createPayment } from '@/api/billing';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';

/**
 * Hook for managing Patient Accounts & Receivables data, server search, debtor filtering, and pagination.
 */
export function usePatientAccounts(pageSize = 20) {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();

    const search = searchParams.get('q') || '';
    const from = searchParams.get('from') || '';
    const to = searchParams.get('to') || '';
    const outstandingOnly = searchParams.get('filter') === 'debtors';
    const pageParam = parseInt(searchParams.get('page') || '1', 10);
    const currentPage = isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;

    const skip = (currentPage - 1) * pageSize;

    // 1. Fetch Paginated Patient Accounts Report
    const accountsQuery = useQuery({
        queryKey: financeKeys.receivables({ search, from, to, outstandingOnly, skip, limit: pageSize }),
        queryFn: async () => {
            const params = {
                skip,
                limit: pageSize,
                outstanding_only: outstandingOnly,
            };
            if (search.trim()) params.search = search.trim();
            if (from) params.start_date = from;
            if (to) params.end_date = to;

            const res = await getPatientsReport(params);
            return res.data?.data || res.data || { total: 0, patients: [] };
        },
        staleTime: 30 * 1000,
    });

    // 2. Fetch Comprehensive Stats for Clinic-wide Headline Debt Summary
    const statsQuery = useQuery({
        queryKey: financeKeys.overviewStats({ from, to }),
        queryFn: async () => {
            const res = await getComprehensiveStats(from, to);
            return res.data?.data || res.data;
        },
        staleTime: 60 * 1000,
    });

    const accountsData = accountsQuery.data || { total: 0, patients: [] };
    const items = accountsData.patients || [];
    const totalCount = accountsData.total || 0;

    const statsData = statsQuery.data;
    const allTimeOutstanding = Number(statsData?.income?.all_time_outstanding || statsData?.income?.outstanding) || 0;

    // Update URL Filter Helpers
    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        if (newSearch) params.set('q', newSearch);
        else params.delete('q');
        params.set('page', '1');
        setSearchParams(params);
    };

    const updateFilter = (filterType) => {
        const params = new URLSearchParams(searchParams);
        if (filterType === 'debtors') params.set('filter', 'debtors');
        else params.delete('filter');
        params.set('page', '1');
        setSearchParams(params);
    };

    const setPage = (newPage) => {
        const params = new URLSearchParams(searchParams);
        params.set('page', String(newPage));
        setSearchParams(params);
    };

    // Record Payment Mutation
    const createMutation = useMutation({
        mutationFn: (data) => createPayment(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.all });
        },
    });

    return {
        items,
        totalCount,
        allTimeOutstanding,
        search,
        from,
        to,
        outstandingOnly,
        currentPage,
        pageSize,
        isLoading: accountsQuery.isLoading,
        isError: accountsQuery.isError,
        refetch: () => {
            accountsQuery.refetch();
            statsQuery.refetch();
        },
        updateSearch,
        updateFilter,
        setPage,
        createPayment: createMutation.mutateAsync,
        isCreating: createMutation.isPending,
    };
}
