import { useRef, useState } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    flexRender,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ChevronUp, ChevronDown, ChevronsUpDown, Search, LayoutGrid } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const VirtualizedBody = ({ rows, containerRef, onRowClick }) => {
    const rowVirtualizer = useVirtualizer({
        count: rows.length,
        getScrollElement: () => containerRef.current,
        estimateSize: () => 56,
        overscan: 10,
    });

    const virtualRows = rowVirtualizer.getVirtualItems();
    const totalSize = rowVirtualizer.getTotalSize();
    const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start || 0 : 0;
    const paddingBottom = virtualRows.length > 0
        ? totalSize - (virtualRows[virtualRows.length - 1]?.end || 0)
        : 0;

    return (
        <>
            {paddingTop > 0 && <tr><td style={{ height: `${paddingTop}px` }} /></tr>}
            {virtualRows.map((virtualRow) => {
                const row = rows[virtualRow.index];
                return (
                    <tr
                        key={row.id}
                        onClick={() => onRowClick?.(row.original)}
                        className={`group/row relative border-b border-border/50 transition-colors last:border-0 hover:bg-slate-50 dark:hover:bg-white/5 ${onRowClick ? 'cursor-pointer' : ''}`}
                    >
                        {row.getVisibleCells().map((cell) => (
                            <td key={cell.id} className="p-4 text-sm text-slate-700 dark:text-slate-300">
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                        ))}
                    </tr>
                );
            })}
            {paddingBottom > 0 && <tr><td style={{ height: `${paddingBottom}px` }} /></tr>}
        </>
    );
};

const StandardBody = ({ rows, onRowClick }) => (
    <>
        {rows.map((row) => (
            <tr
                key={row.id}
                onClick={() => onRowClick?.(row.original)}
                className={`group/row relative border-b border-border/50 transition-colors last:border-0 hover:bg-slate-50 dark:hover:bg-white/5 ${onRowClick ? 'cursor-pointer' : ''}`}
            >
                {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="p-4 text-sm text-slate-700 dark:text-slate-300">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                ))}
            </tr>
        ))}
    </>
);

const AdvancedTable = ({
    data = [],
    columns = [],
    isLoading = false,
    emptyMessage,
    onRowClick,
    enableVirtualization = false,
    pagination = true,
    pageSize = 10,
    className = '',
    title,
    actions,
    mobileCards = true,
}) => {
    const { t } = useTranslation();
    const [sorting, setSorting] = useState([]);
    const [globalFilter, setGlobalFilter] = useState('');
    const [columnVisibility, setColumnVisibility] = useState({});

    const table = useReactTable({
        data,
        columns,
        state: { sorting, globalFilter, columnVisibility },
        onSortingChange: setSorting,
        onGlobalFilterChange: setGlobalFilter,
        onColumnVisibilityChange: setColumnVisibility,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: pagination ? getPaginationRowModel() : undefined,
        initialState: { pagination: { pageSize } },
    });

    const { rows } = table.getRowModel();
    const tableContainerRef = useRef(null);

    const renderMobileHeader = (cell) => {
        const header = table.getFlatHeaders().find(item => item.column.id === cell.column.id);
        if (!header) return cell.column.id;
        return flexRender(header.column.columnDef.header, header.getContext());
    };

    return (
        <div className={`flex min-w-0 flex-col gap-4 ${className}`}>
            <div className="flex min-w-0 flex-col gap-3 md:flex-row md:items-center md:justify-between md:gap-4">
                {title && (
                    <h3 className="min-w-0 break-words text-lg font-extrabold tracking-tight text-slate-800 dark:text-white">
                        {title}
                    </h3>
                )}
                <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center md:max-w-md">
                    <div className="relative min-w-0 flex-1">
                        <Search className="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-slate-500 dark:text-slate-400" size={18} aria-hidden="true" />
                        <input
                            type="search"
                            value={globalFilter ?? ''}
                            onChange={(event) => setGlobalFilter(event.target.value)}
                            placeholder={t('common.search', 'Search...')}
                            className="min-h-11 w-full rounded-xl border border-border bg-surface py-2 ps-3 pe-10 text-sm outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20 dark:bg-white/5 sm:ps-4"
                        />
                    </div>
                    {actions && <div className="flex min-w-0 flex-wrap items-center gap-2 [&>*]:min-h-11">{actions}</div>}
                </div>
            </div>

            {mobileCards && (
                <div className="grid gap-3 md:hidden">
                    {isLoading ? (
                        Array.from({ length: 4 }).map((_, index) => (
                            <div key={index} className="rounded-2xl border border-border bg-surface-elevated p-3 shadow-low animate-pulse">
                                <div className="mb-3 h-4 w-1/2 rounded-full bg-slate-100 dark:bg-slate-800" />
                                <div className="space-y-2">
                                    <div className="h-10 rounded-xl bg-slate-100 dark:bg-slate-800" />
                                    <div className="h-10 rounded-xl bg-slate-100 dark:bg-slate-800" />
                                </div>
                            </div>
                        ))
                    ) : rows.length > 0 ? (
                        rows.map((row) => (
                            <article
                                key={row.id}
                                onClick={() => onRowClick?.(row.original)}
                                onKeyDown={(event) => {
                                    if (onRowClick && (event.key === 'Enter' || event.key === ' ')) {
                                        event.preventDefault();
                                        onRowClick(row.original);
                                    }
                                }}
                                role={onRowClick ? 'button' : undefined}
                                tabIndex={onRowClick ? 0 : undefined}
                                className={`min-w-0 rounded-2xl border border-border bg-surface-elevated p-3 shadow-low sm:p-4 ${onRowClick ? 'cursor-pointer focus-visible:ring-focus' : ''}`}
                            >
                                <dl className="divide-y divide-border/70">
                                    {row.getVisibleCells().map((cell) => (
                                        <div key={cell.id} className="grid min-w-0 grid-cols-[minmax(5.5rem,0.8fr)_minmax(0,1.2fr)] items-start gap-2 py-2.5 first:pt-0 last:pb-0">
                                            <dt className="min-w-0 break-words text-[11px] font-bold uppercase tracking-wide text-text-muted">
                                                {renderMobileHeader(cell)}
                                            </dt>
                                            <dd className="min-w-0 break-words text-end text-sm text-text-primary [&_button]:min-h-11 [&_a]:min-h-11 [&_select]:min-h-11">
                                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                            </dd>
                                        </div>
                                    ))}
                                </dl>
                            </article>
                        ))
                    ) : (
                        <div className="rounded-2xl border border-border bg-surface-elevated p-8 text-center">
                            <div className="mx-auto mb-3 inline-flex h-14 w-14 items-center justify-center rounded-full bg-slate-50 text-slate-300 dark:bg-white/5">
                                <LayoutGrid size={28} aria-hidden="true" />
                            </div>
                            <p className="font-bold text-slate-500">{emptyMessage || t('common.no_data', 'No data available')}</p>
                        </div>
                    )}
                </div>
            )}

            <div className={`${mobileCards ? 'hidden md:flex' : 'flex'} min-w-0 flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-sm dark:bg-slate-900/50`}>
                <div
                    ref={tableContainerRef}
                    className={`relative overflow-x-auto overscroll-x-contain ${enableVirtualization ? 'max-h-[600px] overflow-y-auto' : ''}`}
                >
                    <table className="w-full min-w-max border-collapse text-start">
                        <thead className="sticky top-0 z-10 border-b border-border bg-slate-50/95 backdrop-blur-md dark:bg-slate-800/95">
                            {table.getHeaderGroups().map((headerGroup) => (
                                <tr key={headerGroup.id}>
                                    {headerGroup.headers.map((header) => (
                                        <th
                                            key={header.id}
                                            className="select-none p-4 text-start text-xs font-bold uppercase tracking-widest text-slate-500"
                                        >
                                            <button
                                                type="button"
                                                onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
                                                disabled={!header.column.getCanSort()}
                                                className={`flex min-h-11 items-center gap-2 rounded-lg text-start ${header.column.getCanSort() ? 'cursor-pointer transition-colors hover:text-primary' : 'cursor-default'}`}
                                            >
                                                {flexRender(header.column.columnDef.header, header.getContext())}
                                                {header.column.getCanSort() && (
                                                    <span className="text-slate-300" aria-hidden="true">
                                                        {{ asc: <ChevronUp size={14} />, desc: <ChevronDown size={14} /> }[header.column.getIsSorted()] ?? <ChevronsUpDown size={14} opacity={0.3} />}
                                                    </span>
                                                )}
                                            </button>
                                        </th>
                                    ))}
                                </tr>
                            ))}
                        </thead>
                        <tbody>
                            {isLoading ? (
                                Array.from({ length: 5 }).map((_, index) => (
                                    <tr key={index} className="border-b border-border/50 animate-pulse">
                                        {columns.map((_, columnIndex) => (
                                            <td key={columnIndex} className="p-4">
                                                <div className="h-4 w-full rounded-full bg-slate-100 dark:bg-slate-800" />
                                            </td>
                                        ))}
                                    </tr>
                                ))
                            ) : enableVirtualization ? (
                                <VirtualizedBody rows={rows} containerRef={tableContainerRef} onRowClick={onRowClick} />
                            ) : (
                                <StandardBody rows={rows} onRowClick={onRowClick} />
                            )}
                        </tbody>
                    </table>

                    {!isLoading && rows.length === 0 && (
                        <div className="p-12 text-center">
                            <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-slate-50 text-slate-300 dark:bg-white/5">
                                <LayoutGrid size={32} aria-hidden="true" />
                            </div>
                            <p className="font-bold text-slate-500">{emptyMessage || t('common.no_data', 'No data available')}</p>
                        </div>
                    )}
                </div>
            </div>

            {pagination && rows.length > 0 && (
                <div className="flex min-w-0 flex-col gap-3 rounded-xl border border-border bg-slate-50/50 p-3 dark:bg-white/5 sm:flex-row sm:items-center sm:justify-between sm:p-4">
                    <span className="text-center text-xs font-bold text-slate-500 sm:text-start">
                        {t('common.page', 'Page')} {table.getState().pagination.pageIndex + 1} {t('common.of', 'of')} {table.getPageCount()}
                    </span>
                    <div className="grid grid-cols-2 gap-2 sm:flex">
                        <button
                            type="button"
                            onClick={() => table.previousPage()}
                            disabled={!table.getCanPreviousPage()}
                            className="min-h-11 rounded-xl border border-border bg-white px-3 py-2 text-xs font-bold uppercase tracking-wider transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-800"
                        >
                            {t('common.previous', 'Prev')}
                        </button>
                        <button
                            type="button"
                            onClick={() => table.nextPage()}
                            disabled={!table.getCanNextPage()}
                            className="min-h-11 rounded-xl border border-border bg-white px-3 py-2 text-xs font-bold uppercase tracking-wider transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-800"
                        >
                            {t('common.next', 'Next')}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdvancedTable;
