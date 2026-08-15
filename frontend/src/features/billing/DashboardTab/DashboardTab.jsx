import { useMemo } from 'react';
import { Calendar } from 'lucide-react';
import { SkeletonBox, Card, DateTimePicker } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import useBillingDashboard from '@/hooks/useBillingDashboard';
import FinancialOverviewCards from './FinancialOverviewCards';
import CollectionProgressBar from './CollectionProgressBar';
import DeductionsBreakdown from './DeductionsBreakdown';
import NetProfitBanner from './NetProfitBanner';

export default function DashboardTab() {
    const { t } = useTranslation();
    const {
        startDate,
        setStartDate,
        endDate,
        setEndDate,
        comprehensiveStats,
        isLoading
    } = useBillingDashboard();

    const periodLabel = useMemo(() => {
        if (!startDate || !endDate) return '';
        const formatDate = (date) => new Intl.DateTimeFormat('ar-EG', {
            day: 'numeric', month: 'short', year: 'numeric'
        }).format(new Date(`${date}T12:00:00`));
        return `${formatDate(startDate)} — ${formatDate(endDate)}`;
    }, [startDate, endDate]);

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-EG', { style: 'currency', currency: 'EGP', maximumFractionDigits: 0 }).format(amount || 0);
    };

    if (isLoading) {
        return (
            <div className="space-y-6">
                <SkeletonBox className="h-28 w-full rounded-2xl" />
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => <SkeletonBox key={i} className="h-28 rounded-2xl" />)}
                </div>
                <SkeletonBox className="h-64 w-full rounded-2xl" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Filter Panel: Date Range */}
            <Card className="p-6 border-primary/15 bg-gradient-to-br from-primary/5 via-surface to-surface">
                <div className="flex flex-col gap-1 mb-6">
                    <div className="flex items-center gap-2 text-primary font-black">
                        <Calendar size={19} />
                        <h3>{t('billing.summary.period', 'Time Period')}</h3>
                    </div>
                    <p className="text-sm text-text-secondary">
                        {t('billing.summary.period_scope_hint', 'All figures, patient totals, and details below are limited to the selected period.')}
                    </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl">
                    <DateTimePicker
                        label={t('billing.summary.from')}
                        mode="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                    />
                    <DateTimePicker
                        label={t('billing.summary.to')}
                        mode="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                    />
                </div>
                <div className="mt-5 inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-primary/10 text-primary text-sm font-bold">
                    <Calendar size={15} />
                    {periodLabel}
                </div>
            </Card>

            {/* Header Cards - Income */}
            <FinancialOverviewCards
                comprehensiveStats={comprehensiveStats}
                formatCurrency={formatCurrency}
            />

            {/* Collection Progress */}
            <CollectionProgressBar
                comprehensiveStats={comprehensiveStats}
                formatCurrency={formatCurrency}
            />

            {/* Deductions Breakdown */}
            <DeductionsBreakdown
                comprehensiveStats={comprehensiveStats}
                formatCurrency={formatCurrency}
            />

            {/* Net Profit Banner */}
            <NetProfitBanner
                comprehensiveStats={comprehensiveStats}
                formatCurrency={formatCurrency}
            />
        </div>
    );
}
