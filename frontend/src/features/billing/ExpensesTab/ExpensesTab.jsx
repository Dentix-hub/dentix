import { TrendingDown, Plus, Calendar, Trash2, Search, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { Button, Card, EmptyState, DateTimePicker, Input } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import useExpenses from '@/hooks/useExpenses';
import ExpenseStats from './ExpenseStats';
import ExpenseFormModal from './ExpenseFormModal';

export default function ExpensesTab() {
    const { t } = useTranslation();
    const {
        expenses,
        totalCount,
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
    } = useExpenses();

    const categories = [
        { id: 'ALL', label: t('common.all', 'All') },
        { id: 'General', label: t('billing.expenses.categories.general') },
        { id: 'Materials', label: t('billing.expenses.categories.materials') },
        { id: 'Laboratory', label: t('billing.expenses.categories.laboratory', 'Laboratory') },
        { id: 'Salaries', label: t('billing.expenses.categories.salaries') },
        { id: 'Rent', label: t('billing.expenses.categories.rent') },
        { id: 'Utilities', label: t('billing.expenses.categories.utilities') },
        { id: 'Maintenance', label: t('billing.expenses.categories.maintenance') }
    ];

    return (
        <div className="space-y-6">
            {/* Stats Overview */}
            <ExpenseStats stats={stats} />

            {/* Expenses Card */}
            <Card className="overflow-hidden">
                {/* Card Header & Controls */}
                <div className="p-6 border-b border-border space-y-4 bg-surface">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex items-center gap-4">
                            <div className="w-1.5 h-8 bg-danger rounded-full"></div>
                            <div>
                                <h3 className="font-bold text-xl text-text-primary">{t('billing.expenses.title')}</h3>
                                <p className="text-xs text-text-secondary">{totalCount} {t('common.records', 'records')}</p>
                            </div>
                        </div>
                        <Button
                            onClick={() => setIsExpenseModalOpen(true)}
                            variant="danger"
                        >
                            <Plus size={18} className="me-2" /> {t('billing.expenses.add')}
                        </Button>
                    </div>

                    {/* Filters Row */}
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                        <div className="md:col-span-4 relative">
                            <Input
                                placeholder={t('common.search', 'Search expenses...')}
                                value={search}
                                onChange={(e) => {
                                    setSearch(e.target.value);
                                    setPage(0);
                                }}
                                className="ps-10"
                            />
                            <Search size={16} className="absolute start-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                        </div>
                        <div className="md:col-span-8 flex flex-wrap md:flex-nowrap items-center gap-3">
                            <div className="w-full md:w-36">
                                <DateTimePicker
                                    mode="date"
                                    value={startDate}
                                    onChange={(e) => {
                                        setStartDate(e.target.value);
                                        setPage(0);
                                    }}
                                    compact
                                />
                            </div>
                            <span className="text-text-secondary hidden md:inline">-</span>
                            <div className="w-full md:w-36">
                                <DateTimePicker
                                    mode="date"
                                    value={endDate}
                                    onChange={(e) => {
                                        setEndDate(e.target.value);
                                        setPage(0);
                                    }}
                                    compact
                                />
                            </div>
                        </div>
                    </div>

                    {/* Category Filter Chips */}
                    <div className="flex items-center gap-2 overflow-x-auto pb-1 custom-scrollbar">
                        <Filter size={14} className="text-text-secondary shrink-0" />
                        {categories.map(cat => (
                            <button
                                key={cat.id}
                                onClick={() => {
                                    setCategory(cat.id);
                                    setPage(0);
                                }}
                                className={`px-3 py-1 rounded-xl text-xs font-bold transition-all shrink-0 ${category === cat.id
                                    ? 'bg-danger text-white shadow-sm'
                                    : 'bg-surface-hover text-text-secondary hover:text-text-primary'
                                    }`}
                            >
                                {cat.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Expenses Table */}
                <div className="overflow-x-auto">
                    {expenses.length > 0 ? (
                        <table className="w-full text-right text-sm">
                            <thead className="bg-surface-hover text-text-secondary font-bold text-xs border-b border-border">
                                <tr>
                                    <th className="p-4">{t('billing.expenses.item')}</th>
                                    <th className="p-4">{t('billing.expenses.category')}</th>
                                    <th className="p-4">{t('billing.expenses.date')}</th>
                                    <th className="p-4">{t('billing.expenses.cost')}</th>
                                    <th className="p-4">{t('billing.expenses.actions')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {expenses.map(exp => (
                                    <tr key={exp.id} className="hover:bg-surface-hover transition-colors">
                                        <td className="p-4">
                                            <div className="font-bold text-text-primary">{exp.item_name}</div>
                                            {exp.notes && <div className="text-xs text-text-secondary mt-0.5">{exp.notes}</div>}
                                        </td>
                                        <td className="p-4">
                                            <span className="px-3 py-1 bg-surface-hover rounded-lg text-xs font-bold text-text-secondary">{exp.category}</span>
                                        </td>
                                        <td className="p-4 text-text-secondary flex items-center gap-2">
                                            <Calendar size={14} />
                                            {new Date(exp.date).toLocaleDateString('ar-EG')}
                                        </td>
                                        <td className="p-4 font-bold text-danger">{exp.cost.toLocaleString()}</td>
                                        <td className="p-4">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleDeleteExpense(exp.id)}
                                                className="text-text-secondary hover:text-danger hover:bg-red-50 dark:hover:bg-red-900/10"
                                            >
                                                <Trash2 size={16} />
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <EmptyState
                            icon={TrendingDown}
                            title={t('billing.expenses.no_data')}
                            description={t('billing.expenses.no_data_desc')}
                            action={
                                <Button onClick={() => setIsExpenseModalOpen(true)} variant="outline">
                                    <Plus size={16} className="me-2" /> {t('billing.expenses.add_first')}
                                </Button>
                            }
                        />
                    )}
                </div>

                {/* Pagination */}
                {!loading && totalPages > 1 && (
                    <div className="p-4 border-t border-border flex items-center justify-between">
                        <span className="text-xs font-bold text-text-secondary">
                            {t('common.page', 'Page')} {page + 1} {t('common.of', 'of')} {totalPages}
                        </span>
                        <div className="flex gap-2">
                            <Button
                                variant="secondary"
                                size="sm"
                                disabled={page === 0}
                                onClick={() => setPage(p => Math.max(0, p - 1))}
                                className="rounded-xl p-2"
                            >
                                <ChevronLeft size={16} />
                            </Button>
                            <Button
                                variant="secondary"
                                size="sm"
                                disabled={page >= totalPages - 1}
                                onClick={() => setPage(p => p + 1)}
                                className="rounded-xl p-2"
                            >
                                <ChevronRight size={16} />
                            </Button>
                        </div>
                    </div>
                )}
            </Card>

            {/* Modal */}
            <ExpenseFormModal
                isOpen={isExpenseModalOpen}
                onClose={() => setIsExpenseModalOpen(false)}
                newExpense={newExpense}
                setNewExpense={setNewExpense}
                handleCreateExpense={handleCreateExpense}
            />
        </div>
    );
}
