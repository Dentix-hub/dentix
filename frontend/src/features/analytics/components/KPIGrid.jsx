import { useTranslation } from 'react-i18next';
import { TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';

const StatCard = ({ title, value, subtext, trend, color, icon: Icon }) => (
    <div className="bg-surface p-6 rounded-2xl border border-border/50 shadow-sm relative overflow-hidden group hover:shadow-md transition-all">
        <div className={`absolute -right-4 -top-4 p-4 opacity-5 group-hover:opacity-10 transition-opacity transform rotate-12 ${color}`}>
            <Icon size={100} />
        </div>
        <div className="relative z-10">
            <div className="flex justify-between items-start mb-4">
                <div className={`p-2 rounded-lg bg-surface-hover ${color}`}>
                    <Icon size={20} />
                </div>
            </div>
            <h3 className="text-2xl font-bold text-text-primary tracking-tight mb-1">{value}</h3>
            <p className="text-text-secondary text-sm font-medium mb-1">{title}</p>
            {subtext && <p className="text-xs text-text-tertiary mt-2">{subtext}</p>}
        </div>
    </div>
);

const KPIGrid = ({ data }) => {
    if (!data) return <div className="animate-pulse h-32 bg-surface rounded-2xl"></div>;

    const totalCOGS = (data.breakdown?.material_costs || 0) + (data.breakdown?.lab_costs || 0);

    const { t } = useTranslation();

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
                title={t('analytics.kpi.revenue.title')}
                value={`$${data.revenue.toLocaleString()}`}
                subtext={t('analytics.kpi.revenue.desc')}
                icon={TrendingUp}
                color="text-emerald-500"
            />
            <StatCard
                title={t('analytics.kpi.profit.title')}
                value={`$${data.net_profit.toLocaleString()}`}
                subtext={`${t('analytics.kpi.profit.desc')} ${data.margin_percent}%`}
                icon={DollarSign}
                color="text-blue-600"
            />
            <StatCard
                title={t('analytics.kpi.opex.title')}
                value={`$${(data.breakdown?.expenses || 0).toLocaleString()}`}
                subtext={t('analytics.kpi.opex.desc')}
                icon={Activity}
                color="text-orange-500"
            />
            <StatCard
                title={t('analytics.kpi.cogs.title')}
                value={`$${(totalCOGS || 0).toLocaleString()}`}
                subtext={t('analytics.kpi.cogs.desc')}
                icon={TrendingDown}
                color="text-rose-500"
            />
        </div>
    );
};

export default KPIGrid;