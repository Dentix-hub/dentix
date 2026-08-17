import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Search, X } from 'lucide-react';

export default memo(function PatientFilters({ search, onSearchChange, isFetching }) {
    const { t } = useTranslation();

    return (
        <div className="sticky top-0 z-10 border-b border-border bg-surface/95 p-4 backdrop-blur-md md:p-5">
            <div className="relative max-w-3xl">
                <Search className="pointer-events-none absolute start-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted" aria-hidden="true" />
                <input
                    type="search"
                    value={search}
                    onChange={(event) => onSearchChange(event.target.value)}
                    placeholder={t('patients.workspace_search_placeholder', 'Search by name, file number, or phone...')}
                    className="h-12 w-full rounded-xl border border-border bg-background ps-12 pe-12 text-sm font-semibold text-text-primary outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
                    autoComplete="off"
                    dir="auto"
                    aria-label={t('patients.workspace_search_label', 'Search patients')}
                />
                <div className="absolute end-3 top-1/2 flex -translate-y-1/2 items-center gap-1">
                    {isFetching && <Loader2 className="h-4 w-4 animate-spin text-primary" aria-label={t('common.loading')} />}
                    {search && (
                        <button
                            type="button"
                            onClick={() => onSearchChange('')}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-text-muted transition hover:bg-surface-hover hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
                            aria-label={t('common.clear', 'Clear search')}
                        >
                            <X className="h-4 w-4" />
                        </button>
                    )}
                </div>
            </div>
            <p className="mt-2 text-xs text-text-muted">
                {t('patients.workspace_search_hint', 'Arabic name variants and Egyptian phone formats are supported.')}
            </p>
        </div>
    );
});
