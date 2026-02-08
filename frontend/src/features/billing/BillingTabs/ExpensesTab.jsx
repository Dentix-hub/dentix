import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, Plus, Calendar, Trash2 } from 'lucide-react';
import { Button, Card, EmptyState, StatCard } from '@/shared/ui';

import { useTranslation } from 'react-i18next';
const ExpensesTab = ({ expenses, stats, setIsExpenseModalOpen, handleDeleteExpense }) => {
    const { t } = useTranslation();
    return (
        <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatCard
                    title={t('billing.stats.total_income')}
                    value={`${(stats?.total_received || 0).toLocaleString()}`}
                    icon={TrendingUp}
                    trend="up"
                    color="success"
                />
                <StatCard
                    title={t('billing.stats.total_expenses')}
                    value={`${(stats?.total_expenses || 0).toLocaleString()}`}
                    icon={TrendingDown}
                    trend="down"
                    color="danger"
                />
                <StatCard
                    title={t('billing.stats.net_profit')}
                    value={`${(stats?.net_profit || 0).toLocaleString()}`}
                    icon={DollarSign}
                    color={(stats?.net_profit || 0) >= 0 ? "primary" : "danger"}
                />
            </div>

            {/* Expenses Table */}
            <Card className="overflow-hidden">
                <div className="p-6 border-b border-border flex items-center justify-between bg-surface">
                    <div className="flex items-center gap-4">
                        <div className="w-1.5 h-8 bg-danger rounded-full"></div>
                        <h3 className="font-black text-xl text-text-primary">{t('billing.expenses.title')}</h3>
                    </div>
                    <Button
                        onClick={() => setIsExpenseModalOpen(true)}
                        variant="danger"
                    >
                        <Plus size={18} className="mr-2" /> {t('billing.expenses.add')}
                    </Button>
                </div>
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
                                        <td className="p-4 font-bold text-text-primary">{exp.item_name}</td>
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
                                    <Plus size={16} className="mr-2" /> {t('billing.expenses.add_first')}
                                </Button>
                            }
                        />
                    )}
                </div>
            </Card>
        </div>
    );
};

export default ExpensesTab;
