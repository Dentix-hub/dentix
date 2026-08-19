/**
 * Reusable semantic table for straightforward data sets.
 * Sorting/filtering/pagination remain the responsibility of the capable
 * AdvancedTable path; this component intentionally does not invent features.
 */
export default function DataTable({
    columns,
    data,
    emptyMessage = 'لا توجد بيانات',
    className = '',
}) {
    return (
        <div className={`overflow-hidden rounded-card border border-border bg-surface-elevated shadow-low ${className}`}>
            <div className="overflow-x-auto">
                <table className="w-full text-start align-middle text-type-table">
                    <thead className="bg-surface-subtle text-text-secondary">
                        <tr>
                            {(columns || []).map((col, idx) => (
                                <th key={col.id || col.accessor || idx} className={`px-4 py-3 whitespace-nowrap font-semibold ${col.className || ''}`}>
                                    {col.header}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {(data || []).map((row, rowIdx) => (
                            <tr key={row.id || rowIdx} className="text-text-primary transition-colors duration-fast hover:bg-surface-subtle">
                                {(columns || []).map((col, colIdx) => (
                                    <td key={col.id || col.accessor || colIdx} className={`px-4 py-3 ${col.cellClassName || ''}`}>
                                        {col.render ? col.render(row[col.accessor], row) : row[col.accessor]}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {(data || []).length === 0 && (
                <div className="p-8 text-center text-type-body text-text-muted">{emptyMessage}</div>
            )}
        </div>
    );
}
