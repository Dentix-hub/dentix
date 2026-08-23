import { useTranslation } from 'react-i18next';
import {
    FileSpreadsheet,
    TrendingUp,
    DollarSign,
    Receipt,
    UserCheck,
    Download,
} from 'lucide-react';
import { useReports } from '../reports/hooks/useReports';
import FinancialSummaryReportView from '../reports/components/FinancialSummaryReportView';
import CollectionsReportView from '../reports/components/CollectionsReportView';
import ExpenseCategoryReportView from '../reports/components/ExpenseCategoryReportView';
import ProviderReportView from '../reports/components/ProviderReportView';
import ProcedureProfitabilityReportView from '../reports/components/ProcedureProfitabilityReportView';

/**
 * Finance V2 Reports Workspace.
 * The Finance module header owns the single period control for period reports.
 */
export default function ReportsPage() {
    const { t } = useTranslation();

    const {
        reportType,
        summaryData,
        collectionsData,
        expensesData,
        providersData,
        profitabilityData,
        isLoading,
        isError,
        refetch,
        setReportType,
        exportToCsv,
    } = useReports();

    const reportTabs = [
        { id: 'summary', label: t('finance.reports.tab_summary', 'الملخص المالي العام'), icon: TrendingUp },
        { id: 'collections', label: t('finance.reports.tab_collections', 'التحصيلات والذمم'), icon: DollarSign },
        { id: 'expenses', label: t('finance.reports.tab_expenses', 'المصروفات حسب البند'), icon: Receipt },
        { id: 'providers', label: t('finance.reports.tab_providers', 'أداء الأطباء'), icon: UserCheck },
        { id: 'profitability', label: t('finance.reports.tab_profitability', 'ربحية الإجراءات'), icon: FileSpreadsheet },
    ];

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
            const rows = (collectionsData.patients || []).map((patient) => [
                patient.patient_name,
                patient.patient_phone || '',
                patient.invoiced_in_period || 0,
                patient.paid_in_period || 0,
                patient.period_balance || 0,
                patient.all_time_outstanding || 0,
            ]);
            exportToCsv('Collections_Report', headers, rows);
        } else if (reportType === 'expenses') {
            const headers = ['بند المصروف', 'المبلغ', 'التاريخ', 'البيان'];
            const rows = expensesData.map((expense) => [
                expense.category || 'عام',
                expense.amount || 0,
                expense.date || '',
                expense.notes || '',
            ]);
            exportToCsv('Expenses_Report', headers, rows);
        } else if (reportType === 'providers') {
            const headers = [
                'الطبيب',
                'عدد الحالات',
                'الإنتاجية',
                'المحصل',
                'تكلفة المعمل',
                'نسبة العمولة %',
                'الراتب الثابت الشهري (قاعدة)',
                'حصة الراتب للفترة',
                'المستحق النهائي للفترة',
            ];
            const rows = providersData.map((doctor) => [
                doctor.doctor_name,
                doctor.treatments || 0,
                doctor.revenue || 0,
                doctor.collected || 0,
                doctor.lab_cost || 0,
                doctor.commission_percent || 0,
                doctor.fixed_salary || 0,
                doctor.fixed_salary_period || 0,
                doctor.total_due || 0,
            ]);
            exportToCsv('Providers_Report', headers, rows);
        } else if (reportType === 'profitability') {
            const headers = ['الإجراء الطبي', 'سعر الخدمة', 'تكلفة المواد', 'هامش الربح', 'نسبة الهامش %'];
            const rows = profitabilityData.map((procedure) => [
                procedure.name || procedure.procedure_name,
                procedure.price || procedure.base_price || 0,
                procedure.material_cost || procedure.cost || 0,
                procedure.profit_margin || 0,
                procedure.margin_percent || procedure.profit_margin_percent || 0,
            ]);
            exportToCsv('Procedure_Profitability_Report', headers, rows);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col items-stretch justify-between gap-4 lg:flex-row lg:items-center">
                <div className="flex max-w-full items-center gap-1.5 overflow-x-auto pb-1">
                    {reportTabs.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = reportType === tab.id;
                        return (
                            <button
                                key={tab.id}
                                type="button"
                                onClick={() => setReportType(tab.id)}
                                className={`inline-flex items-center gap-2 whitespace-nowrap rounded-xl px-3.5 py-2 text-xs font-bold transition-all sm:text-sm ${
                                    isActive
                                        ? 'bg-primary text-white shadow-sm'
                                        : 'border border-border bg-card text-text-secondary hover:bg-muted/60 hover:text-text-primary'
                                }`}
                            >
                                <Icon className="h-4 w-4" />
                                <span>{tab.label}</span>
                            </button>
                        );
                    })}
                </div>

                <button
                    type="button"
                    onClick={handleExport}
                    className="inline-flex items-center gap-1.5 self-start rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-bold text-text-primary shadow-xs transition-colors hover:bg-muted/60 sm:text-sm lg:self-auto"
                    title={t('common.export_csv', 'تصدير كملف CSV')}
                >
                    <Download className="h-4 w-4 text-primary" />
                    <span>{t('common.export', 'تصدير')}</span>
                </button>
            </div>

            {reportType === 'summary' && (
                <FinancialSummaryReportView data={summaryData} isLoading={isLoading} isError={isError} onRetry={refetch} />
            )}
            {reportType === 'collections' && (
                <CollectionsReportView data={collectionsData} isLoading={isLoading} isError={isError} onRetry={refetch} />
            )}
            {reportType === 'expenses' && (
                <ExpenseCategoryReportView data={expensesData} isLoading={isLoading} isError={isError} onRetry={refetch} />
            )}
            {reportType === 'providers' && (
                <ProviderReportView data={providersData} isLoading={isLoading} isError={isError} onRetry={refetch} />
            )}
            {reportType === 'profitability' && (
                <ProcedureProfitabilityReportView data={profitabilityData} isLoading={isLoading} isError={isError} onRetry={refetch} />
            )}
        </div>
    );
}
