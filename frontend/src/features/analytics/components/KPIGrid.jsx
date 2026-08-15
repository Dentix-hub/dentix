import { useTranslation } from 'react-i18next';
import { TrendingUp, TrendingDown, DollarSign, Activity, HelpCircle, Clock } from 'lucide-react';
import Tooltip from '@/shared/ui/Tooltip';

// Helper Sparkline SVG component
const MiniSparkline = ({ color = '#0ea5e9', positive = true }) => {
    const points = positive
        ? "0,25 15,20 30,22 45,14 60,16 75,8 90,10 100,2"
        : "0,5 15,10 30,8 45,18 60,14 75,22 90,20 100,28";
    return (
        <svg className="w-full h-8 opacity-40 group-hover:opacity-70 transition-opacity" viewBox="0 0 100 30" preserveAspectRatio="none">
            <polyline
                fill="none"
                stroke={color}
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
            />
        </svg>
    );
};

const StatCard = ({ title, value, subtext, delta, tooltipText, color, strokeColor, icon: Icon, positiveTrend = true }) => {
    return (
        <div className="bg-surface p-5 rounded-3xl border border-border/50 shadow-sm relative overflow-hidden group hover:border-primary/40 hover:shadow-md transition-all">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-text-secondary">
                    <span>{title}</span>
                    {tooltipText && (
                        <Tooltip content={tooltipText} side="top">
                            <HelpCircle size={13} className="text-text-tertiary hover:text-primary cursor-pointer transition-colors" />
                        </Tooltip>
                    )}
                </div>
                {delta !== null && delta !== undefined && (
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-black border flex items-center gap-1 ${
                        Number(delta) >= 0
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
                    }`}>
                        {Number(delta) >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                        {Number(delta) >= 0 ? `+${delta}%` : `${delta}%`}
                    </span>
                )}
            </div>

            <div className="text-2xl font-black text-text-primary tracking-tight mb-1 font-mono">
                {value}
            </div>

            {subtext && (
                <div className="text-[11px] text-text-tertiary font-medium">
                    {subtext}
                </div>
            )}

            <div className="mt-2">
                <MiniSparkline color={strokeColor || '#0ea5e9'} positive={positiveTrend} />
            </div>
        </div>
    );
};

const KPIGrid = ({ data }) => {
    const { t } = useTranslation();

    if (!data) return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-36 bg-surface rounded-3xl"></div>)}
        </div>
    );

    const totalCOGS = (data.breakdown?.material_costs || 0) + (data.breakdown?.lab_costs || 0);
    const prevCOGS = data.previous_period
        ? (data.previous_period.material_costs || 0) + (data.previous_period.lab_costs || 0)
        : null;

    // Calc Deltas
    const calcDelta = (curr, prev) => {
        if (!prev || prev === 0) return null;
        return (((curr - prev) / prev) * 100).toFixed(1);
    };

    const revDelta = calcDelta(data.revenue, data.previous_period?.revenue);
    const profitDelta = calcDelta(data.net_profit, data.previous_period?.net_profit);
    const opexDelta = calcDelta(data.breakdown?.expenses, data.previous_period?.expenses);
    const cogsDelta = calcDelta(totalCOGS, prevCOGS);

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
                title={t('analytics.kpi.revenue.title')}
                value={`$${(data.revenue || 0).toLocaleString()}`}
                subtext={t('analytics.kpi.revenue.desc')}
                tooltipText={t('analytics.kpi.revenue.tooltip')}
                delta={revDelta}
                icon={TrendingUp}
                color="text-emerald-500"
                strokeColor="#10b981"
                positiveTrend={!revDelta || Number(revDelta) >= 0}
            />
            <StatCard
                title={t('analytics.kpi.profit.title')}
                value={`$${(data.net_profit || 0).toLocaleString()}`}
                subtext={`${t('analytics.kpi.profit.desc')} ${data.margin_percent || 0}%`}
                tooltipText={t('analytics.kpi.profit.tooltip')}
                delta={profitDelta}
                icon={DollarSign}
                color="text-blue-600"
                strokeColor="#3b82f6"
                positiveTrend={!profitDelta || Number(profitDelta) >= 0}
            />
            <StatCard
                title={t('analytics.kpi.opex.title')}
                value={`$${(data.breakdown?.expenses || 0).toLocaleString()}`}
                subtext={t('analytics.kpi.opex.desc')}
                tooltipText={t('analytics.kpi.opex.tooltip')}
                delta={opexDelta}
                icon={Activity}
                color="text-orange-500"
                strokeColor="#f97316"
                positiveTrend={opexDelta && Number(opexDelta) < 0}
            />
            <StatCard
                title={t('analytics.kpi.cogs.title')}
                value={`$${(totalCOGS || 0).toLocaleString()}`}
                subtext={t('analytics.kpi.cogs.desc')}
                tooltipText={t('analytics.kpi.cogs.tooltip')}
                delta={cogsDelta}
                icon={TrendingDown}
                color="text-rose-500"
                strokeColor="#f43f5e"
                positiveTrend={cogsDelta && Number(cogsDelta) < 0}
            />
        </div>
    );
};

export default KPIGrid;
