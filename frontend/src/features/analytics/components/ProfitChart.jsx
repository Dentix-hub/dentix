import { useTranslation } from 'react-i18next';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, LazyChart } from '@/components/charts/LazyChart';

const ProfitChart = ({ data }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    if (!data) return null;

    const revenue = data.revenue || 0;
    const netProfit = data.net_profit || 0;

    // Outer ring: Revenue vs Costs breakdown
    const overviewData = [
        { name: isRtl ? 'صافي الربح' : 'Net Profit', value: Math.max(netProfit, 0) },
        { name: t('analytics.chart.expenses'), value: data.breakdown?.expenses || 0 },
        { name: t('analytics.chart.materials'), value: data.breakdown?.material_costs || 0 },
        { name: t('analytics.chart.labs'), value: data.breakdown?.lab_costs || 0 },
    ].filter(d => d.value > 0);

    // Colors: Profit=emerald, Expenses=orange, Materials=rose, Labs=pink
    const COLORS = ['#10b981', '#F97316', '#F43F5E', '#EC4899'];

    // Custom Tooltip
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const pct = revenue > 0 ? ((payload[0].value / revenue) * 100).toFixed(1) : 0;
            return (
                <div className="bg-slate-900/95 backdrop-blur-md p-3 rounded-xl shadow-2xl border border-slate-700/80 text-xs space-y-1">
                    <p className="font-bold text-white flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: payload[0].payload?.fill }}></span>
                        {payload[0].name}
                    </p>
                    <p className="text-slate-300 font-mono">
                        ${(payload[0].value || 0).toLocaleString()}
                        <span className="text-slate-500 ms-1.5">
                            ({pct}% {isRtl ? 'من الإيراد' : 'of revenue'})
                        </span>
                    </p>
                </div>
            );
        }
        return null;
    };

    // Margin health indicator
    const marginPercent = data.margin_percent || 0;
    const marginColor = marginPercent >= 40 ? 'text-emerald-500' : marginPercent >= 20 ? 'text-amber-500' : 'text-rose-500';
    const marginBg = marginPercent >= 40 ? 'bg-emerald-500/10' : marginPercent >= 20 ? 'bg-amber-500/10' : 'bg-rose-500/10';

    return (
        <div className="bg-surface p-6 rounded-3xl border border-border/50 shadow-sm h-full flex flex-col justify-between">
            <div>
                <h3 className="text-lg font-bold text-text-primary mb-1">{t('analytics.chart.title')}</h3>
                <p className="text-xs text-text-secondary mb-2">{t('analytics.chart.subtitle')}</p>

                {/* Revenue vs Costs summary bar */}
                <div className="flex items-center gap-2 mb-4">
                    <div className="flex-1 h-2.5 rounded-full bg-surface-hover overflow-hidden">
                        {revenue > 0 && (
                            <div
                                className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-700"
                                style={{ width: `${Math.min((netProfit / revenue) * 100, 100)}%` }}
                            ></div>
                        )}
                    </div>
                    <span className={`text-xs font-black px-2 py-0.5 rounded-lg ${marginColor} ${marginBg}`}>
                        {marginPercent}%
                    </span>
                </div>
            </div>

            <div className="h-[250px] relative">
                {overviewData.length > 0 ? (
                    <LazyChart>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={overviewData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={55}
                                    outerRadius={80}
                                    paddingAngle={4}
                                    dataKey="value"
                                    stroke="none"
                                    cornerRadius={4}
                                >
                                    {overviewData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip content={<CustomTooltip />} />
                                <Legend
                                    verticalAlign="bottom"
                                    height={36}
                                    iconType="circle"
                                    wrapperStyle={{ fontSize: '11px', paddingTop: '16px' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </LazyChart>
                ) : (
                    <div className="flex items-center justify-center h-full text-slate-300">
                        {t('analytics.chart.no_data')}
                    </div>
                )}

                {/* Center Label — Revenue total */}
                {overviewData.length > 0 && (
                    <div className="absolute top-1/2 start-1/2 -translate-x-1/2 -translate-y-1/2 -mt-4 text-center pointer-events-none">
                        <p className="text-[10px] text-text-tertiary font-bold uppercase tracking-wider">
                            {isRtl ? 'الإيراد' : 'Revenue'}
                        </p>
                        <p className="text-base font-black text-text-primary font-mono">
                            ${revenue > 1000 ? (revenue / 1000).toFixed(1) + 'k' : revenue.toLocaleString()}
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ProfitChart;
