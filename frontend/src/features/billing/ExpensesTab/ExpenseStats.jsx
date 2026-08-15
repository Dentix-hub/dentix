import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { StatCard } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

export default function ExpenseStats({ stats }) {
    const { t } = useTranslation();

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatCard
                title={t('billing.stats.total_income')}
                value={`${(stats?.total_received || 0).toLocaleString()}`}
                icon={TrendingUp}
                trend="up"
                color="success"
            />
            <StatCard
                title={t('billing.stats.total_expenses')}
                value={`${(stats?.total_expenses || 0).toLocaleString()}`}
                icon={TrendingDown}
                trend="down"
                color="danger"
            />
            <StatCard
                title={t('billing.stats.net_profit')}
                value={`${(stats?.net_profit || 0).toLocaleString()}`}
                icon={DollarSign}
                color={(stats?.net_profit || 0) >= 0 ? "primary" : "danger"}
            />
        </div>
    );
}
