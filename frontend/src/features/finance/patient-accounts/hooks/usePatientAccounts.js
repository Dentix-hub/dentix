import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getPatientsReport, getFinanceSummary } from '@/api/financials';
import { createPayment } from '@/api/billing';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';

const parseFileNumber = (value) => {
    if (!value) return null;
    const normalized = String(value).trim().replace(/^#/, '');
    if (!/^\d{1,9}$/.test(normalized)) return null;
    const parsed = Number.parseInt(normalized, 10);
    return parsed > 0 ? parsed : null;
};

/**
 * Hook for managing Patient Accounts & Receivables data.
 * Patient.file_number is the stable Patient.id, so short numeric/# searches are
 * normalized to the explicit patient_id server filter while phone/name searches
 * retain the legacy text-search contract.
 */
export function usePatientAccounts(pageSize = 20) {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();

    const textSearch = searchParams.get('q') || '';
    const fileNumber = parseFileNumber(searchParams.get('file_number'));
    const search = fileNumber ? String(fileNumber) : textSearch;
    const from = searchParams.get('from') || '';
    const to = searchParams.get('to') || '';
    const outstandingOnly = searchParams.get('filter') === 'debtors';
    const pageParam = Number.parseInt(searchParams.get('page') || '1', 10);
    const currentPage = Number.isNaN(pageParam) || pageParam < 1 ? 1 : pageParam;

    const skip = (currentPage - 1) * pageSize;
    const defaultStatsRange = getPresetDates('this_month');
    const statsFrom = from || defaultStatsRange.from;
    const statsTo = to || defaultStatsRange.to;

    const accountsQuery = useQuery({
        queryKey: financeKeys.receivables({
            search: textSearch,
            fileNumber,
            from,
            to,
            outstandingOnly,
            skip,
            limit: pageSize,
        }),
        queryFn: async () => {
            const params = {
                skip,
                limit: pageSize,
                outstanding_only: outstandingOnly,
            };
            if (fileNumber) params.patient_id = fileNumber;
            else if (textSearch.trim()) params.search = textSearch.trim();
            if (from) params.start_date = from;
            if (to) params.end_date = to;

            const res = await getPatientsReport(params);
            return res.data?.data || res.data || { total: 0, patients: [] };
        },
        staleTime: 30 * 1000,
    });

    const statsQuery = useQuery({
        queryKey: financeKeys.summary({ from: statsFrom, to: statsTo }),
        queryFn: async () => {
            const res = await getFinanceSummary(statsFrom, statsTo);
            return res.data?.data || res.data;
        },
        staleTime: 60 * 1000,
    });

    const accountsData = accountsQuery.data || { total: 0, patients: [] };
    const items = accountsData.patients || [];
    const totalCount = accountsData.total || 0;

    const statsData = statsQuery.data;
    const allTimeOutstanding = Number(
        statsData?.income?.all_time_outstanding
        ?? statsData?.income?.outstanding
        ?? 0
    );

    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        const normalizedFileNumber = parseFileNumber(newSearch);
        if (normalizedFileNumber) {
            params.set('file_number', String(normalizedFileNumber));
            params.delete('q');
        } else {
            params.delete('file_number');
            if (newSearch) params.set('q', newSearch);
            else params.delete('q');
        }
        params.delete('page');
        setSearchParams(params);
    };

    const updateFilter = (filterType) => {
        const params = new URLSearchParams(searchParams);
        if (filterType === 'debtors') params.set('filter', 'debtors');
        else params.delete('filter');
        params.delete('page');
        setSearchParams(params);
    };

    const setPage = (newPage) => {
        const params = new URLSearchParams(searchParams);
        if (newPage > 1) params.set('page', String(newPage));
        else params.delete('page');
        setSearchParams(params);
    };

    const createMutation = useMutation({
        mutationFn: (data) => createPayment(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.receivablesRoot() });
            queryClient.invalidateQueries({ queryKey: financeKeys.summaryRoot() });
            queryClient.invalidateQueries({ queryKey: financeKeys.paymentsRoot() });
            queryClient.invalidateQueries({ queryKey: financeKeys.activityRoot() });
        },
    });

    return {
        items,
        totalCount,
        allTimeOutstanding,
        search,
        fileNumber,
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
