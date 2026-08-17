import { useTranslation } from 'react-i18next';
import {
    Receipt,
    Percent,
    PieChart,
    Layers,
} from 'lucide-react';
import MetricCard from '../../components/MetricCard';
import DataTable from '../../components/DataTable';
import Money from '../../components/Money';
import ScopeBadge from '../../components/ScopeBadge';

/**
 * Expense by Category Report View (§18 MASTER_SPEC, `FIN-RPT-004`).
 */
export default function ExpenseCategoryReportView({ data = [], isLoading, isError, onRetry }) {
    const { t } = useTranslation();

    // Group expenses by category
    const categoriesMap = {};
    let totalExpenseAmount = 0;

    data.forEach((exp) => {
        const cat = exp.category || t('finance.expenses.category_general', 'عام / متنوع');
        const amount = Number(exp.amount || 0);
        totalExpenseAmount += amount;

        if (!categoriesMap[cat]) {
            categoriesMap[cat] = {
                category: cat,
                total: 0,
                count: 0,
            };
        }
        categoriesMap[cat].total += amount;
        categoriesMap[cat].count += 1;
    });

    const categoryList = Object.values(categoriesMap)
        .map((cat) => ({
            ...cat,
            share: totalExpenseAmount > 0 ? ((cat.total / totalExpenseAmount) * 100).toFixed(1) : '0.0',
        }))
        .sort((a, b) => b.total - a.total);

    const columns = [
        {
            id: 'category',
            header: t('finance.expenses.category', 'بند المصروف'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">{row.category}</span>
                    <span className="text-[11px] text-text-secondary">
                        {row.count} {t('finance.expenses.records_count', 'سجل')}
                    </span>
                </div>
            ),
        },
        {
            id: 'share',
            header: t('finance.reports.share_percent', 'النسبة من الإجمالي'),
            sortable: false,
            width: '140px',
            cell: (row) => (
                <div className="space-y-1">
                    <span className="text-xs font-mono font-bold text-primary block">
                        {row.share}%
                    </span>
                    <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-primary h-1.5 rounded-full"
                            style={{ width: `${Math.min(100, parseFloat(row.share))}%` }}
                        />
                    </div>
                </div>
            ),
        },
        {
            id: 'total',
            header: t('finance.activity.movement', 'إجمالي المنصرف'),
            align: 'end',
            sortable: false,
            width: '160px',
            cell: (row) => (
                <Money amount={row.total} size="sm" colored />
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Top KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard
                    title={t('finance.expenses.total_expenses', 'إجمالي المصروفات المباشرة')}
                    amount={totalExpenseAmount}
                    scope="period"
                    subtitle={`${data.length} ${t('finance.expenses.records_count', 'عملية صرف مسجلة')}`}
                    icon={Receipt}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.reports.categories_count', 'عدد البنود التشغيلية')}
                    amount={categoryList.length}
                    scope="period"
                    subtitle={t('finance.reports.categories_sub', 'تصنيفات المصروفات النشطة')}
                    icon={Layers}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.reports.top_category', 'أعلى بند استهلاكاً')}
                    amount={categoryList[0]?.total || 0}
                    scope="period"
                    subtitle={categoryList[0]?.category || '—'}
                    icon={PieChart}
                    isLoading={isLoading}
                />
            </div>

            {/* Category Breakdown Table */}
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                    <div>
                        <h3 className="text-sm font-bold text-text-primary">
                            {t('finance.reports.expense_category_title', 'تحليل وتوزيع المصروفات حسب البند')}
                        </h3>
                        <p className="text-xs text-text-secondary">
                            {t('finance.reports.expense_category_sub', 'توزيع النفقات التشغيلية المباشرة وحصتها المئوية من الميزانية')}
                        </p>
                    </div>
                    <ScopeBadge scope="period" />
                </div>

                <DataTable
                    columns={columns}
                    data={categoryList}
                    keyField="category"
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={onRetry}
                    emptyMessage={t('finance.expenses.no_expenses', 'لا توجد مصروفات مسجلة في هذه الفترة')}
                />
            </div>
        </div>
    );
}
