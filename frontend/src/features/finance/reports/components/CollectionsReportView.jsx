import { useTranslation } from 'react-i18next';
import {
    DollarSign,
    TrendingUp,
    AlertCircle,
    Users,
} from 'lucide-react';
import MetricCard from '../../components/MetricCard';
import DataTable from '../../components/DataTable';
import Money from '../../components/Money';

/**
 * Collections & Receivables Report View (§18 MASTER_SPEC, `FIN-RPT-003`).
 */
export default function CollectionsReportView({ data, isLoading, isError, onRetry }) {
    const { t } = useTranslation();

    const summary = data.summary || {};
    const patients = data.patients || [];

    const totalCollected = Number(summary.total_paid || 0);
    const totalInvoiced = Number(summary.total_invoiced || 0);
    const periodBalance = Number(summary.period_balance || (totalInvoiced - totalCollected));
    const allTimeDebt = Number(summary.total_outstanding || 0);

    const columns = [
        {
            id: 'patient_name',
            header: t('patients.patient_name', 'المريض'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className="font-bold text-text-primary block">{row.patient_name}</span>
                    <span className="text-[11px] text-text-secondary font-mono">
                        {row.patient_phone || '—'}
                    </span>
                </div>
            ),
        },
        {
            id: 'invoiced',
            header: t('finance.metrics.invoiced', 'المحتسب للفترة'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.invoiced_in_period} size="sm" />
            ),
        },
        {
            id: 'paid',
            header: t('finance.metrics.collected', 'المحصل للفترة'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.paid_in_period} size="sm" colored />
            ),
        },
        {
            id: 'period_balance',
            header: t('finance.metrics.period_balance', 'فارق الفترة'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.period_balance} size="sm" colored />
            ),
        },
        {
            id: 'all_time_outstanding',
            header: t('finance.metrics.all_time_debt', 'إجمالي الدين المتراكم'),
            align: 'end',
            sortable: false,
            cell: (row) => (
                <Money amount={row.all_time_outstanding} size="sm" colored />
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Top KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <MetricCard
                    title={t('finance.metrics.collected', 'المحصل للفترة')}
                    amount={totalCollected}
                    scope="period"
                    subtitle={t('finance.reports.collected_desc', 'إجمالي المقبوضات النقدية')}
                    icon={DollarSign}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.metrics.invoiced', 'المحتسب للفترة')}
                    amount={totalInvoiced}
                    scope="period"
                    subtitle={t('finance.reports.invoiced_desc', 'إجمالي الإنتاجية العلاجية')}
                    icon={TrendingUp}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.metrics.period_balance', 'فارق الفترة')}
                    amount={periodBalance}
                    scope="period"
                    subtitle={t('finance.reports.period_balance_sub', 'صافي تغير المديونية خلال الفترة')}
                    icon={AlertCircle}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.obligations.all_time_debt', 'إجمالي الديون المتراكمة')}
                    amount={allTimeDebt}
                    scope="all_time"
                    subtitle={t('finance.reports.all_time_sub', 'رصيد الذمم المدينة لجميع المرضى')}
                    icon={Users}
                    colored
                    isLoading={isLoading}
                />
            </div>

            {/* Patients Collections Table */}
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                    <div>
                        <h3 className="text-sm font-bold text-text-primary">
                            {t('finance.reports.collections_table_title', 'تقرير تحصيلات وحسابات المرضى')}
                        </h3>
                        <p className="text-xs text-text-secondary">
                            {t('finance.reports.collections_table_sub', 'كشف مفصل بالإنتاجية، المبالغ المحصلة، والديون المتراكمة')}
                        </p>
                    </div>
                </div>

                <DataTable
                    columns={columns}
                    data={patients}
                    keyField="patient_id"
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={onRetry}
                    emptyMessage={t('finance.reports.no_patients_data', 'لا توجد بيانات مرضى في هذه الفترة')}
                />
            </div>
        </div>
    );
}
