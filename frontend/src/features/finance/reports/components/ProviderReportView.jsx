import { useTranslation } from 'react-i18next';
import {
    UserCheck,
    TrendingUp,
    DollarSign,
    FlaskConical,
} from 'lucide-react';
import MetricCard from '../../components/MetricCard';
import DataTable from '../../components/DataTable';
import Money from '../../components/Money';
import ScopeBadge from '../../components/ScopeBadge';

/**
 * Provider Financial Performance Report (§18 MASTER_SPEC, `FIN-RPT-005`).
 */
export default function ProviderReportView({ data = [], isLoading, isError, onRetry }) {
    const { t } = useTranslation();

    const totalProduction = data.reduce((sum, d) => sum + (Number(d.revenue) || 0), 0);
    const totalCollected = data.reduce((sum, d) => sum + (Number(d.collected) || 0), 0);
    const totalLabCosts = data.reduce((sum, d) => sum + (Number(d.lab_cost) || 0), 0);
    const totalDues = data.reduce((sum, d) => sum + (Number(d.total_due) || 0), 0);

    const columns = [
        {
            id: 'doctor_name',
            header: t('finance.compensation.doctor_name', 'الطبيب'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">{row.doctor_name}</span>
                    <span className="text-[11px] text-text-secondary">
                        {row.treatments} {t('appointments.treatments_count', 'إجراء')} • {row.commission_percent}% {t('finance.compensation.commission_short', 'عمولة')}
                    </span>
                </div>
            ),
        },
        {
            id: 'revenue',
            header: t('finance.metrics.invoiced', 'الإنتاجية'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.revenue} size="sm" />
            ),
        },
        {
            id: 'collected',
            header: t('finance.metrics.collected', 'المحصل'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.collected} size="sm" colored />
            ),
        },
        {
            id: 'lab_cost',
            header: t('finance.expenses.lab_total', 'تكلفة المعمل'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.lab_cost} size="sm" colored />
            ),
        },
        {
            id: 'total_due',
            header: t('finance.compensation.total_due', 'مستحقات الطبيب'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.total_due} size="sm" colored />
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Top KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <MetricCard
                    title={t('finance.compensation.total_production', 'إجمالي إنتاجية الأطباء')}
                    amount={totalProduction}
                    scope="period"
                    subtitle={`${data.length} ${t('finance.compensation.doctors', 'طبيب مسجل')}`}
                    icon={TrendingUp}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.compensation.total_collected', 'المحصل منسوباً للأطباء')}
                    amount={totalCollected}
                    scope="period"
                    subtitle={t('finance.compensation.collected_sub', 'المبالغ المحصلة من حالات الأطباء')}
                    icon={DollarSign}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.expenses.lab_total', 'إجمالي تكاليف المعامل')}
                    amount={totalLabCosts}
                    scope="period"
                    subtitle={t('finance.reports.doctor_labs_sub', 'تكاليف المعامل المخصومة من الأطباء')}
                    icon={FlaskConical}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.obligations.doctor_dues', 'مجموع مستحقات الأطباء')}
                    amount={totalDues}
                    scope="period"
                    subtitle={t('finance.compensation.dues_sub', 'العمولات والرواتب المستحقة للفترة')}
                    icon={UserCheck}
                    colored
                    isLoading={isLoading}
                />
            </div>

            {/* Provider Breakdown Table */}
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                    <div>
                        <h3 className="text-sm font-bold text-text-primary">
                            {t('finance.reports.provider_performance_title', 'تقرير الأداء المالي للأطباء')}
                        </h3>
                        <p className="text-xs text-text-secondary">
                            {t('finance.reports.provider_performance_sub', 'الإنتاجية، المبالغ المحصلة، الخصومات المعملية، وصافي العمولات')}
                        </p>
                    </div>
                    <ScopeBadge scope="period" />
                </div>

                <DataTable
                    columns={columns}
                    data={data}
                    keyField="doctor_id"
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={onRetry}
                    emptyMessage={t('finance.compensation.no_doctors', 'لا توجد بيانات أطباء في هذه الفترة')}
                />
            </div>
        </div>
    );
}
