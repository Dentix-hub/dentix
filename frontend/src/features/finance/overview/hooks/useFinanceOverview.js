import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { getFinanceSummary, getFinanceProfitabilityTrend } from '@/api/financials';
import { getAllPayments, getExpenses } from '@/api/billing';
import { financeKeys } from '../../queryKeys';
import { getPresetDates } from '../../utils/datePresets';

const financeLink = (pathname, from, to, extra = {}) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    Object.entries(extra).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            params.set(key, String(value));
        }
    });
    const query = params.toString();
    return query ? `${pathname}?${query}` : pathname;
};

/**
 * Hook for fetching all data required by the Finance Overview V2 page.
 * Headline financial values come only from the authoritative backend summary.
 */
export function useFinanceOverview() {
    const [searchParams] = useSearchParams();

    const defaultDates = getPresetDates('this_month');
    const from = searchParams.get('from') || defaultDates.from;
    const to = searchParams.get('to') || defaultDates.to;

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

    const statsQuery = useQuery({
        queryKey: financeKeys.summary({ from, to }),
        queryFn: async () => {
            const res = await getFinanceSummary(from, to);
            return res.data?.data || res.data;
        },
        staleTime: 60 * 1000,
    });

    const trendQuery = useQuery({
        queryKey: financeKeys.overviewTrends({ period: trendPeriod, from, to }),
        queryFn: async () => {
            const res = await getFinanceProfitabilityTrend(trendPeriod, from, to);
            return res.data?.data || res.data;
        },
        staleTime: 2 * 60 * 1000,
    });

    const paymentsQuery = useQuery({
        queryKey: financeKeys.payments({ from, to, limit: 8, context: 'overview' }),
        queryFn: async () => {
            const res = await getAllPayments({ start_date: from, end_date: to, limit: 8 });
            const list = Array.isArray(res.data?.data) ? res.data.data : Array.isArray(res.data) ? res.data : [];
            return list.slice(0, 8);
        },
        staleTime: 60 * 1000,
    });

    const expensesQuery = useQuery({
        queryKey: financeKeys.expenses({ from, to, limit: 8, context: 'overview' }),
        queryFn: async () => {
            const res = await getExpenses({ start_date: from, end_date: to, limit: 8 });
            const payload = res.data?.data || res.data;
            const list = Array.isArray(payload)
                ? payload
                : Array.isArray(payload?.items)
                  ? payload.items
                  : [];
            return list.slice(0, 8);
        },
        staleTime: 60 * 1000,
    });

    const paymentsList = (paymentsQuery.data || []).map((payment) => ({
        id: `pay-${payment.id}`,
        rawId: payment.id,
        type: 'payment',
        date: payment.date ? new Date(payment.date) : new Date(),
        dateStr: payment.date ? String(payment.date).split('T')[0] : '',
        title: payment.patient_name || payment.patient?.name || `مريض #${payment.patient_id}`,
        subtitle: payment.notes || (payment.doctor_name ? `د. ${payment.doctor_name}` : 'دفعة مريض'),
        amount: Number(payment.amount) || 0,
        isIncome: true,
        to: financeLink('/finance/payments', from, to, {
            patient_id: payment.patient_id,
            payment_id: payment.id,
        }),
    }));

    const expensesList = (expensesQuery.data || []).map((expense) => ({
        id: `exp-${expense.id}`,
        rawId: expense.id,
        type: 'expense',
        date: expense.date ? new Date(expense.date) : new Date(),
        dateStr: expense.date ? String(expense.date).split('T')[0] : '',
        title: expense.title || expense.item_name || expense.category || 'مصروف عام',
        subtitle: expense.category ? `تصنيف: ${expense.category}` : (expense.notes || 'مصروف تشغيلي'),
        amount: Number(expense.cost || expense.amount) || 0,
        isIncome: false,
        to: financeLink('/finance/expenses', from, to),
    }));

    const recentActivity = [...paymentsList, ...expensesList]
        .sort((a, b) => b.date - a.date)
        .slice(0, 10);

    const statsData = statsQuery.data;
    const income = statsData?.income || {};
    const deductions = statsData?.deductions || {};

    const netInvoiced = Number(income.net_revenue ?? income.total_revenue ?? 0);
    const collected = Number(income.total_collected ?? 0);
    const totalDeductions = Number(deductions.total_deductions ?? 0);
    const netResult = Number(
        statsData?.net_operational_result ?? statsData?.net_profit ?? 0,
    );
    const allTimeOutstanding = Number(
        income.all_time_outstanding ?? income.outstanding ?? 0,
    );
    const periodBalance = Number(income.period_balance ?? 0);
    const doctorDuesTotal = Number(deductions.doctor_dues?.total ?? 0);
    const staffDuesTotal = Number(deductions.staff_dues?.total ?? 0);

    return {
        from,
        to,
        statsQuery,
        trendQuery,
        paymentsQuery,
        expensesQuery,
        netInvoiced,
        collected,
        totalDeductions,
        netResult,
        allTimeOutstanding,
        periodBalance,
        doctorDuesTotal,
        staffDuesTotal,
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
