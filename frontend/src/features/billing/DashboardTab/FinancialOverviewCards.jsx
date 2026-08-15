import { TrendingUp, Banknote, DollarSign, UsersRound } from 'lucide-react';
import { StatCard } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

export default function FinancialOverviewCards({ comprehensiveStats, formatCurrency }) {
    const { t } = useTranslation();

    const totalRevenue = comprehensiveStats?.income?.total_revenue || 0;
    const totalCollected = comprehensiveStats?.income?.total_collected || 0;
    const periodBalance = comprehensiveStats?.income?.period_balance ?? totalRevenue - totalCollected;
    const collectionRate = totalRevenue > 0 ? Math.min(100, Math.round((totalCollected / totalRevenue) * 100)) : 0;

    return (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard
                title={t('billing.summary.total_revenue')}
                value={formatCurrency(totalRevenue)}
                subtext={t('billing.summary.in_selected_period', 'In selected period')}
                icon={TrendingUp}
                color="success"
            />
            <StatCard
                title={t('billing.summary.total_collected')}
                value={formatCurrency(totalCollected)}
                subtext={`${t('billing.summary.collection_rate', 'Collection rate')}: ${collectionRate}%`}
                icon={Banknote}
                color="info"
            />
            <StatCard
                title={t('billing.summary.period_balance', 'Period Balance')}
                value={formatCurrency(periodBalance)}
                subtext={`${t('billing.summary.all_time_outstanding', 'All-time outstanding')}: ${formatCurrency(comprehensiveStats?.income?.all_time_outstanding ?? comprehensiveStats?.income?.outstanding ?? 0)}`}
                icon={DollarSign}
                color="warning"
            />
            <StatCard
                title={t('billing.summary.patient_count')}
                value={comprehensiveStats?.income?.unique_patients || 0}
                subtext={`${comprehensiveStats?.income?.total_appointments || 0} ${t('billing.summary.treatments', 'treatments')}`}
                icon={UsersRound}
                color="primary"
            />
        </div>
    );
}
