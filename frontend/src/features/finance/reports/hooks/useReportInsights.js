import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';

import {
    getMaterialMarginReport,
    getPeriodComparisonReport,
} from '@/api/financials';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';

const MATERIAL_PAGE_SIZE = 25;

function positiveInt(value, fallback = 1) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function useReportInsights() {
    const [searchParams, setSearchParams] = useSearchParams();
    const defaults = getPresetDates('this_month');

    const from = searchParams.get('from') || defaults.from;
    const to = searchParams.get('to') || defaults.to;
    const search = searchParams.get('q') || '';
    const page = positiveInt(searchParams.get('page'), 1);
    const sort = ['name_asc', 'name_desc', 'price_asc', 'price_desc'].includes(
        searchParams.get('sort'),
    )
        ? searchParams.get('sort')
        : 'name_asc';

    const updateParams = (updates) => {
        const next = new URLSearchParams(searchParams);
        Object.entries(updates).forEach(([key, value]) => {
            if (value === undefined || value === null || value === '') next.delete(key);
            else next.set(key, String(value));
        });
        setSearchParams(next, { replace: true });
    };

    const comparisonQuery = useQuery({
        queryKey: financeKeys.periodComparison({ from, to }),
        queryFn: async () => {
            const response = await getPeriodComparisonReport({
                start_date: from,
                end_date: to,
            });
            return response.data;
        },
        enabled: Boolean(from && to),
        staleTime: 60 * 1000,
    });

    const materialQuery = useQuery({
        queryKey: financeKeys.materialMargin({ search, page, sort, limit: MATERIAL_PAGE_SIZE }),
        queryFn: async () => {
            const response = await getMaterialMarginReport({
                search: search || undefined,
                skip: (page - 1) * MATERIAL_PAGE_SIZE,
                limit: MATERIAL_PAGE_SIZE,
                sort,
            });
            return response.data;
        },
        staleTime: 2 * 60 * 1000,
    });

    const setSearch = (value) => updateParams({ q: value, page: 1 });
    const setSort = (value) => updateParams({ sort: value, page: 1 });
    const setPage = (value) => updateParams({ page: Math.max(1, value) });

    return {
        from,
        to,
        search,
        sort,
        page,
        pageSize: MATERIAL_PAGE_SIZE,
        comparisonQuery,
        materialQuery,
        setSearch,
        setSort,
        setPage,
    };
}
