import { useTranslation } from 'react-i18next';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { useFinanceOverview } from '../overview/hooks/useFinanceOverview';
import HeadlineMetrics from '../overview/components/HeadlineMetrics';
import ObligationsSection from '../overview/components/ObligationsSection';
import FinancialTrendChart from '../overview/components/FinancialTrendChart';
import RecentActivityPreview from '../overview/components/RecentActivityPreview';

/**
 * Finance Overview V2 Page.
 * Implements §10 of MASTER_SPEC:
 * - 4 Headline KPIs (Net Invoiced, Collected, Total Deductions, Net Operational Result)
 * - Obligations & Receivables section (Patient Debt, Doctor Dues, Staff Payroll)
 * - Primary Trend Chart (Collections vs Expenses over time)
 * - Recent Financial Activity preview feed
 */
export default function OverviewPage() {
    const { t } = useTranslation();

    const {
        netInvoiced,
        collected,
        totalDeductions,
        netResult,
        allTimeOutstanding,
        doctorDuesTotal,
        staffDuesTotal,
        timeline,
        recentActivity,
        isLoading,
        isError,
        refetch,
    } = useFinanceOverview();

    if (isError) {
        return (
            <div className="p-8 rounded-2xl border border-rose-200 dark:border-rose-900/50 bg-card text-center space-y-4 shadow-sm">
                <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 mx-auto flex items-center justify-center">
                    <AlertCircle className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                    <h3 className="text-base font-bold text-text-primary">
                        {t('common.error_loading_data', 'حدث خطأ أثناء تحميل المؤشرات المالية')}
                    </h3>
                    <p className="text-xs text-text-secondary">
                        {t('common.try_again_later', 'يرجى المحاولة مرة أخرى أو التحقق من الاتصال بالخادم')}
                    </p>
                </div>
                <button
                    type="button"
                    onClick={refetch}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors shadow-sm"
                >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>{t('common.retry', 'إعادة المحاولة')}</span>
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* 1. Headline Metrics (4 Core KPIs) */}
            <HeadlineMetrics
                netInvoiced={netInvoiced}
                collected={collected}
                totalDeductions={totalDeductions}
                netResult={netResult}
                isLoading={isLoading}
            />

            {/* 2. Actionable Obligations & Receivables */}
            <ObligationsSection
                allTimeOutstanding={allTimeOutstanding}
                doctorDuesTotal={doctorDuesTotal}
                staffDuesTotal={staffDuesTotal}
                isLoading={isLoading}
            />

            {/* 3. Financial Trends & Recent Activity Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                    <FinancialTrendChart
                        timeline={timeline}
                        isLoading={isLoading}
                    />
                </div>
                <div className="lg:col-span-1">
                    <RecentActivityPreview
                        activities={recentActivity}
                        isLoading={isLoading}
                    />
                </div>
            </div>
        </div>
    );
}
