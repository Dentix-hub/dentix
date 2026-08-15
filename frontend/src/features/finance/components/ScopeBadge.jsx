import { useTranslation } from 'react-i18next';
import { Calendar, Layers } from 'lucide-react';

/**
 * ScopeBadge clarifies whether a displayed metric/value belongs to
 * the selected date range period or is an all-time/current balance.
 */
export default function ScopeBadge({
    scope = 'period', // 'period' | 'all_time' | 'custom'
    label,
    className = '',
}) {
    const { t } = useTranslation();

    const isAllTime = scope === 'all_time';

    const defaultLabel = isAllTime
        ? t('finance.scope.all_time', 'الرصيد التراكمي (الكل)')
        : t('finance.scope.period', 'الفترة المحددة');

    const displayLabel = label || defaultLabel;

    return (
        <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold tracking-wide transition-colors ${
                isAllTime
                    ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20'
                    : 'bg-primary/10 text-primary border border-primary/20'
            } ${className}`}
            title={isAllTime ? t('finance.scope.all_time_tooltip', 'يشمل جميع المعاملات غير المسددة عبر كل الفترات') : t('finance.scope.period_tooltip', 'خاص بنطاق التواريخ المحدد فقط')}
        >
            {isAllTime ? (
                <Layers className="w-3 h-3 flex-shrink-0" />
            ) : (
                <Calendar className="w-3 h-3 flex-shrink-0" />
            )}
            <span className="truncate">{displayLabel}</span>
        </span>
    );
}
