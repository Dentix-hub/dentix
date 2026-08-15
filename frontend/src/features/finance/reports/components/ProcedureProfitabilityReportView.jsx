import { useTranslation } from 'react-i18next';
import {
    Activity,
    DollarSign,
    TrendingUp,
    Percent,
    Sparkles,
} from 'lucide-react';
import MetricCard from '../../components/MetricCard';
import DataTable from '../../components/DataTable';
import Money from '../../components/Money';

/**
 * Procedure Profitability Report View (§18 MASTER_SPEC, `FIN-RPT-006`).
 */
export default function ProcedureProfitabilityReportView({ data = [], isLoading, isError, onRetry }) {
    const { t } = useTranslation();

    const totalProcedures = data.length;
    const avgMargin = data.length > 0
        ? (data.reduce((sum, p) => sum + (Number(p.margin_percent || p.profit_margin_percent) || 0), 0) / data.length).toFixed(1)
        : '0.0';

    const columns = [
        {
            id: 'procedure_name',
            header: t('appointments.procedure', 'الإجراء الطبي'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">
                        {row.name || row.procedure_name}
                    </span>
                    <span className="text-[11px] text-text-secondary">
                        {row.category || t('common.general', 'عام')}
                    </span>
                </div>
            ),
        },
        {
            id: 'price',
            header: t('finance.metrics.invoiced', 'سعر الخدمة'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.price || row.base_price || 0} size="sm" />
            ),
        },
        {
            id: 'cost',
            header: t('finance.expenses.direct_total', 'تكلفة المواد'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.material_cost || row.cost || 0} size="sm" colored />
            ),
        },
        {
            id: 'profit_margin',
            header: t('finance.reports.margin_amount', 'هامش الربح'),
            align: 'end',
            sortable: false,
            cell: (row) => {
                const price = Number(row.price || row.base_price || 0);
                const cost = Number(row.material_cost || row.cost || 0);
                const margin = row.profit_margin !== undefined ? row.profit_margin : (price - cost);
                return <Money amount={margin} size="sm" colored />;
            },
        },
        {
            id: 'margin_percent',
            header: t('finance.reports.margin_percent_short', 'نسبة الهامش'),
            align: 'end',
            sortable: false,
            width: '120px',
            cell: (row) => {
                const percent = row.margin_percent || row.profit_margin_percent || 0;
                return (
                    <span className="font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400">
                        {parseFloat(percent).toFixed(1)}%
                    </span>
                );
            },
        },
    ];

    return (
        <div className="space-y-6">
            {/* Top KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricCard
                    title={t('finance.reports.procedures_analyzed', 'عدد الإجراءات المحللة')}
                    amount={totalProcedures}
                    scope="all_time"
                    subtitle={t('finance.reports.procedures_sub', 'الخدمات المربوطة بجدول تكلفة المواد')}
                    icon={Activity}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.reports.avg_margin', 'متوسط هامش الربح للإجراءات')}
                    amount={Number(avgMargin)}
                    scope="all_time"
                    subtitle={`${avgMargin}% ${t('finance.reports.avg_margin_sub', 'متوسط العائد على تكلفة الخامات')}`}
                    icon={Percent}
                    colored
                    isLoading={isLoading}
                />
            </div>

            {/* Profitability Table */}
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                    <div>
                        <h3 className="text-sm font-bold text-text-primary">
                            {t('finance.reports.profitability_table_title', 'تحليل ربحية الخدمات والإجراءات')}
                        </h3>
                        <p className="text-xs text-text-secondary">
                            {t('finance.reports.profitability_table_sub', 'مقارنة سعر الخدمة وتكلفة المواد المستهلكة لتقدير العائد المالي')}
                        </p>
                    </div>
                </div>

                <DataTable
                    columns={columns}
                    data={data}
                    keyField="id"
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={onRetry}
                    emptyMessage={t('finance.reports.no_procedures_data', 'لا توجد بيانات تكاليف للإجراءات')}
                />
            </div>
        </div>
    );
}
