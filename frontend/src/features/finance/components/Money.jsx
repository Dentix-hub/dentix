import { useTranslation } from 'react-i18next';
import { formatMoney } from '../utils/currencyFormatter';

/**
 * Shared Money/Currency display component.
 * Uses Intl.NumberFormat via formatMoney with semantic styling and RTL awareness.
 */
export default function Money({
    amount = 0,
    currency = 'EGP',
    compact = false,
    colored = false,
    showSign = false,
    size = 'md',
    className = '',
}) {
    const { i18n } = useTranslation();
    const isArabic = i18n.language === 'ar';
    const num = Number(amount) || 0;

    const formatted = formatMoney(Math.abs(num), {
        currency,
        locale: isArabic ? 'ar-EG' : 'en-US',
        compact,
    });

    const isPositive = num > 0;
    const isNegative = num < 0;
    const sizeClasses = {
        xs: 'text-xs',
        sm: 'text-sm font-medium',
        md: 'text-base font-bold',
        lg: 'text-lg font-bold',
        xl: 'text-xl font-extrabold tracking-tight',
        '2xl': 'text-2xl lg:text-3xl font-black tracking-tight',
    }[size] || 'text-base font-bold';

    let colorClass = 'text-text-primary';
    if (colored) {
        if (isPositive) colorClass = 'text-emerald-600 dark:text-emerald-400';
        else if (isNegative) colorClass = 'text-rose-600 dark:text-rose-400';
        else colorClass = 'text-text-secondary';
    }

    const signPrefix = showSign && isPositive ? '+' : isNegative ? '-' : '';

    return (
        <span
            className={`inline-flex items-center gap-0.5 font-mono ${sizeClasses} ${colorClass} ${className}`}
            dir="ltr"
            aria-label={`${num} ${currency}`}
        >
            {signPrefix && <span className="font-sans me-0.5">{signPrefix}</span>}
            <span>{formatted}</span>
        </span>
    );
}
