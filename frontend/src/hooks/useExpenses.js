import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getExpenses, getLabOrders, createExpense, deleteExpense, getFinancialStats } from '@/api';
import { getTodayStr } from '@/utils/toothUtils';
import { toast } from '@/shared/ui';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';

export function useExpenses() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [category, setCategory] = useState('ALL');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [page, setPage] = useState(0);
    const limit = 10;

    const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
    const [newExpense, setNewExpense] = useState({
        item_name: '',
        cost: '',
        category: 'General',
        date: getTodayStr(),
        notes: ''
    });

    const { data: expensesData, isLoading: loading } = useQuery({
        queryKey: ['expenses_tab_data'],
        queryFn: async () => {
            const [eRes, labRes, statsRes] = await Promise.all([
                getExpenses(),
                getLabOrders(),
                getFinancialStats()
            ]);

            const manualExpenses = (eRes.data || []).map(e => ({ ...e, type: 'manual' }));
            const labExpenses = (labRes.data || []).map(order => ({
                id: `lab-${order.id}`,
                original_id: order.id,
                item_name: `معمل: ${order.work_type} (${order.patient_name}) - ${order.laboratory_name}`,
                category: 'Laboratory',
                date: order.order_date,
                cost: order.cost,
                type: 'lab_order'
            }));

            const combined = [...manualExpenses, ...labExpenses].sort((a, b) => new Date(b.date) - new Date(a.date));

            return {
                allExpenses: combined,
                stats: statsRes.data
            };
        }
    });

    const allExpenses = useMemo(() => expensesData?.allExpenses || [], [expensesData]);
    const stats = expensesData?.stats || null;

    const filteredExpenses = useMemo(() => {
        return allExpenses.filter(exp => {
            if (search) {
                const query = search.toLowerCase();
                const matchesItem = (exp.item_name || '').toLowerCase().includes(query);
                const matchesCategory = (exp.category || '').toLowerCase().includes(query);
                if (!matchesItem && !matchesCategory) return false;
            }
            if (category !== 'ALL' && exp.category !== category) {
                return false;
            }
            if (startDate && new Date(exp.date) < new Date(startDate)) {
                return false;
            }
            if (endDate && new Date(exp.date) > new Date(`${endDate}T23:59:59`)) {
                return false;
            }
            return true;
        });
    }, [allExpenses, search, category, startDate, endDate]);

    const totalPages = Math.ceil(filteredExpenses.length / limit) || 1;
    const paginatedExpenses = useMemo(() => {
        const start = page * limit;
        return filteredExpenses.slice(start, start + limit);
    }, [filteredExpenses, page, limit]);

    const handleCreateExpense = async () => {
        if (!newExpense.item_name || !newExpense.cost) {
            return toast.error(t('billing.alerts.enter_item_cost'));
        }
        try {
            await createExpense({ ...newExpense, cost: parseFloat(newExpense.cost) });
            setIsExpenseModalOpen(false);
            setNewExpense({ item_name: '', cost: '', category: 'General', date: getTodayStr(), notes: '' });
            toast.success(t('billing.alerts.expense_add_success'));
            queryClient.invalidateQueries(['expenses_tab_data']);
            queryClient.invalidateQueries(['billing_data']);
        } catch (err) {
            logger.error(err);
            toast.error(t('billing.alerts.expense_add_fail'));
        }
    };

    const handleDeleteExpense = async (id) => {
        if (String(id).startsWith('lab-')) {
            return toast.error(t('billing.alerts.lab_delete_error'));
        }
        if (!confirm(t('billing.alerts.delete_expense_confirm'))) return;
        try {
            await deleteExpense(id);
            toast.success(t('billing.alerts.expense_delete_success'));
            queryClient.invalidateQueries(['expenses_tab_data']);
            queryClient.invalidateQueries(['billing_data']);
        } catch (err) {
            logger.error(err);
            toast.error(t('billing.alerts.delete_error'));
        }
    };

    return {
        expenses: paginatedExpenses,
        totalCount: filteredExpenses.length,
        stats,
        loading,
        search,
        setSearch,
        category,
        setCategory,
        startDate,
        setStartDate,
        endDate,
        setEndDate,
        page,
        setPage,
        totalPages,
        isExpenseModalOpen,
        setIsExpenseModalOpen,
        newExpense,
        setNewExpense,
        handleCreateExpense,
        handleDeleteExpense
    };
}

export default useExpenses;
