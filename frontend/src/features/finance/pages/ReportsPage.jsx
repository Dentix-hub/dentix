import { useTranslation } from 'react-i18next';
import {
    FileSpreadsheet,
    TrendingUp,
    DollarSign,
    Receipt,
    UserCheck,
    Download,
    Calendar,
    Sparkles,
} from 'lucide-react';
import { useReports } from '../reports/hooks/useReports';
import DateRangePicker from '../components/DateRangePicker';
import FinancialSummaryReportView from '../reports/components/FinancialSummaryReportView';
import CollectionsReportView from '../reports/components/CollectionsReportView';
import ExpenseCategoryReportView from '../reports/components/ExpenseCategoryReportView';
import ProviderReportView from '../reports/components/ProviderReportView';
import ProcedureProfitabilityReportView from '../reports/components/ProcedureProfitabilityReportView';

/**
 * Finance V2 Reports Workspace (§18 MASTER_SPEC, `PHASE_09_REPORTS.md`).
 * Executive reporting workspace covering Financial Summary, Collections, Expenses, Providers, and Profitability.
 */
export default function ReportsPage() {
    const { t } = useTranslation();

    const {
        reportType,
        from,
        to,
        search,
        summaryData,
        collectionsData,
        expensesData,
        providersData,
        profitabilityData,
        isLoading,
        isError,
        refetch,
        setReportType,
        updateDateRange,
        updateSearch,
        exportToCsv,
    } = useReports();

    const reportTabs = [
        { id: 'summary', label: t('finance.reports.tab_summary', 'الملخص المالي العام'), icon: TrendingUp },
        { id: 'collections', label: t('finance.reports.tab_collections', 'التحصيلات والذمم'), icon: DollarSign },
        { id: 'expenses', label: t('finance.reports.tab_expenses', 'المصروفات حسب البند'), icon: Receipt },
        { id: 'providers', label: t('finance.reports.tab_providers', 'أداء الأطباء'), icon: UserCheck },
        { id: 'profitability', label: t('finance.reports.tab_profitability', 'ربحية الإجراءات'), icon: FileSpreadsheet },
    ];

    // Handle CSV Export
    const handleExport = () => {
        if (reportType === 'summary') {
            const headers = ['البند', 'المبلغ (ج.م)'];
            const rows = [
                ['إجمالي الإنتاجية', summaryData.invoiced_revenue || 0],
                ['إجمالي الخصومات', summaryData.total_discounts || 0],
                ['صافي الإنتاجية', summaryData.net_production || 0],
                ['المحصل النقدي', summaryData.collected_revenue || 0],
                ['المصروفات التشغيلية', summaryData.manual_expenses || 0],
                ['تكاليف المعامل', summaryData.lab_costs || 0],
                ['مستحقات الأطباء', summaryData.doctor_dues || 0],
                ['رواتب الموظفين', summaryData.staff_dues || 0],
                ['إجمالي الاستقطاعات', summaryData.total_deductions || 0],
                ['صافي الربح التشغيلي', summaryData.net_profit || 0],
            ];
            exportToCsv('Financial_Summary', headers, rows);
        } else if (reportType === 'collections') {
            const headers = ['المريض', 'رقم الهاتف', 'المحتسب للفترة', 'المحصل للفترة', 'فارق الفترة', 'إجمالي الدين المتراكم'];
            const rows = (collectionsData.patients || []).map((p) => [
                p.patient_name,
                p.patient_phone || '',
                p.invoiced_in_period || 0,
                p.paid_in_period || 0,
                p.period_balance || 0,
                p.all_time_outstanding || 0,
            ]);
            exportToCsv('Collections_Report', headers, rows);
        } else if (reportType === 'expenses') {
            const headers = ['بند المصروف', 'المبلغ', 'التاريخ', 'البيان'];
            const rows = expensesData.map((e) => [
                e.category || 'عام',
                e.amount || 0,
                e.date || '',
                e.description || '',
            ]);
            exportToCsv('Expenses_Report', headers, rows);
        } else if (reportType === 'providers') {
            const headers = ['الطبيب', 'عدد الحالات', 'الإنتاجية', 'المحصل', 'تكلفة المعمل', 'نسبة العمولة %', 'الراتب الثابت', 'المستحق النهائي'];
            const rows = providersData.map((d) => [
                d.doctor_name,
                d.treatments || 0,
                d.revenue || 0,
                d.collected || 0,
                d.lab_cost || 0,
                d.commission_percent || 0,
                d.fixed_salary || 0,
                d.total_due || 0,
            ]);
            exportToCsv('Providers_Report', headers, rows);
        } else if (reportType === 'profitability') {
            const headers = ['الإجراء الطبي', 'سعر الخدمة', 'تكلفة المواد', 'هامش الربح', 'نسبة الهامش %'];
            const rows = profitabilityData.map((p) => [
                p.name || p.procedure_name,
                p.price || p.base_price || 0,
                p.material_cost || p.cost || 0,
                p.profit_margin || 0,
                p.margin_percent || p.profit_margin_percent || 0,
            ]);
            exportToCsv('Procedure_Profitability_Report', headers, rows);
        }
    };

    return (
        <div className="space-y-6">
            {/* Top Report Header Controls */}
            <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
                {/* Report Tabs */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
                    {reportTabs.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = reportType === tab.id;
                        return (
                            <button
                                key={tab.id}
                                type="button"
                                onClick={() => setReportType(tab.id)}
                                className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold whitespace-nowrap transition-all ${
                                    isActive
                                        ? 'bg-primary text-white shadow-sm'
                                        : 'bg-card border border-border text-text-secondary hover:text-text-primary hover:bg-muted/60'
                                }`}
                            >
                                <Icon className="w-4 h-4" />
                                <span>{tab.label}</span>
                            </button>
                        );
                    })}
                </div>

                {/* Date Picker & Export Action */}
                <div className="flex items-center gap-2">
                    {reportType !== 'profitability' && (
                        <DateRangePicker
                            value={{ from, to }}
                            onChange={updateDateRange}
                        />
                    )}

                    <button
                        type="button"
                        onClick={handleExport}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold bg-card border border-border text-text-primary hover:bg-muted/60 transition-colors shadow-xs"
                        title={t('common.export_csv', 'تصدير كملف CSV')}
                    >
                        <Download className="w-4 h-4 text-primary" />
                        <span className="hidden sm:inline">{t('common.export', 'تصدير')}</span>
                    </button>
                </div>
            </div>

            {/* Active Report View Rendering */}
            {reportType === 'summary' && (
                <FinancialSummaryReportView
                    data={summaryData}
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={refetch}
                />
            )}

            {reportType === 'collections' && (
                <CollectionsReportView
                    data={collectionsData}
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={refetch}
                />
            )}

            {reportType === 'expenses' && (
                <ExpenseCategoryReportView
                    data={expensesData}
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={refetch}
                />
            )}

            {reportType === 'providers' && (
                <ProviderReportView
                    data={providersData}
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={refetch}
                />
            )}

            {reportType === 'profitability' && (
                <ProcedureProfitabilityReportView
                    data={profitabilityData}
                    isLoading={isLoading}
                    isError={isError}
                    onRetry={refetch}
                />
            )}
        </div>
    );
}
