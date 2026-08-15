import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Receipt,
    Plus,
    Trash2,
    FlaskConical,
    PieChart,
    Calendar,
    Tag,
} from 'lucide-react';
import { useExpenses } from '../expenses/hooks/useExpenses';
import { useFinancePermissions } from '../useFinancePermissions';
import MetricCard from '../components/MetricCard';
import FilterBar from '../components/FilterBar';
import DateRangePicker from '../components/DateRangePicker';
import DataTable from '../components/DataTable';
import Money from '../components/Money';
import AddExpenseDrawer from '../expenses/components/AddExpenseDrawer';
import DeleteExpenseModal from '../expenses/components/DeleteExpenseModal';

/**
 * Expenses V2 Management Page (§13 MASTER_SPEC).
 * Displays manual operating expenses, distinguishes lab provenance, server search/filtering, and targeted mutations.
 */
export default function ExpensesPage() {
    const { t } = useTranslation();
    const { canWriteFinance } = useFinancePermissions();

    const {
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
        isLoading,
        isError,
        refetch,
        updateSearch,
        updateCategory,
        updateDateRange,
        setPage,
        createExpense,
        isCreating,
        deleteExpense,
        isDeleting,
    } = useExpenses(25);

    const [isAddDrawerOpen, setIsAddDrawerOpen] = useState(false);
    const [expenseToDelete, setExpenseToDelete] = useState(null);

    // Filters Definition
    const filterOptions = [
        {
            id: 'category',
            label: t('finance.expenses.category', 'التصنيف'),
            icon: Tag,
            options: [
                { value: '', label: t('common.all', 'الكل') },
                { value: 'Supplies', label: 'مستلزمات طبية (Supplies)' },
                { value: 'Utilities', label: 'فواتير وخدمات (Utilities)' },
                { value: 'Rent', label: 'إيجار (Rent)' },
                { value: 'Maintenance', label: 'صيانة (Maintenance)' },
                { value: 'Laboratory', label: 'معامل (Laboratory)' },
                { value: 'Salaries', label: 'رواتب وأجور (Salaries)' },
                { value: 'Other', label: 'أخرى (Other)' },
            ],
        },
    ];

    // Columns Definition for DataTable
    const columns = [
        {
            id: 'item_name',
            header: t('finance.expenses.item_name', 'بيان المصروف'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">
                        {row.item_name}
                    </span>
                    {row.notes && (
                        <span className="text-[11px] text-text-secondary truncate max-w-xs block">
                            {row.notes}
                        </span>
                    )}
                </div>
            ),
        },
        {
            id: 'source',
            header: t('finance.expenses.source', 'المصدر'),
            sortable: false,
            width: '110px',
            cell: (row) => (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-muted text-text-secondary border border-border/60">
                    <Receipt className="w-3 h-3 text-primary" />
                    <span>{t('finance.expenses.source_manual', 'يدوي')}</span>
                </span>
            ),
        },
        {
            id: 'category',
            header: t('finance.expenses.category', 'التصنيف'),
            sortable: false,
            width: '130px',
            cell: (row) => (
                <span className="inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-semibold bg-primary/5 text-primary border border-primary/10">
                    {row.category || 'Other'}
                </span>
            ),
        },
        {
            id: 'date',
            header: t('finance.expenses.date', 'التاريخ'),
            sortable: false,
            width: '120px',
            cell: (row) => (
                <span className="font-mono text-xs text-text-secondary">
                    {row.date ? new Date(row.date).toLocaleDateString('ar-EG') : '—'}
                </span>
            ),
        },
        {
            id: 'cost',
            header: t('finance.expenses.cost', 'المبلغ'),
            align: 'end',
            sortable: false,
            width: '130px',
            cell: (row) => (
                <Money
                    amount={row.cost}
                    size="sm"
                    colored
                />
            ),
        },
        {
            id: 'actions',
            header: t('common.actions', 'إجراءات'),
            align: 'end',
            sortable: false,
            width: '80px',
            cell: (row) => (
                <div className="flex items-center justify-end">
                    {canWriteFinance && (
                        <button
                            type="button"
                            onClick={() => setExpenseToDelete(row)}
                            className="p-1.5 rounded-lg text-text-secondary hover:text-destructive hover:bg-destructive/10 transition-colors"
                            title={t('common.delete', 'حذف')}
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    )}
                </div>
            ),
        },
    ];

    // Mobile Card Render
    const renderMobileCard = (row) => (
        <div
            key={row.id}
            className="p-4 rounded-xl border border-border bg-card space-y-2.5 shadow-xs"
        >
            <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                    <p className="text-sm font-bold text-text-primary">
                        {row.item_name}
                    </p>
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-primary/5 text-primary">
                            {row.category || 'Other'}
                        </span>
                        <span className="text-[11px] font-mono text-text-secondary">
                            {row.date ? new Date(row.date).toLocaleDateString('ar-EG') : '—'}
                        </span>
                    </div>
                </div>
                <div className="text-end space-y-1">
                    <Money amount={row.cost} colored size="sm" />
                    {canWriteFinance && (
                        <button
                            type="button"
                            onClick={() => setExpenseToDelete(row)}
                            className="p-1 text-text-secondary hover:text-destructive transition-colors block ms-auto"
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </div>
            {row.notes && (
                <p className="text-xs text-text-secondary pt-1 border-t border-border/40">
                    {row.notes}
                </p>
            )}
        </div>
    );

    return (
        <div className="space-y-6">
            {/* Top Headline Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard
                    title={t('finance.expenses.manual_total', 'المصروفات التشغيلية المباشرة')}
                    amount={manualExpensesTotal}
                    scope={from && to ? 'period' : 'all_time'}
                    subtitle={t('finance.expenses.manual_total_sub', 'المصروفات اليومية والمستلزمات المسجلة')}
                    icon={Receipt}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.expenses.lab_total', 'تكاليف المعامل والتركيبات')}
                    amount={labExpensesTotal}
                    scope={from && to ? 'period' : 'all_time'}
                    subtitle={t('finance.expenses.lab_total_sub', 'إجمالي مطالبات المعامل الخاصة بحالات المرضى')}
                    icon={FlaskConical}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.metrics.deductions', 'إجمالي الخصومات والالتزامات')}
                    amount={totalDeductions}
                    scope={from && to ? 'period' : 'all_time'}
                    subtitle={t('finance.expenses.deductions_sub', 'تشمل المصروفات + المعامل + أتعاب الأطباء والرواتب')}
                    icon={PieChart}
                    isLoading={isLoading}
                />
            </div>

            {/* Filter Bar & Header Actions */}
            <div className="space-y-3">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <DateRangePicker
                        value={{ from, to }}
                        onChange={updateDateRange}
                    />

                    {canWriteFinance && (
                        <button
                            type="button"
                            onClick={() => setIsAddDrawerOpen(true)}
                            className="flex items-center justify-center gap-2 py-2 px-4 text-xs font-bold text-white bg-primary hover:bg-primary/90 rounded-xl transition-all shadow-sm self-end sm:self-auto"
                        >
                            <Plus className="w-4 h-4" />
                            <span>{t('finance.expenses.add_btn', 'تسجيل مصروف')}</span>
                        </button>
                    )}
                </div>

                <FilterBar
                    searchValue={search}
                    onSearchChange={updateSearch}
                    searchPlaceholder={t('finance.expenses.search_placeholder', 'البحث في بيان المصروفات والملاحظات...')}
                    filters={filterOptions}
                    activeFilters={{ category }}
                    onFilterChange={(fId, val) => {
                        if (fId === 'category') updateCategory(val);
                    }}
                    onClearFilters={() => {
                        updateSearch('');
                        updateCategory('');
                        updateDateRange({ from: '', to: '' });
                    }}
                />
            </div>

            {/* Data Table */}
            <DataTable
                columns={columns}
                data={items}
                keyField="id"
                isLoading={isLoading}
                isError={isError}
                onRetry={refetch}
                renderMobileCard={renderMobileCard}
                emptyMessage={t('finance.expenses.no_expenses', 'لا توجد مصروفات مسجلة تطابق معايير البحث')}
                page={currentPage}
                pageSize={pageSize}
                totalItems={totalItems}
                onPageChange={setPage}
            />

            {/* Add Expense Drawer */}
            <AddExpenseDrawer
                isOpen={isAddDrawerOpen}
                onClose={() => setIsAddDrawerOpen(false)}
                onSubmit={createExpense}
                isSubmitting={isCreating}
            />

            {/* Delete Confirmation Modal */}
            <DeleteExpenseModal
                expense={expenseToDelete}
                isOpen={Boolean(expenseToDelete)}
                onClose={() => setExpenseToDelete(null)}
                onConfirm={async (id) => {
                    await deleteExpense(id);
                    setExpenseToDelete(null);
                }}
                isDeleting={isDeleting}
            />
        </div>
    );
}
