import { memo } from 'react';
import { CalendarDays, Clock3, UserRound, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const BASE_FILTERS = [
    { id: 'all', labelKey: 'patients.scope_all', icon: Users },
    { id: 'today', labelKey: 'patients.scope_today', icon: CalendarDays },
    { id: 'recent', labelKey: 'patients.scope_recent', icon: Clock3 },
];

export default memo(function PatientQuickFilters({ scope, onScopeChange, isDoctor }) {
    const { t } = useTranslation();
    const filters = isDoctor
        ? [...BASE_FILTERS, { id: 'mine', labelKey: 'patients.scope_mine', icon: UserRound }]
        : BASE_FILTERS;

    return (
        <div className="border-b border-border bg-surface px-4 pb-4 md:px-5" aria-label={t('patients.quick_filters', 'Patient filters')}>
            <div className="flex gap-2 overflow-x-auto pb-1" role="group">
                {filters.map(({ id, labelKey, icon: Icon }) => {
                    const active = scope === id;
                    return (
                        <button
                            key={id}
                            type="button"
                            onClick={() => onScopeChange(id)}
                            aria-pressed={active}
                            className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-bold transition focus:outline-none focus:ring-2 focus:ring-primary/30 ${active ? 'border-primary bg-primary text-white shadow-sm' : 'border-border bg-background text-text-secondary hover:border-primary/40 hover:text-primary'}`}
                        >
                            <Icon className="h-4 w-4" aria-hidden="true" />
                            {t(labelKey)}
                        </button>
                    );
                })}
            </div>
        </div>
    );
});
