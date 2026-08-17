import { useTranslation } from 'react-i18next';
import DateRangePicker from './DateRangePicker';

/**
 * Finance Header with stable title, subtitle, date range picker, and optional primary actions.
 */
export default function FinanceHeader({
    title,
    description,
    showDatePicker = true,
    actionButton,
    className = '',
}) {
    const { t } = useTranslation();

    return (
        <header className={`flex flex-col md:flex-row md:items-center justify-between gap-4 py-4 px-4 sm:px-6 bg-card border-b border-border ${className}`}>
            <div className="space-y-1">
                <h1 className="text-xl sm:text-2xl font-black text-text-primary tracking-tight">
                    {title || t('finance.title', 'الإدارة المالية')}
                </h1>
                <p className="text-xs sm:text-sm text-text-secondary">
                    {description || t('finance.subtitle', 'متابعة التحصيلات، التكاليف، الأرصدة ومستحقات الفريق')}
                </p>
            </div>

            <div className="flex items-center flex-wrap gap-2.5 self-start md:self-auto">
                {showDatePicker && <DateRangePicker />}
                {actionButton && <div>{actionButton}</div>}
            </div>
        </header>
    );
}
