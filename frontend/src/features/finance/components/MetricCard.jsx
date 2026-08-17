import { Link } from 'react-router-dom';
import { ArrowUpRight, ArrowDownRight, TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import Money from './Money';
import ScopeBadge from './ScopeBadge';

/**
 * MetricCard component for displaying headline financial KPIs.
 * Built without superfluous decoration; clean, readable typography and strict hierarchy.
 */
export default function MetricCard({
    title,
    amount = 0,
    currency = 'EGP',
    scope = 'period', // 'period' | 'all_time' | 'custom'
    scopeLabel,
    subtitle,
    trend, // { value: number, direction: 'up' | 'down', label: string, isPositive: boolean }
    icon: Icon,
    to,
    isLoading = false,
    colored = false,
    className = '',
}) {
    if (isLoading) {
        return (
            <div className={`p-5 rounded-2xl border border-border bg-card shadow-sm animate-pulse space-y-3 ${className}`}>
                <div className="flex items-center justify-between">
                    <div className="h-4 w-28 bg-muted rounded"></div>
                    <div className="h-4 w-16 bg-muted rounded-full"></div>
                </div>
                <div className="h-8 w-36 bg-muted rounded"></div>
                <div className="h-3 w-24 bg-muted rounded"></div>
            </div>
        );
    }

    const CardContent = (
        <div className={`p-5 rounded-2xl border border-border bg-card hover:border-primary/30 transition-all duration-200 shadow-sm flex flex-col justify-between group ${to ? 'cursor-pointer hover:shadow-md' : ''} ${className}`}>
            <div className="space-y-3">
                {/* Header: Title + Scope Badge */}
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                        {Icon && (
                            <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                                <Icon className="w-4 h-4" />
                            </div>
                        )}
                        <h3 className="text-sm font-semibold text-text-secondary line-clamp-1">
                            {title}
                        </h3>
                    </div>
                    <ScopeBadge scope={scope} label={scopeLabel} />
                </div>

                {/* Amount */}
                <div className="pt-1">
                    <Money
                        amount={amount}
                        currency={currency}
                        colored={colored}
                        size="2xl"
                    />
                </div>
            </div>

            {/* Footer: Trend / Subtitle / Action */}
            <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between text-xs text-text-secondary">
                {trend ? (
                    <div className="flex items-center gap-1.5">
                        <span
                            className={`inline-flex items-center font-bold font-mono ${
                                trend.isPositive
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : 'text-rose-600 dark:text-rose-400'
                            }`}
                        >
                            {trend.direction === 'up' ? (
                                <ArrowUpRight className="w-3.5 h-3.5" />
                            ) : (
                                <ArrowDownRight className="w-3.5 h-3.5" />
                            )}
                            {trend.value}%
                        </span>
                        <span>{trend.label}</span>
                    </div>
                ) : (
                    <span>{subtitle || ''}</span>
                )}

                {to && (
                    <span className="inline-flex items-center gap-0.5 text-primary font-semibold group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5 transition-transform">
                        <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" />
                    </span>
                )}
            </div>
        </div>
    );

    if (to) {
        return (
            <Link to={to} className="block focus:outline-none focus:ring-2 focus:ring-primary rounded-2xl">
                {CardContent}
            </Link>
        );
    }

    return CardContent;
}
