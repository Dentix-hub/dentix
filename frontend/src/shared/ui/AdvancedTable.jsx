import React, { useRef, useState } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    flexRender,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { 
    ChevronUp, ChevronDown, ChevronsUpDown, Search, LayoutGrid 
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

/**
 * Virtualized table body — only mounted when enableVirtualization is true.
 * Extracted into its own component so useVirtualizer is not called unconditionally.
 */
const VirtualizedBody = ({ rows, containerRef, onRowClick, columns }) => {
    const rowVirtualizer = useVirtualizer({
        count: rows.length,
        getScrollElement: () => containerRef.current,
        estimateSize: () => 56,
        overscan: 10,
    });

    const virtualRows = rowVirtualizer.getVirtualItems();
    const totalSize = rowVirtualizer.getTotalSize();
    const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start || 0 : 0;
    const paddingBottom =
        virtualRows.length > 0
            ? totalSize - (virtualRows[virtualRows.length - 1]?.end || 0)
            : 0;

    return (
        <>
            {paddingTop > 0 && (
                <tr><td style={{ height: `${paddingTop}px` }} /></tr>
            )}
            {virtualRows.map((virtualRow) => {
                const row = rows[virtualRow.index];
                return (
                    <tr
                        key={row.id}
                        onClick={() => onRowClick?.(row.original)}
                        className={`
                            group/row relative border-b border-border/50 last:border-0 hover:bg-slate-50 dark:hover:bg-white/5 transition-all
                            ${onRowClick ? 'cursor-pointer' : ''}
                        `}
                    >
                        {row.getVisibleCells().map((cell) => (
                            <td key={cell.id} className="p-4 text-sm text-slate-700 dark:text-slate-300">
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                        ))}
                    </tr>
                );
            })}
            {paddingBottom > 0 && (
                <tr><td style={{ height: `${paddingBottom}px` }} /></tr>
            )}
        </>
    );
};

/**
 * Standard (non-virtualized) table body.
 */
const StandardBody = ({ rows, onRowClick }) => (
    <>
        {rows.map((row) => (
            <tr
                key={row.id}
                onClick={() => onRowClick?.(row.original)}
                className={`
                    group/row relative border-b border-border/50 last:border-0 hover:bg-slate-50 dark:hover:bg-white/5 transition-all
                    ${onRowClick ? 'cursor-pointer' : ''}
                `}
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
    className = "",
    title,
    actions
}) => {
    const { t } = useTranslation();
    const [sorting, setSorting] = useState([]);
    const [globalFilter, setGlobalFilter] = useState('');
    const [columnVisibility, setColumnVisibility] = useState({});

    const table = useReactTable({
        data,
        columns,
        state: {
            sorting,
            globalFilter,
            columnVisibility,
        },
        onSortingChange: setSorting,
        onGlobalFilterChange: setGlobalFilter,
        onColumnVisibilityChange: setColumnVisibility,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: pagination ? getPaginationRowModel() : undefined,
        initialState: {
            pagination: {
                pageSize: pageSize,
            },
        },
    });

    const { rows } = table.getRowModel();
    const tableContainerRef = useRef(null);

    return (
        <div className={`flex flex-col gap-4 ${className}`}>
            {/* Table Header / Toolbar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                {title && (
                    <h3 className="text-lg font-extrabold text-slate-800 dark:text-white tracking-tight">
                        {title}
                    </h3>
                )}
                <div className="flex items-center gap-3 flex-1 md:max-w-md">
                    <div className="relative flex-1">
                        <Search className="absolute end-3 top-1/2 -translate-y-1/2 text-slate-500 dark:text-slate-400" size={18} />
                        <input
                            type="text"
                            value={globalFilter ?? ''}
                            onChange={(e) => setGlobalFilter(e.target.value)}
                            placeholder={t('common.search', 'Search...')}
                            className="w-full pe-10 ps-4 py-2 bg-surface dark:bg-white/5 border border-border rounded-xl text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-all outline-none"
                        />
                    </div>
                    {actions && <div className="flex items-center gap-2">{actions}</div>}
                </div>
            </div>

            {/* Table Body */}
            <div className="bg-surface dark:bg-slate-900/50 rounded-2xl border border-border shadow-sm overflow-hidden flex flex-col">
                <div 
                    ref={tableContainerRef}
                    className={`overflow-x-auto relative ${enableVirtualization ? 'max-h-[600px] overflow-y-auto' : ''}`}
                >
                    <table className="w-full text-right border-collapse">
                        <thead className="sticky top-0 z-10 bg-slate-50/80 dark:bg-slate-800/80 backdrop-blur-md border-b border-border">
                            {table.getHeaderGroups().map((headerGroup) => (
                                <tr key={headerGroup.id}>
                                    {headerGroup.headers.map((header) => (
                                        <th
                                            key={header.id}
                                            className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest cursor-pointer select-none group"
                                            onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
                                        >
                                            <div className="flex items-center gap-2">
                                                {flexRender(header.column.columnDef.header, header.getContext())}
                                                {header.column.getCanSort() && (
                                                    <span className="text-slate-300 group-hover:text-primary transition-colors">
                                                        {{
                                                            asc: <ChevronUp size={14} />,
                                                            desc: <ChevronDown size={14} />,
                                                        }[header.column.getIsSorted()] ?? <ChevronsUpDown size={14} opacity={0.3} />}
                                                    </span>
                                                )}
                                            </div>
                                        </th>
                                    ))}
                                </tr>
                            ))}
                        </thead>
                        <tbody>
                            {isLoading ? (
                                Array.from({ length: 5 }).map((_, i) => (
                                    <tr key={i} className="animate-pulse border-b border-border/50">
                                        {columns.map((_, j) => (
                                            <td key={j} className="p-4">
                                                <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded-full w-full" />
                                            </td>
                                        ))}
                                    </tr>
                                ))
                            ) : enableVirtualization ? (
                                <VirtualizedBody
                                    rows={rows}
                                    containerRef={tableContainerRef}
                                    onRowClick={onRowClick}
                                    columns={columns}
                                />
                            ) : (
                                <StandardBody rows={rows} onRowClick={onRowClick} />
                            )}
                        </tbody>
                    </table>

                    {!isLoading && rows.length === 0 && (
                        <div className="p-12 text-center">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-50 dark:bg-white/5 text-slate-300 mb-4">
                                <LayoutGrid size={32} />
                            </div>
                            <p className="text-slate-500 font-bold">
                                {emptyMessage || t('common.no_data', 'No data available')}
                            </p>
                        </div>
                    )}
                </div>

                {/* Pagination */}
                {pagination && rows.length > 0 && (
                    <div className="p-4 bg-slate-50/50 dark:bg-white/5 border-t border-border flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-500">
                                {t('common.page', 'Page')} {table.getState().pagination.pageIndex + 1} {t('common.of', 'of')} {table.getPageCount()}
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => table.previousPage()}
                                disabled={!table.getCanPreviousPage()}
                                className="px-3 py-1 text-xs font-bold uppercase tracking-widest bg-white dark:bg-slate-800 border border-border rounded-lg disabled:opacity-50 transition-all hover:bg-slate-50"
                            >
                                {t('common.previous', 'Prev')}
                            </button>
                            <button
                                onClick={() => table.nextPage()}
                                disabled={!table.getCanNextPage()}
                                className="px-3 py-1 text-xs font-bold uppercase tracking-widest bg-white dark:bg-slate-800 border border-border rounded-lg disabled:opacity-50 transition-all hover:bg-slate-50"
                            >
                                {t('common.next', 'Next')}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AdvancedTable;
