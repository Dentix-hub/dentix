import { useTranslation } from 'react-i18next';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { TrendingUp, BarChart2 } from 'lucide-react';
import { formatMoney } from '../../utils/currencyFormatter';

/**
 * Financial Trend Chart for Overview V2.
 * Visualizes Collections (Cash In) vs Expenses/Deductions (Cash Out) over time.
 */
export default function FinancialTrendChart({
    timeline = [],
    isLoading = false,
    currency = 'EGP',
    className = '',
}) {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';

    // Format timeline dates for chart display
    const formattedData = timeline.map((item) => {
        let label = item.date;
        try {
            const d = new Date(item.date);
            label = d.toLocaleDateString(isArabic ? 'ar-EG' : 'en-US', {
                month: 'numeric',
                day: 'numeric',
            });
        } catch {
            label = item.date;
        }

        return {
            date: item.date,
            displayDate: label,
            revenue: Number(item.revenue) || 0,
            expenses: Number(item.expenses) || 0,
            net_profit: Number(item.net_profit) || 0,
        };
    });

    // Custom Tooltip
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-card/95 backdrop-blur-sm border border-border p-3 rounded-xl shadow-xl space-y-1.5 text-xs">
                    <p className="font-bold text-text-primary border-b border-border/50 pb-1 font-mono">
                        {payload[0]?.payload?.date || label}
                    </p>
                    <div className="space-y-1">
                        <div className="flex items-center justify-between gap-4 text-emerald-600 dark:text-emerald-400">
                            <span className="flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
                                {t('finance.metrics.collected', 'التحصيلات')}:
                            </span>
                            <span className="font-mono font-bold" dir="ltr">
                                {formatMoney(payload[0]?.value, { currency, locale: isArabic ? 'ar-EG' : 'en-US' })}
                            </span>
                        </div>
                        <div className="flex items-center justify-between gap-4 text-rose-600 dark:text-rose-400">
                            <span className="flex items-center gap-1">
                                <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
                                {t('finance.metrics.expenses', 'المصروفات')}:
                            </span>
                            <span className="font-mono font-bold" dir="ltr">
                                {formatMoney(payload[1]?.value, { currency, locale: isArabic ? 'ar-EG' : 'en-US' })}
                            </span>
                        </div>
                    </div>
                </div>
            );
        }
        return null;
    };

    if (isLoading) {
        return (
            <div className={`p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 ${className}`}>
                <div className="h-5 w-40 bg-muted rounded animate-pulse"></div>
                <div className="h-64 bg-muted/40 rounded-xl animate-pulse"></div>
            </div>
        );
    }

    const hasData = formattedData.length > 0 && formattedData.some((d) => d.revenue > 0 || d.expenses > 0);

    return (
        <section
            aria-label={t('finance.overview.trend_chart_title', 'اتجاهات التحصيل والمصروفات')}
            className={`p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 ${className}`}
        >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="space-y-0.5">
                    <h2 className="text-sm sm:text-base font-bold text-text-primary flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-primary" />
                        <span>{t('finance.overview.trend_chart_title', 'حركة التدفق المالي (التحصيلات مقابل المصروفات)')}</span>
                    </h2>
                    <p className="text-xs text-text-secondary">
                        {t('finance.overview.trend_chart_subtitle', 'تتبع يومي لمقارنة السيولة الداخلة بالنفقات التشغيلية')}
                    </p>
                </div>

                <div className="flex items-center gap-3 text-xs">
                    <span className="inline-flex items-center gap-1.5 text-text-secondary">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                        {t('finance.metrics.collected', 'التحصيلات')}
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-text-secondary">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                        {t('finance.metrics.expenses', 'المصروفات')}
                    </span>
                </div>
            </div>

            {!hasData ? (
                <div className="h-64 flex flex-col items-center justify-center border border-dashed border-border rounded-xl text-center p-6 space-y-2">
                    <BarChart2 className="w-8 h-8 text-text-secondary/50" />
                    <p className="text-xs text-text-secondary">
                        {t('finance.overview.no_trend_data', 'لا توجد حركات مالية مسجلة خلال هذه الفترة')}
                    </p>
                </div>
            ) : (
                <div className="h-64 sm:h-72 w-full pt-2" dir="ltr">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                            data={formattedData}
                            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                        >
                            <defs>
                                <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="colorExp" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-border/40" />
                            <XAxis
                                dataKey="displayDate"
                                stroke="currentColor"
                                className="text-[11px] text-text-secondary font-mono"
                                tickLine={false}
                            />
                            <YAxis
                                stroke="currentColor"
                                className="text-[11px] text-text-secondary font-mono"
                                tickLine={false}
                                tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Area
                                type="monotone"
                                dataKey="revenue"
                                stroke="#10b981"
                                strokeWidth={2.5}
                                fillOpacity={1}
                                fill="url(#colorRev)"
                                name={t('finance.metrics.collected', 'التحصيلات')}
                            />
                            <Area
                                type="monotone"
                                dataKey="expenses"
                                stroke="#f43f5e"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                fillOpacity={1}
                                fill="url(#colorExp)"
                                name={t('finance.metrics.expenses', 'المصروفات')}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            )}
        </section>
    );
}
