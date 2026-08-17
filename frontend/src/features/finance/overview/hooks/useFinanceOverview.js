import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getComprehensiveStats, getFinanceProfitabilityTrend } from '@/api/financials';
import { getAllPayments, getExpenses } from '@/api/billing';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';

/**
 * Hook for fetching all data required by the Finance Overview V2 page.
 * Respects URL date filters (`from` and `to`) and separates period metrics from all-time debt.
 */
export function useFinanceOverview() {
    const [searchParams] = useSearchParams();

    // Default to this_month if no query params provided
    const defaultDates = getPresetDates('this_month');
    const from = searchParams.get('from') || defaultDates.from;
    const to = searchParams.get('to') || defaultDates.to;

    // Determine approximate trend period
    let trendPeriod = '30d';
    try {
        const fromDate = new Date(from);
        const toDate = new Date(to);
        const diffDays = Math.ceil((toDate - fromDate) / (1000 * 60 * 60 * 24));
        if (diffDays <= 7) trendPeriod = '7d';
        else if (diffDays <= 31) trendPeriod = '30d';
        else trendPeriod = '90d';
    } catch {
        trendPeriod = '30d';
    }

    // 1. Comprehensive Financial Statistics
    const statsQuery = useQuery({
        queryKey: financeKeys.overviewStats({ from, to }),
        queryFn: async () => {
            const res = await getComprehensiveStats(from, to);
            return res.data?.data || res.data;
        },
        staleTime: 60 * 1000,
    });

    // 2. Profitability Trend Series
    const trendQuery = useQuery({
        queryKey: financeKeys.overviewTrends({ period: trendPeriod }),
        queryFn: async () => {
            const res = await getFinanceProfitabilityTrend(trendPeriod);
            return res.data?.data || res.data;
        },
        staleTime: 2 * 60 * 1000,
    });

    // 3. Recent Payments
    const paymentsQuery = useQuery({
        queryKey: financeKeys.payments({ limit: 8 }),
        queryFn: async () => {
            const res = await getAllPayments();
            const list = Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
            return list.slice(0, 8);
        },
        staleTime: 60 * 1000,
    });

    // 4. Recent Expenses
    const expensesQuery = useQuery({
        queryKey: financeKeys.expenses({ limit: 8 }),
        queryFn: async () => {
            const res = await getExpenses();
            const list = Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
            return list.slice(0, 8);
        },
        staleTime: 60 * 1000,
    });

    // Merge recent activity items chronologically
    const paymentsList = (paymentsQuery.data || []).map((p) => ({
        id: `pay-${p.id}`,
        rawId: p.id,
        type: 'payment',
        date: p.date ? new Date(p.date) : new Date(),
        dateStr: p.date ? String(p.date).split('T')[0] : '',
        title: p.patient_name || p.patient?.name || `مريض #${p.patient_id}`,
        subtitle: p.notes || (p.doctor_name ? `د. ${p.doctor_name}` : 'دفعة مريض'),
        amount: Number(p.amount) || 0,
        isIncome: true,
        to: `/finance/payments`,
    }));

    const expensesList = (expensesQuery.data || []).map((e) => ({
        id: `exp-${e.id}`,
        rawId: e.id,
        type: 'expense',
        date: e.date ? new Date(e.date) : new Date(),
        dateStr: e.date ? String(e.date).split('T')[0] : '',
        title: e.title || e.category || 'مصروف عام',
        subtitle: e.category ? `تصنيف: ${e.category}` : (e.notes || 'مصروف تشغيلي'),
        amount: Number(e.cost || e.amount) || 0,
        isIncome: false,
        to: `/finance/expenses`,
    }));

    const recentActivity = [...paymentsList, ...expensesList]
        .sort((a, b) => b.date - a.date)
        .slice(0, 10);

    const statsData = statsQuery.data;
    const income = statsData?.income || {};
    const deductions = statsData?.deductions || {};

    const netInvoiced = Number(income.total_revenue) || 0;
    const collected = Number(income.total_collected) || 0;
    const totalDeductions = Number(deductions.total_deductions) || 0;
    const netResult = Number(statsData?.net_profit) || (collected - totalDeductions);

    const allTimeOutstanding = Number(income.all_time_outstanding || income.outstanding) || 0;
    const periodBalance = Number(income.period_balance) || (netInvoiced - collected);

    const doctorDuesTotal = Number(deductions.doctor_dues?.total) || 0;
    const staffDuesTotal = Number(deductions.staff_dues?.total) || 0;

    return {
        from,
        to,
        // Raw queries
        statsQuery,
        trendQuery,
        paymentsQuery,
        expensesQuery,
        // Extracted Metrics
        netInvoiced,
        collected,
        totalDeductions,
        netResult,
        allTimeOutstanding,
        periodBalance,
        doctorDuesTotal,
        staffDuesTotal,
        // Processed Trends & Activity
        timeline: trendQuery.data?.timeline || [],
        recentActivity,
        isLoading: statsQuery.isLoading,
        isError: statsQuery.isError,
        refetch: () => {
            statsQuery.refetch();
            trendQuery.refetch();
            paymentsQuery.refetch();
            expensesQuery.refetch();
        },
    };
}
