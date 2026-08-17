import { useQuery } from '@tanstack/react-query';
import { getProfitabilityTrend } from '@/api/analytics';
import { useTranslation } from 'react-i18next';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    CartesianGrid,
    LazyChart
} from '@/components/charts/LazyChart';
import { TrendingUp, LineChart as LineChartIcon } from 'lucide-react';

const CustomTooltip = ({ active, payload, label, currency }) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-slate-900/95 border border-slate-700/80 p-3 rounded-xl shadow-2xl text-xs backdrop-blur-md space-y-1.5 min-w-[160px]">
                <p className="font-bold text-slate-300 border-b border-slate-800 pb-1">{label}</p>
                {payload.map((entry, index) => (
                    <div key={index} className="flex items-center justify-between gap-4 font-mono">
                        <span className="flex items-center gap-1.5 text-slate-400 font-sans">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }}></span>
                            {entry.name}:
                        </span>
                        <span className="font-bold text-white">
                            {Number(entry.value).toLocaleString()} {currency}
                        </span>
                    </div>
                ))}
            </div>
        );
    }
    return null;
};

export default function RevenueTrendChart({ period = '30d' }) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const { data: trendData, isLoading, error } = useQuery({
        queryKey: ['profitability_trend', period],
        queryFn: async () => {
            const res = await getProfitabilityTrend(period);
            return res.data?.timeline || [];
        },
        staleTime: 2 * 60 * 1000,
    });

    const currency = t('analytics.general_analysis.currency') || 'EGP';

    if (isLoading) {
        return (
            <div className="bg-surface p-6 rounded-3xl border border-border/50 shadow-sm space-y-4">
                <div className="h-6 bg-surface-hover w-48 rounded-lg animate-pulse"></div>
                <div className="h-[300px] bg-surface-hover/50 rounded-2xl animate-pulse w-full"></div>
            </div>
        );
    }

    if (error || !trendData) {
        return null;
    }

    // Format dates for display
    const formattedData = trendData.map(item => {
        const dateObj = new Date(item.date);
        const dayMonth = dateObj.toLocaleDateString(isRtl ? 'ar-EG' : 'en-US', { day: 'numeric', month: 'short' });
        return {
            ...item,
            displayDate: dayMonth,
        };
    });

    return (
        <div className="bg-surface p-6 rounded-3xl border border-border/50 shadow-sm space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                    <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
                        <LineChartIcon className="text-sky-500" size={20} />
                        {isRtl ? 'المنحنى الزمني للإيرادات والأرباح' : 'Financial Trend Curve'}
                    </h3>
                    <p className="text-xs text-text-secondary mt-0.5">
                        {isRtl ? 'مقارنة الإيرادات اليومية وتكاليف التشغيل وصافي الربح عبر الزمن' : 'Daily breakdown of revenue, expenses, and net profit over time'}
                    </p>
                </div>
                <div className="flex items-center gap-4 text-xs font-bold">
                    <span className="flex items-center gap-1.5 text-sky-500">
                        <span className="w-3 h-3 rounded-full bg-sky-500 inline-block"></span>
                        {isRtl ? 'الإيراد' : 'Revenue'}
                    </span>
                    <span className="flex items-center gap-1.5 text-emerald-500">
                        <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span>
                        {isRtl ? 'صافي الربح' : 'Net Profit'}
                    </span>
                    <span className="flex items-center gap-1.5 text-rose-500">
                        <span className="w-3 h-3 rounded-full bg-rose-500 inline-block"></span>
                        {isRtl ? 'المصروفات' : 'Expenses'}
                    </span>
                </div>
            </div>

            <div className="h-[300px] w-full pt-2">
                <LazyChart>
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.35} />
                                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                            <XAxis
                                dataKey="displayDate"
                                stroke="#94a3b8"
                                fontSize={11}
                                tickLine={false}
                                reversed={isRtl}
                            />
                            <YAxis
                                stroke="#94a3b8"
                                fontSize={11}
                                tickLine={false}
                                tickFormatter={(v) => `$${v}`}
                            />
                            <Tooltip content={<CustomTooltip currency={currency} />} />
                            <Area
                                type="monotone"
                                dataKey="revenue"
                                name={isRtl ? 'الإيراد' : 'Revenue'}
                                stroke="#0ea5e9"
                                strokeWidth={3}
                                fillOpacity={1}
                                fill="url(#colorRevenue)"
                            />
                            <Area
                                type="monotone"
                                dataKey="net_profit"
                                name={isRtl ? 'صافي الربح' : 'Net Profit'}
                                stroke="#10b981"
                                strokeWidth={3}
                                fillOpacity={1}
                                fill="url(#colorProfit)"
                            />
                            <Area
                                type="monotone"
                                dataKey="expenses"
                                name={isRtl ? 'المصروفات' : 'Expenses'}
                                stroke="#f43f5e"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                fillOpacity={0}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </LazyChart>
            </div>
        </div>
    );
}
