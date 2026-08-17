import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    History,
    ArrowRight,
    CreditCard,
    Receipt,
    Inbox,
} from 'lucide-react';
import Money from '../../components/Money';

/**
 * Recent Activity Preview for Finance Overview V2.
 * Shows the last 8-10 actual cash movements (Payments & Expenses) with type indicator and link to full Activity.
 */
export default function RecentActivityPreview({
    activities = [],
    isLoading = false,
    currency = 'EGP',
    className = '',
}) {
    const { t, i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';

    if (isLoading) {
        return (
            <div className={`p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 ${className}`}>
                <div className="flex items-center justify-between">
                    <div className="h-5 w-36 bg-muted rounded animate-pulse"></div>
                    <div className="h-4 w-20 bg-muted rounded animate-pulse"></div>
                </div>
                <div className="space-y-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="h-12 bg-muted/40 rounded-xl animate-pulse"></div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <section
            aria-label={t('finance.activity.preview_title', 'آخر المعاملات المالية')}
            className={`p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4 ${className}`}
        >
            <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                    <h2 className="text-sm sm:text-base font-bold text-text-primary flex items-center gap-2">
                        <History className="w-4 h-4 text-primary" />
                        <span>{t('finance.activity.preview_title', 'آخر المعاملات والتحصيلات')}</span>
                    </h2>
                    <p className="text-xs text-text-secondary">
                        {t('finance.activity.preview_subtitle', 'سجل فوري للتحصيلات والمصروفات المسجلة')}
                    </p>
                </div>

                <Link
                    to="/finance/activity"
                    className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:text-primary/80 transition-colors"
                >
                    <span>{t('common.view_all', 'عرض الكل')}</span>
                    <ArrowRight className="w-3.5 h-3.5 rtl:rotate-180" />
                </Link>
            </div>

            {activities.length === 0 ? (
                <div className="py-8 flex flex-col items-center justify-center border border-dashed border-border rounded-xl text-center space-y-2">
                    <Inbox className="w-8 h-8 text-text-secondary/50" />
                    <p className="text-xs text-text-secondary">
                        {t('finance.activity.no_recent_activity', 'لا توجد معاملات مسجلة مؤخراً')}
                    </p>
                </div>
            ) : (
                <div className="divide-y divide-border/50">
                    {activities.map((item) => {
                        const isIncome = item.isIncome;
                        const Icon = isIncome ? CreditCard : Receipt;
                        const formattedDate = item.dateStr || (item.date instanceof Date ? item.date.toISOString().split('T')[0] : '');

                        return (
                            <Link
                                key={item.id}
                                to={item.to || '/finance/activity'}
                                className="flex items-center justify-between py-3 px-2 rounded-xl hover:bg-muted/40 transition-colors group"
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className={`p-2 rounded-xl flex-shrink-0 ${
                                            isIncome
                                                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                                : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
                                        }`}
                                    >
                                        <Icon className="w-4 h-4" />
                                    </div>
                                    <div className="space-y-0.5">
                                        <p className="text-xs sm:text-sm font-bold text-text-primary group-hover:text-primary transition-colors line-clamp-1">
                                            {item.title}
                                        </p>
                                        <div className="flex items-center gap-2 text-[11px] text-text-secondary">
                                            <span className="font-mono">{formattedDate}</span>
                                            {item.subtitle && <span>• {item.subtitle}</span>}
                                        </div>
                                    </div>
                                </div>

                                <div className="text-end flex-shrink-0">
                                    <Money
                                        amount={item.amount}
                                        currency={currency}
                                        colored
                                        showSign
                                        size="sm"
                                    />
                                    <p className="text-[10px] font-semibold text-text-secondary">
                                        {isIncome ? t('finance.metrics.payment', 'تحصيل') : t('finance.metrics.expense', 'مصروف')}
                                    </p>
                                </div>
                            </Link>
                        );
                    })}
                </div>
            )}
        </section>
    );
}
