import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Search, X, Filter, RotateCcw } from 'lucide-react';

/**
 * FilterBar component for tables and lists in Finance V2.
 * Syncs filters with URL search parameters and supports active filter chips.
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
    const [searchParams, setSearchParams] = useSearchParams();

    // Check if any filter or search is active
    const hasActiveFilters = Boolean(
        searchValue ||
        filters.some((f) => f.value && f.value !== 'all' && f.value !== '')
    );

    const handleClearAll = () => {
        if (onReset) {
            onReset();
        } else {
            if (onSearchChange) onSearchChange('');
            filters.forEach((f) => f.onChange && f.onChange('all'));
        }
    };

    return (
        <div className={`space-y-3 ${className}`}>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                {/* Left: Search input + Primary Dropdowns */}
                <div className="flex flex-wrap items-center gap-2.5 flex-1">
                    {/* Search Box */}
                    {onSearchChange && (
                        <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
                            <Search className="w-4 h-4 absolute start-3 top-1/2 -translate-y-1/2 text-text-secondary" />
                            <input
                                type="text"
                                value={searchValue}
                                onChange={(e) => onSearchChange(e.target.value)}
                                placeholder={searchPlaceholder || t('common.search', 'بحث...')}
                                className="w-full ps-9 pe-8 py-2 text-xs sm:text-sm bg-card border border-border rounded-lg text-text-primary placeholder:text-text-secondary/70 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                            />
                            {searchValue && (
                                <button
                                    type="button"
                                    onClick={() => onSearchChange('')}
                                    className="absolute end-2.5 top-1/2 -translate-y-1/2 p-0.5 text-text-secondary hover:text-text-primary rounded-full"
                                    aria-label={t('common.clear_search', 'مسح البحث')}
                                >
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            )}
                        </div>
                    )}

                    {/* Filter Dropdowns */}
                    {filters.map((filter) => (
                        <div key={filter.id} className="relative min-w-[130px]">
                            <select
                                value={filter.value || 'all'}
                                onChange={(e) => filter.onChange(e.target.value)}
                                className="w-full px-3 py-2 text-xs sm:text-sm bg-card border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer appearance-none pe-8 font-medium transition-colors"
                            >
                                {filter.options.map((opt) => (
                                    <option key={opt.value} value={opt.value}>
                                        {opt.label}
                                    </option>
                                ))}
                            </select>
                            <div className="absolute end-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-text-secondary">
                                <Filter className="w-3.5 h-3.5" />
                            </div>
                        </div>
                    ))}

                    {/* Reset All Button */}
                    {hasActiveFilters && (
                        <button
                            type="button"
                            onClick={handleClearAll}
                            className="inline-flex items-center gap-1 px-2.5 py-2 text-xs font-semibold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 hover:bg-rose-100 rounded-lg transition-colors"
                        >
                            <RotateCcw className="w-3 h-3" />
                            <span>{t('common.reset_filters', 'إعادة ضبط')}</span>
                        </button>
                    )}
                </div>

                {/* Right: Custom actions / Extra buttons */}
                {children && (
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {children}
                    </div>
                )}
            </div>

            {/* Active Filters Chips */}
            {hasActiveFilters && (
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-[11px] font-bold text-text-secondary uppercase tracking-wider me-1">
                        {t('common.active_filters', 'الفلاتر النشطة:')}
                    </span>

                    {searchValue && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted text-text-primary text-xs font-medium border border-border">
                            <span>{t('common.search_for', 'بحث:')} &ldquo;{searchValue}&rdquo;</span>
                            <button
                                type="button"
                                onClick={() => onSearchChange('')}
                                className="text-text-secondary hover:text-text-primary"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        </span>
                    )}

                    {filters.map((filter) => {
                        if (!filter.value || filter.value === 'all') return null;
                        const selectedOption = filter.options.find((o) => o.value === filter.value);
                        return (
                            <span
                                key={filter.id}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-medium border border-primary/20"
                            >
                                <span>{filter.label}: {selectedOption?.label || filter.value}</span>
                                <button
                                    type="button"
                                    onClick={() => filter.onChange('all')}
                                    className="hover:opacity-75"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                            </span>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
