import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Baby } from 'lucide-react';

export default memo(function MedicalAlertBadge({ alert, className = '' }) {
    const { t } = useTranslation();

    if (!alert || !alert.has_alert || !Array.isArray(alert.kinds) || alert.kinds.length === 0) {
        return null;
    }

    const kinds = alert.kinds;
    const hasPregnancy = kinds.includes('pregnancy');
    const nonPregnancyKinds = kinds.filter((k) => k !== 'pregnancy' && k !== 'smoking');

    if (!hasPregnancy && nonPregnancyKinds.length === 0) {
        return null;
    }

    const pregnancyTooltip = t('patients.medical_conditions.pregnancy', 'Pregnancy/Lactation');
    const generalTooltip = t('patients.medical_alert_generic', 'تنبيه طبي');

    return (
        <span className={`inline-flex items-center gap-1 shrink-0 ${className}`}>
            {hasPregnancy && (
                <span
                    data-testid="medical-alert-pregnancy"
                    title={pregnancyTooltip}
                    aria-label={pregnancyTooltip}
                    className="inline-flex h-6 w-6 items-center justify-center rounded-lg border border-rose-200 bg-rose-50 text-rose-600 shadow-xs dark:border-rose-900/60 dark:bg-rose-950/50 dark:text-rose-300"
                >
                    <Baby size={14} aria-hidden="true" />
                </span>
            )}
            {nonPregnancyKinds.length > 0 && (
                <span
                    data-testid="medical-alert-warning"
                    title={generalTooltip}
                    aria-label={generalTooltip}
                    className="inline-flex h-6 w-6 items-center justify-center rounded-lg border border-amber-200 bg-amber-50 text-amber-700 shadow-xs dark:border-amber-900/60 dark:bg-amber-950/50 dark:text-amber-300"
                >
                    <AlertTriangle size={13} aria-hidden="true" />
                </span>
            )}
        </span>
    );
});
