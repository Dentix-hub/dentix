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
    const tooltip = isAllTime
        ? t('finance.scope.all_time_tooltip', 'يشمل جميع المعاملات غير المسددة عبر كل الفترات')
        : t('finance.scope.period_tooltip', 'خاص بنطاق التواريخ المحدد فقط');

    return (
        <span
            className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold tracking-wide transition-colors ${
                isAllTime
                    ? 'border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                    : 'border-primary/20 bg-primary/10 text-primary'
            } ${className}`}
            title={tooltip}
            aria-label={displayLabel}
        >
            {isAllTime ? (
                <Layers className="h-3 w-3 shrink-0" aria-hidden="true" />
            ) : (
                <Calendar className="h-3 w-3 shrink-0" aria-hidden="true" />
            )}
            <span className="hidden max-w-40 truncate sm:inline">{displayLabel}</span>
        </span>
    );
}
