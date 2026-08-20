import { useTranslation } from 'react-i18next';
import {
    TrendingUp,
    DollarSign,
    Receipt,
    Scale,
} from 'lucide-react';
import MetricCard from '../../components/MetricCard';
import DataTable from '../../components/DataTable';
import Money from '../../components/Money';
import ScopeBadge from '../../components/ScopeBadge';

/**
 * Executive Financial Summary Report (§18 MASTER_SPEC, `FIN-RPT-002`).
 */
export default function FinancialSummaryReportView({ data, isLoading, isError, onRetry }) {
    const { t } = useTranslation();

    const invoiced = Number(data.invoiced_revenue || 0);
    const discounts = Number(data.total_discounts || 0);
    const netInvoiced = Number(data.net_production || (invoiced - discounts));
    const collected = Number(data.collected_revenue || 0);

    const manualExpenses = Number(data.manual_expenses || 0);
    const labCosts = Number(data.lab_costs || 0);
    const doctorDues = Number(data.doctor_dues || 0);
    const staffDues = Number(data.staff_dues || 0);

    const totalDeductions = Number(data.total_deductions || (manualExpenses + labCosts + doctorDues + staffDues));
    const netProfit = Number(data.net_profit || (collected - totalDeductions));
    const marginPercent = collected > 0 ? ((netProfit / collected) * 100).toFixed(1) : '0.0';

    const breakdownItems = [
        {
            id: 'invoiced',
            category: t('finance.metrics.gross_production', 'إجمالي قيمة الخدمات العلاجية (Gross Production)'),
            type: 'inflow',
            amount: invoiced,
            note: t('finance.reports.gross_sub', 'القيمة الإجمالية قبل الخصومات'),
        },
        {
            id: 'discounts',
            category: t('finance.metrics.discount', 'خصومات المرضى والتخفيضات'),
            type: 'discount',
            amount: discounts,
            note: t('finance.reports.discounts_sub', 'مجموع الخصومات الممنوحة على الخدمات'),
        },
        {
            id: 'net_invoiced',
            category: t('finance.metrics.net_invoiced', 'صافي الإنتاجية المحتسبة (Net Production)'),
            type: 'inflow',
            amount: netInvoiced,
            note: t('finance.reports.net_invoiced_sub', 'القيمة الصافية المستحقة بعد الخصم'),
        },
        {
            id: 'collected',
            category: t('finance.metrics.collected', 'إجمالي الإيراد النقدي المحصل (Cash Collections)'),
            type: 'collected',
            amount: collected,
            note: t('finance.reports.collected_sub', 'المبالغ النقدية المقبوضة فعلياً في العيادة'),
        },
        {
            id: 'manual_expenses',
            category: t('finance.expenses.direct_total', 'المصروفات التشغيلية المباشرة'),
            type: 'deduction',
            amount: manualExpenses,
            note: t('finance.reports.expenses_sub', 'إيجار، فواتير، مستلزمات، صيانة'),
        },
        {
            id: 'lab_costs',
            category: t('finance.expenses.lab_total', 'تكاليف المعامل وتركيبات الأسنان'),
            type: 'deduction',
            amount: labCosts,
            note: t('finance.reports.labs_sub', 'مطالبات وتكاليف معامل الأسنان للفترة'),
        },
        {
            id: 'doctor_dues',
            category: t('finance.obligations.doctor_dues', 'مستحقات وعمولات الأطباء'),
            type: 'deduction',
            amount: doctorDues,
            note: t('finance.reports.doctor_dues_sub', 'نسب الأطباء ورواتبهم المعتمدة'),
        },
        {
            id: 'staff_dues',
            category: t('finance.obligations.staff_dues', 'رواتب الموظفين والتمريض'),
            type: 'deduction',
            amount: staffDues,
            note: t('finance.reports.staff_dues_sub', 'رواتب طاقم الاستقبال والمساعدين'),
        },
        {
            id: 'total_deductions',
            category: t('finance.metrics.total_deductions', 'إجمالي الالتزامات والخصومات التشغيلية'),
            type: 'total_deductions',
            amount: totalDeductions,
            note: t('finance.reports.total_deductions_sub', 'مجموع (المصروفات + المعامل + الأطباء + الموظفين)'),
        },
        {
            id: 'net_profit',
            category: t('finance.metrics.net_profit', 'صافي الدخل التشغيلي للعيادة (Net Operating Profit)'),
            type: 'net_profit',
            amount: netProfit,
            note: `${t('finance.reports.margin_label', 'هامش الربح التشغيلي')}: ${marginPercent}%`,
        },
    ];

    const columns = [
        {
            id: 'category',
            header: t('finance.reports.statement_item', 'بند البيان المالي'),
            sortable: false,
            cell: (row) => (
                <div className="space-y-0.5">
                    <span className={`block text-xs sm:text-sm ${
                        row.type === 'net_profit'
                            ? 'font-black text-emerald-600 dark:text-emerald-400 text-sm'
                            : row.type === 'total_deductions'
                            ? 'font-black text-text-primary text-sm'
                            : 'font-bold text-text-primary'
                    }`}>
                        {row.category}
                    </span>
                    <span className="text-[11px] text-text-secondary block">{row.note}</span>
                </div>
            ),
        },
        {
            id: 'amount',
            header: t('finance.activity.movement', 'المبلغ'),
            align: 'end',
            sortable: false,
            width: '180px',
            cell: (row) => (
                <Money
                    amount={row.amount}
                    size={row.type === 'net_profit' ? 'lg' : 'sm'}
                    colored={row.type === 'net_profit' || row.type === 'collected'}
                />
            ),
        },
    ];

    return (
        <div className="space-y-6">
            {/* Top KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <MetricCard
                    title={t('finance.metrics.net_invoiced', 'صافي الإنتاجية')}
                    amount={netInvoiced}
                    scope="period"
                    subtitle={t('finance.reports.invoiced_kpi_sub', 'قيمة الخدمات بعد الخصم')}
                    icon={TrendingUp}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.metrics.collected', 'المحصل النقدي')}
                    amount={collected}
                    scope="period"
                    subtitle={t('finance.reports.collected_kpi_sub', 'التدفقات النقدية الداخلة')}
                    icon={DollarSign}
                    colored
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.metrics.total_deductions', 'إجمالي الاستقطاعات')}
                    amount={totalDeductions}
                    scope="period"
                    subtitle={t('finance.reports.deductions_kpi_sub', 'مصروفات، معامل، أجور')}
                    icon={Receipt}
                    isLoading={isLoading}
                />

                <MetricCard
                    title={t('finance.metrics.net_profit', 'صافي الربح')}
                    amount={netProfit}
                    scope="period"
                    subtitle={`${t('finance.reports.margin_label', 'هامش الربح')}: ${marginPercent}%`}
                    icon={Scale}
                    colored
                    isLoading={isLoading}
                />
            </div>

            {/* Detailed Statement Table */}
            <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                    <div>
                        <h3 className="text-sm font-bold text-text-primary">
                            {t('finance.reports.statement_title', 'قائمة الدخل والتدفقات المالية المعتمدة')}
                        </h3>
                        <p className="text-xs text-text-secondary">
                            {t('finance.reports.statement_sub', 'مطابقة كاملة بين الإنتاجية، التحصيلات، والاستقطاعات التشغيلية')}
                        </p>
                    </div>
                    <ScopeBadge scope="period" />
                </div>

                <DataTable
                    columns={columns}
                    data={breakdownItems}
                    keyField="id"
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={onRetry}
                />
            </div>
        </div>
    );
}
