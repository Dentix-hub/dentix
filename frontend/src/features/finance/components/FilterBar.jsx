import { useTranslation } from 'react-i18next';
import { Search, X, Filter, RotateCcw } from 'lucide-react';

/**
 * FilterBar component for tables and lists in Finance V2.
 * Uses controlled filter definitions and supports active filter chips.
 */
export default function FilterBar({
    searchValue = '',
    onSearchChange,
    searchPlaceholder,
    filters = [], // Array of { id, label, options: [{ value, label }], value, onChange }
    onReset,
    children, // Optional custom controls/buttons on the right
    className = '',
}) {
    const { t } = useTranslation();

    const hasActiveFilters = Boolean(
        searchValue ||
        filters.some((filter) => filter.value && filter.value !== 'all')
    );

    const handleClearAll = () => {
        if (onReset) {
            onReset();
            return;
        }

        if (onSearchChange) onSearchChange('');
        filters.forEach((filter) => {
            if (!filter.onChange) return;
            const hasEmptyOption = filter.options?.some((option) => option.value === '');
            filter.onChange(hasEmptyOption ? '' : 'all');
        });
    };

    const resolvedSearchLabel = searchPlaceholder || t('common.search', 'بحث...');

    return (
        <div className={`space-y-3 ${className}`}>
            <div className="flex flex-col items-stretch justify-between gap-3 sm:flex-row sm:items-center">
                {/* Search input + primary dropdowns */}
                <div className="flex min-w-0 flex-1 flex-col gap-2.5 sm:flex-row sm:flex-wrap sm:items-center">
                    {onSearchChange && (
                        <div className="relative w-full min-w-0 flex-1 sm:min-w-[200px] sm:max-w-xs">
                            <Search className="absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
                            <input
                                type="text"
                                value={searchValue}
                                onChange={(event) => onSearchChange(event.target.value)}
                                placeholder={resolvedSearchLabel}
                                aria-label={resolvedSearchLabel}
                                className="w-full rounded-lg border border-border bg-card py-2 ps-9 pe-8 text-sm text-text-primary placeholder:text-text-secondary/70 transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                            />
                            {searchValue && (
                                <button
                                    type="button"
                                    onClick={() => onSearchChange('')}
                                    className="absolute end-2.5 top-1/2 -translate-y-1/2 rounded-full p-0.5 text-text-secondary hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                    aria-label={t('common.clear_search', 'مسح البحث')}
                                >
                                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                                </button>
                            )}
                        </div>
                    )}

                    {filters.map((filter) => {
                        const hasEmptyOption = filter.options?.some((option) => option.value === '');
                        const resolvedValue = filter.value ?? (hasEmptyOption ? '' : 'all');

                        return (
                            <div key={filter.id} className="relative w-full sm:w-auto sm:min-w-[130px]">
                                <select
                                    value={resolvedValue}
                                    onChange={(event) => filter.onChange?.(event.target.value)}
                                    aria-label={filter.label}
                                    className="w-full cursor-pointer appearance-none rounded-lg border border-border bg-card px-3 py-2 pe-8 text-sm font-medium text-text-primary transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-sm"
                                >
                                    {filter.options.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                                <div className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 text-text-secondary" aria-hidden="true">
                                    <Filter className="h-3.5 w-3.5" />
                                </div>
                            </div>
                        );
                    })}

                    {hasActiveFilters && (
                        <button
                            type="button"
                            onClick={handleClearAll}
                            className="inline-flex w-full items-center justify-center gap-1 rounded-lg bg-rose-50 px-2.5 py-2 text-xs font-semibold text-rose-600 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 dark:bg-rose-950/30 dark:text-rose-400 sm:w-auto"
                        >
                            <RotateCcw className="h-3 w-3" aria-hidden="true" />
                            <span>{t('common.reset_filters', 'إعادة ضبط')}</span>
                        </button>
                    )}
                </div>

                {children && (
                    <div className="flex w-full shrink-0 items-center gap-2 sm:w-auto">
                        {children}
                    </div>
                )}
            </div>

            {hasActiveFilters && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="me-1 text-[11px] font-bold uppercase tracking-wider text-text-secondary">
                        {t('common.active_filters', 'الفلاتر النشطة:')}
                    </span>

                    {searchValue && (
                        <span className="inline-flex max-w-full items-center gap-1 rounded-md border border-border bg-muted px-2 py-0.5 text-xs font-medium text-text-primary">
                            <span className="min-w-0 truncate">{t('common.search_for', 'بحث:')} &ldquo;{searchValue}&rdquo;</span>
                            <button
                                type="button"
                                onClick={() => onSearchChange('')}
                                className="shrink-0 rounded-sm text-text-secondary hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                aria-label={t('common.remove_search_filter', 'إزالة فلتر البحث')}
                            >
                                <X className="h-3 w-3" aria-hidden="true" />
                            </button>
                        </span>
                    )}

                    {filters.map((filter) => {
                        if (!filter.value || filter.value === 'all') return null;
                        const selectedOption = filter.options.find((option) => option.value === filter.value);
                        const selectedLabel = selectedOption?.label || filter.value;

                        return (
                            <span
                                key={filter.id}
                                className="inline-flex max-w-full items-center gap-1 rounded-md border border-primary/20 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
                            >
                                <span className="min-w-0 truncate">{filter.label}: {selectedLabel}</span>
                                <button
                                    type="button"
                                    onClick={() => {
                                        const hasEmptyOption = filter.options?.some((option) => option.value === '');
                                        filter.onChange?.(hasEmptyOption ? '' : 'all');
                                    }}
                                    className="shrink-0 rounded-sm hover:opacity-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                                    aria-label={`${t('common.remove_filter', 'إزالة الفلتر')} ${filter.label}: ${selectedLabel}`}
                                >
                                    <X className="h-3 w-3" aria-hidden="true" />
                                </button>
                            </span>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
