import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getFinancialActivity } from '@/api/financials';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';

/**
 * Hook for managing unified Financial Activity feed (§17 MASTER_SPEC, `FIN-ACT-002`, `FIN-ACT-003`).
 * Supports server-side pagination, date range filtering, type filtering, and search.
 */
export function useFinancialActivity(pageSize = 20) {
    const [searchParams, setSearchParams] = useSearchParams();

    const defaultDates = getPresetDates('this_month');
    const from = searchParams.get('from') || defaultDates.from;
    const to = searchParams.get('to') || defaultDates.to;
    const type = searchParams.get('type') || 'all';
    const search = searchParams.get('q') || '';
    const page = parseInt(searchParams.get('page') || '1', 10);

    const skip = (page - 1) * pageSize;
    const limit = pageSize;

    const queryParams = {
        start_date: from,
        end_date: to,
        types: type !== 'all' ? type : undefined,
        search: search.trim() || undefined,
        skip,
        limit,
    };

    const activityQuery = useQuery({
        queryKey: financeKeys.activity(queryParams),
        queryFn: async () => {
            const res = await getFinancialActivity(queryParams);
            return res.data?.data || res.data || {
                events: [],
                total_count: 0,
                total_inflow: 0,
                total_outflow: 0,
                net_flow: 0,
            };
        },
        enabled: Boolean(from && to),
        staleTime: 30 * 1000,
    });

    const data = activityQuery.data || {
        events: [],
        total_count: 0,
        total_inflow: 0,
        total_outflow: 0,
        net_flow: 0,
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

    const updateType = (newType) => {
        const params = new URLSearchParams(searchParams);
        if (newType && newType !== 'all') {
            params.set('type', newType);
        } else {
            params.delete('type');
        }
        params.set('page', '1');
        setSearchParams(params);
    };

    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        if (newSearch) {
            params.set('q', newSearch);
        } else {
            params.delete('q');
        }
        params.set('page', '1');
        setSearchParams(params);
    };

    const setPage = (newPage) => {
        const params = new URLSearchParams(searchParams);
        if (newPage > 1) {
            params.set('page', String(newPage));
        } else {
            params.delete('page');
        }
        setSearchParams(params);
    };

    return {
        events: data.events || [],
        totalCount: data.total_count || 0,
        totalInflow: data.total_inflow || 0,
        totalOutflow: data.total_outflow || 0,
        netFlow: data.net_flow || 0,
        from,
        to,
        type,
        search,
        page,
        pageSize,
        isLoading: activityQuery.isLoading,
        isError: activityQuery.isError,
        refetch: activityQuery.refetch,
        updateDateRange,
        updateType,
        updateSearch,
        setPage,
    };
}
