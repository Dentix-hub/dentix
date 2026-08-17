import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import {
    getComprehensiveStats,
    getPatientsReport,
    getDoctorRevenue,
    getAllProceduresFinancials,
} from '@/api/financials';
import { getExpenses } from '@/api/billing';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';
import {
    adaptComprehensiveStats,
    adaptPatientsReport,
    adaptExpensesReport,
    adaptProvidersReport,
    adaptProfitabilityReport,
} from '../utils/reportAdapters';

const REPORT_PAGE_SIZE = 200;

async function fetchAllPages(fetchPage, extractPayload) {
    const firstResponse = await fetchPage(0);
    const firstPayload = extractPayload(firstResponse);
    const firstItems = firstPayload.items || [];
    const total = Number(firstPayload.total || firstItems.length);
    const allItems = [...firstItems];

    for (let skip = REPORT_PAGE_SIZE; skip < total; skip += REPORT_PAGE_SIZE) {
        const response = await fetchPage(skip);
        const payload = extractPayload(response);
        if (!payload.items?.length) break;
        allItems.push(...payload.items);
    }

    return { ...firstPayload, total, items: allItems };
}

/**
 * Hook for managing Finance V2 Reports workspace (§18 MASTER_SPEC, GEMINI_REPAIR_PLAN R1).
 */
export function useReports() {
    const [searchParams, setSearchParams] = useSearchParams();

    const defaultDates = getPresetDates('this_month');
    const from = searchParams.get('from') || defaultDates.from;
    const to = searchParams.get('to') || defaultDates.to;
    const reportType = searchParams.get('type') || 'summary';
    const search = searchParams.get('q') || '';

    const updateDateRange = ({ from: newFrom, to: newTo }) => {
        const params = new URLSearchParams(searchParams);
        if (newFrom) params.set('from', newFrom);
        else params.delete('from');
        if (newTo) params.set('to', newTo);
        else params.delete('to');
        setSearchParams(params);
    };

    const setReportType = (newType) => {
        const params = new URLSearchParams(searchParams);
        params.set('type', newType);
        setSearchParams(params);
    };

    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        if (newSearch) params.set('q', newSearch);
        else params.delete('q');
        setSearchParams(params);
    };

    // 1. Summary Query
    const summaryQuery = useQuery({
        queryKey: financeKeys.reports('summary', { from, to }),
        queryFn: async () => {
            const res = await getComprehensiveStats(from, to);
            const raw = res.data?.data || res.data || {};
            return adaptComprehensiveStats(raw);
        },
        enabled: reportType === 'summary' && Boolean(from && to),
        staleTime: 60 * 1000,
    });

    // 2. Collections Query
    const collectionsQuery = useQuery({
        queryKey: financeKeys.reports('collections', { from, to, search }),
        queryFn: async () => {
            const raw = await fetchAllPages(
                (skip) => getPatientsReport({
                    start_date: from,
                    end_date: to,
                    search: search || undefined,
                    skip,
                    limit: REPORT_PAGE_SIZE,
                }),
                (res) => {
                    const data = res.data?.data || res.data || {};
                    return { ...data, items: Array.isArray(data.patients) ? data.patients : [] };
                },
            );
            return adaptPatientsReport({ ...raw, patients: raw.items });
        },
        enabled: reportType === 'collections' && Boolean(from && to),
        staleTime: 60 * 1000,
    });

    // 3. Expenses Query
    const expensesQuery = useQuery({
        queryKey: financeKeys.reports('expenses', { from, to }),
        queryFn: async () => {
            const raw = await fetchAllPages(
                (skip) => getExpenses({
                    start_date: from,
                    end_date: to,
                    skip,
                    limit: REPORT_PAGE_SIZE,
                }),
                (res) => {
                    const data = res.data?.data || res.data || {};
                    return Array.isArray(data)
                        ? { items: data, total: data.length }
                        : { ...data, items: Array.isArray(data.items) ? data.items : [] };
                },
            );
            return adaptExpensesReport(raw.items);
        },
        enabled: reportType === 'expenses' && Boolean(from && to),
        staleTime: 60 * 1000,
    });

    // 4. Providers Query
    const providersQuery = useQuery({
        queryKey: financeKeys.reports('providers', { from, to }),
        queryFn: async () => {
            const res = await getDoctorRevenue(from, to);
            const raw = res.data?.data?.doctors || res.data?.data || res.data?.doctors || res.data || [];
            return adaptProvidersReport(raw);
        },
        enabled: reportType === 'providers' && Boolean(from && to),
        staleTime: 60 * 1000,
    });

    // 5. Profitability Query
    const profitabilityQuery = useQuery({
        queryKey: financeKeys.reports('profitability', {}),
        queryFn: async () => {
            const res = await getAllProceduresFinancials();
            const raw = res.data?.procedures || res.data?.data || res.data || [];
            return adaptProfitabilityReport(raw);
        },
        enabled: reportType === 'profitability',
        staleTime: 60 * 1000,
    });

    // Export CSV Helper with UTF-8 BOM and ObjectURL revocation
    const exportToCsv = (filename, headers, rows) => {
        const csvRows = [];
        csvRows.push(headers.join(','));

        rows.forEach((row) => {
            const escaped = row.map((val) => {
                const str = String(val ?? '').replace(/"/g, '""');
                return `"${str}"`;
            });
            csvRows.push(escaped.join(','));
        });

        const csvContent = '\uFEFF' + csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `${filename}_${from}_${to}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    };

    const currentQuery =
        reportType === 'summary'
            ? summaryQuery
            : reportType === 'collections'
            ? collectionsQuery
            : reportType === 'expenses'
            ? expensesQuery
            : reportType === 'providers'
            ? providersQuery
            : profitabilityQuery;

    return {
        reportType,
        from,
        to,
        search,
        summaryData: summaryQuery.data || adaptComprehensiveStats({}),
        collectionsData: collectionsQuery.data || adaptPatientsReport({}),
        expensesData: expensesQuery.data || [],
        providersData: providersQuery.data || [],
        profitabilityData: profitabilityQuery.data || [],
        isLoading: currentQuery.isLoading,
        isError: currentQuery.isError,
        refetch: currentQuery.refetch,
        setReportType,
        updateDateRange,
        updateSearch,
        exportToCsv,
    };
}
