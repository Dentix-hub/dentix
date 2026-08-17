import { useTranslation } from 'react-i18next';
import {
    ChevronUp,
    ChevronDown,
    ChevronsUpDown,
    ChevronLeft,
    ChevronRight,
    AlertCircle,
    Inbox,
    RefreshCw,
} from 'lucide-react';

/**
 * Reusable, accessible Data Table for Finance V2.
 * Supports sorting, pagination, skeleton loading, empty/error states, and mobile card fallback.
 */
export default function DataTable({
    columns = [], // Array of { id, header, accessor, cell, sortable, align: 'start'|'center'|'end', width }
    data = [],
    keyField = 'id',
    sortBy,
    sortDirection = 'desc', // 'asc' | 'desc'
    onSort,
    page = 1,
    pageSize = 10,
    totalItems = 0,
    onPageChange,
    isLoading = false,
    isError = false,
    errorMessage,
    onRetry,
    renderMobileCard, // Optional custom mobile card renderer: (item, index) => ReactNode
    emptyMessage,
    emptyIcon: EmptyIcon = Inbox,
    className = '',
}) {
    const { t } = useTranslation();

    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    const canPrev = page > 1;
    const canNext = page < totalPages;

    const handleHeaderClick = (col) => {
        if (!col.sortable || !onSort) return;
        if (sortBy === col.id) {
            onSort(col.id, sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            onSort(col.id, 'desc');
        }
    };

    const getAlignmentClass = (align = 'start') => {
        switch (align) {
            case 'center':
                return 'text-center justify-center';
            case 'end':
                return 'text-end justify-end';
            default:
                return 'text-start justify-start';
        }
    };

    // Loading State
    if (isLoading) {
        return (
            <div className={`w-full bg-card border border-border rounded-xl overflow-hidden shadow-sm ${className}`}>
                <div className="p-4 space-y-3">
                    <div className="h-10 bg-muted/60 rounded-lg animate-pulse"></div>
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="h-14 bg-muted/30 rounded-lg animate-pulse"></div>
                    ))}
                </div>
            </div>
        );
    }

    // Error State
    if (isError) {
        return (
            <div className={`w-full bg-card border border-rose-200 dark:border-rose-900/50 rounded-xl p-8 text-center space-y-4 shadow-sm ${className}`}>
                <div className="w-12 h-12 rounded-full bg-rose-100 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 mx-auto flex items-center justify-center">
                    <AlertCircle className="w-6 h-6" aria-hidden="true" />
                </div>
                <div className="space-y-1">
                    <h4 className="text-base font-bold text-text-primary">
                        {t('common.error_loading_data', 'حدث خطأ أثناء تحميل البيانات')}
                    </h4>
                    <p className="text-xs text-text-secondary max-w-sm mx-auto">
                        {errorMessage || t('common.try_again_later', 'يرجى المحاولة مرة أخرى أو التحقق من الاتصال')}
                    </p>
                </div>
                {onRetry && (
                    <button
                        type="button"
                        onClick={onRetry}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                    >
                        <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
                        <span>{t('common.retry', 'إعادة المحاولة')}</span>
                    </button>
                )}
            </div>
        );
    }

    // Empty State
    if (!data || data.length === 0) {
        return (
            <div className={`w-full bg-card border border-border rounded-xl p-12 text-center space-y-3 shadow-sm ${className}`}>
                <div className="w-12 h-12 rounded-full bg-muted text-text-secondary mx-auto flex items-center justify-center">
                    <EmptyIcon className="w-6 h-6" aria-hidden="true" />
                </div>
                <h4 className="text-sm font-semibold text-text-secondary">
                    {emptyMessage || t('common.no_data', 'لا توجد بيانات للعرض')}
                </h4>
            </div>
        );
    }

    return (
        <div className={`w-full space-y-3 ${className}`}>
            {/* Desktop Table View */}
            <div className="hidden md:block w-full bg-card border border-border rounded-xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-xs sm:text-sm text-start border-collapse">
                        <thead>
                            <tr className="border-b border-border bg-muted/40 text-text-secondary font-bold text-xs uppercase tracking-wider">
                                {columns.map((col) => {
                                    const isSorted = sortBy === col.id;
                                    const ariaSort = col.sortable
                                        ? (isSorted ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none')
                                        : undefined;

                                    return (
                                        <th
                                            key={col.id}
                                            scope="col"
                                            aria-sort={ariaSort}
                                            className={`px-4 py-3.5 font-bold ${getAlignmentClass(col.align)}`}
                                            style={col.width ? { width: col.width } : undefined}
                                        >
                                            {col.sortable && onSort ? (
                                                <button
                                                    type="button"
                                                    onClick={() => handleHeaderClick(col)}
                                                    className={`inline-flex items-center gap-1.5 rounded-md hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${getAlignmentClass(col.align)}`}
                                                >
                                                    <span>{col.header}</span>
                                                    <span className="text-text-secondary/70" aria-hidden="true">
                                                        {isSorted ? (
                                                            sortDirection === 'asc' ? (
                                                                <ChevronUp className="w-3.5 h-3.5 text-primary" />
                                                            ) : (
                                                                <ChevronDown className="w-3.5 h-3.5 text-primary" />
                                                            )
                                                        ) : (
                                                            <ChevronsUpDown className="w-3.5 h-3.5 opacity-50" />
                                                        )}
                                                    </span>
                                                </button>
                                            ) : (
                                                <div className={`inline-flex items-center gap-1.5 ${getAlignmentClass(col.align)}`}>
                                                    <span>{col.header}</span>
                                                </div>
                                            )}
                                        </th>
                                    );
                                })}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60">
                            {data.map((item, index) => {
                                const rowKey = item[keyField] || index;
                                return (
                                    <tr
                                        key={rowKey}
                                        className="hover:bg-muted/30 transition-colors group"
                                    >
                                        {columns.map((col) => {
                                            const val = col.accessor ? (typeof col.accessor === 'function' ? col.accessor(item) : item[col.accessor]) : item[col.id];
                                            return (
                                                <td
                                                    key={col.id}
                                                    className={`px-4 py-3.5 align-middle text-text-primary ${getAlignmentClass(col.align)}`}
                                                >
                                                    {col.cell ? (typeof col.cell === 'function' ? col.cell(item, { row: item, value: val, index }) : col.cell) : val}
                                                </td>
                                            );
                                        })}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Mobile Semantic Card View */}
            <div className="block md:hidden space-y-2.5">
                {data.map((item, index) => {
                    const rowKey = item[keyField] || index;
                    if (renderMobileCard) {
                        return <div key={rowKey}>{renderMobileCard(item, index)}</div>;
                    }

                    // Default Mobile Card
                    return (
                        <div
                            key={rowKey}
                            className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-2"
                        >
                            {columns.map((col) => {
                                const val = col.accessor ? (typeof col.accessor === 'function' ? col.accessor(item) : item[col.accessor]) : item[col.id];
                                return (
                                    <div key={col.id} className="flex items-center justify-between text-xs py-1 border-b border-border/40 last:border-0">
                                        <span className="font-semibold text-text-secondary">{col.header}</span>
                                        <span className="font-medium text-text-primary">
                                            {col.cell ? col.cell({ row: item, value: val, index }) : val}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    );
                })}
            </div>

            {/* Pagination Controls */}
            {totalItems > pageSize && onPageChange && (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-2 py-3 bg-card border border-border rounded-xl">
                    <div className="text-xs text-text-secondary">
                        {t('common.showing_results', 'عرض {{from}} إلى {{to}} من أصل {{total}} سجل', {
                            from: (page - 1) * pageSize + 1,
                            to: Math.min(page * pageSize, totalItems),
                            total: totalItems,
                        })}
                    </div>

                    <div className="flex items-center gap-1">
                        <button
                            type="button"
                            onClick={() => onPageChange(page - 1)}
                            disabled={!canPrev}
                            className="p-1.5 rounded-lg border border-border bg-card text-text-primary hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                            aria-label={t('common.prev_page', 'الصفحة السابقة')}
                        >
                            <ChevronLeft className="w-4 h-4 rtl:rotate-180" aria-hidden="true" />
                        </button>

                        <span className="px-3 py-1 text-xs font-bold text-text-primary" aria-live="polite">
                            {page} / {totalPages}
                        </span>

                        <button
                            type="button"
                            onClick={() => onPageChange(page + 1)}
                            disabled={!canNext}
                            className="p-1.5 rounded-lg border border-border bg-card text-text-primary hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                            aria-label={t('common.next_page', 'الصفحة التالية')}
                        >
                            <ChevronRight className="w-4 h-4 rtl:rotate-180" aria-hidden="true" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
