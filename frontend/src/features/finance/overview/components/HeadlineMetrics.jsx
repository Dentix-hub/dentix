import { useTranslation } from 'react-i18next';
import {
    FileSpreadsheet,
    CreditCard,
    Receipt,
    PiggyBank,
} from 'lucide-react';
import MetricCard from '../../components/MetricCard';

/**
 * Headline Metrics Grid for Finance Overview V2.
 * Displays 4 primary KPIs: Net Invoiced, Cash Collected, Total Deductions, Net Operational Result.
 * The overview date range is already visible in the page-level picker, so period badges are intentionally omitted here.
 */
export default function HeadlineMetrics({
    netInvoiced = 0,
    collected = 0,
    totalDeductions = 0,
    netResult = 0,
    isLoading = false,
    currency = 'EGP',
}) {
    const { t } = useTranslation();

    return (
        <section aria-label={t('finance.overview.headline_metrics', 'المؤشرات المالية الرئيسية')}>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* 1. Net Invoiced Revenue */}
                <MetricCard
                    title={t('finance.metrics.net_revenue', 'صافي الإيراد المحتسب')}
                    amount={netInvoiced}
                    currency={currency}
                    subtitle={t('finance.metrics.net_revenue_sub', 'إجمالي قيمة الجلسات بعد الخصم')}
                    icon={FileSpreadsheet}
                    to="/finance/reports"
                    isLoading={isLoading}
                />

                {/* 2. Cash Collected */}
                <MetricCard
                    title={t('finance.metrics.collected', 'التحصيلات النقدية')}
                    amount={collected}
                    currency={currency}
                    subtitle={t('finance.metrics.collected_sub', 'النقد المقبوض فعلياً من المرضى')}
                    icon={CreditCard}
                    to="/finance/payments"
                    colored
                    isLoading={isLoading}
                />

                {/* 3. Total Deductions */}
                <MetricCard
                    title={t('finance.metrics.total_deductions', 'إجمالي الاستقطاعات')}
                    amount={totalDeductions}
                    currency={currency}
                    subtitle={t('finance.metrics.total_deductions_sub', 'أطباء + موظفين + تشغيل + معامل')}
                    icon={Receipt}
                    to="/finance/expenses"
                    isLoading={isLoading}
                />

                {/* 4. Net Operational Result */}
                <MetricCard
                    title={t('finance.metrics.net_result', 'صافي النتيجة التشغيلية')}
                    amount={netResult}
                    currency={currency}
                    subtitle={t('finance.metrics.net_result_sub', 'التحصيل مطروحاً منه الاستقطاعات')}
                    icon={PiggyBank}
                    to="/finance/reports"
                    colored
                    isLoading={isLoading}
                />
            </div>
        </section>
    );
}
