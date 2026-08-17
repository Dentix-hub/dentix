import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import {
    getSalariesStatus,
    recordSalaryPayment,
    deleteSalaryPayment,
    updateStaffCompensation,
    updateHireDate,
} from '@/api/financials';
import { financeKeys } from '../../queryKeys';

/**
 * Helper to get current month in YYYY-MM format.
 */
export function getCurrentMonthStr() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
}

/**
 * Hook for managing Payroll V2 state, monthly records, payments, and staff compensation rules (§16 MASTER_SPEC, GEMINI_REPAIR_PLAN R3).
 */
export function usePayroll() {
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();

    const currentMonth = getCurrentMonthStr();
    const month = searchParams.get('month') || currentMonth;
    const search = searchParams.get('q') || '';

    // 1. Fetch Salaries for Month
    const payrollQuery = useQuery({
        queryKey: financeKeys.payroll(month),
        queryFn: async () => {
            const res = await getSalariesStatus(month);
            const data = res.data?.data || res.data || {};
            return data.employees || [];
        },
        enabled: Boolean(month),
        staleTime: 30 * 1000,
    });

    const employees = payrollQuery.data || [];

    // Filter by search query
    const filteredEmployees = employees.filter((emp) => {
        if (!search.trim()) return true;
        return (emp.username || '').toLowerCase().includes(search.trim().toLowerCase());
    });

    // Authoritative Aggregates derived from backend employee state
    const totalPayable = employees.reduce(
        (sum, emp) => sum + (Number(emp.payable_amount !== undefined ? emp.payable_amount : emp.prorated_salary) || 0),
        0
    );
    const totalPaid = employees.reduce(
        (sum, emp) => sum + (Number(emp.paid_amount !== undefined ? emp.paid_amount : (emp.payment?.amount || 0)) || 0),
        0
    );
    const totalRemaining = employees.reduce(
        (sum, emp) => sum + (Number(emp.remaining_amount !== undefined ? emp.remaining_amount : Math.max(0, (emp.payable_amount || emp.prorated_salary || 0) - (emp.paid_amount || 0))) || 0),
        0
    );
    const employeeCount = employees.length;

    // Month Navigation
    const setMonth = (newMonth) => {
        const params = new URLSearchParams(searchParams);
        if (newMonth && newMonth !== currentMonth) {
            params.set('month', newMonth);
        } else {
            params.delete('month');
        }
        setSearchParams(params);
    };

    const updateSearch = (newSearch) => {
        const params = new URLSearchParams(searchParams);
        if (newSearch) params.set('q', newSearch);
        else params.delete('q');
        setSearchParams(params);
    };

    // 2. Mutations
    const recordPaymentMutation = useMutation({
        mutationFn: ({ userId, amount, isPartial, daysWorked, notes }) =>
            recordSalaryPayment(userId, month, amount, isPartial, daysWorked, notes),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.payroll(month) });
            queryClient.invalidateQueries({ queryKey: financeKeys.overview() });
            queryClient.invalidateQueries({ queryKey: financeKeys.activity() });
        },
    });

    const deletePaymentMutation = useMutation({
        mutationFn: (paymentId) => deleteSalaryPayment(paymentId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.payroll(month) });
            queryClient.invalidateQueries({ queryKey: financeKeys.overview() });
            queryClient.invalidateQueries({ queryKey: financeKeys.activity() });
        },
    });

    const updateStaffRulesMutation = useMutation({
        mutationFn: async ({ userId, salary, hireDate }) => {
            if (salary !== undefined) {
                await updateStaffCompensation(userId, 0, salary, 0);
            }
            if (hireDate !== undefined) {
                await updateHireDate(userId, hireDate);
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: financeKeys.payroll(month) });
            queryClient.invalidateQueries({ queryKey: financeKeys.overview() });
        },
    });

    return {
        month,
        employees: filteredEmployees,
        rawEmployees: employees,
        totalPayable,
        totalPaid,
        totalRemaining,
        employeeCount,
        search,
        isLoading: payrollQuery.isLoading,
        isError: payrollQuery.isError,
        refetch: payrollQuery.refetch,
        setMonth,
        updateSearch,
        recordPayment: recordPaymentMutation.mutateAsync,
        isRecording: recordPaymentMutation.isPending,
        deletePayment: deletePaymentMutation.mutateAsync,
        isDeleting: deletePaymentMutation.isPending,
        updateStaffRules: updateStaffRulesMutation.mutateAsync,
        isUpdatingRules: updateStaffRulesMutation.isPending,
    };
}
