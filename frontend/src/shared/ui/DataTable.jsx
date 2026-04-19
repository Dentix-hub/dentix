/**
 * DataTable Component
 * Reusable table with empty state support.
 */

export default function DataTable({
    columns,
    data,
    emptyMessage = 'لا توجد بيانات',
    className = ''
}) {
    return (
        <div className={`bg-surface rounded-2xl border border-border overflow-hidden shadow-sm ${className}`}>
            <div className="overflow-x-auto">
                <table className="w-full text-right align-middle">
                    <thead className="bg-surface-hover text-text-secondary text-sm font-bold uppercase tracking-wider">
                        <tr>
                            {(columns || []).map((col, idx) => (
                                <th
                                    key={idx}
                                    className={`p-4 whitespace-nowrap ${col.className || ''}`}
                                >
                                    {col.header}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                        {(data || []).map((row, rowIdx) => (
                            <tr key={row.id || rowIdx} className="hover:bg-surface-hover transition-colors text-text-secondary">
                                {(columns || []).map((col, colIdx) => (
                                    <td
                                        key={colIdx}
                                        className={`p-4 ${col.cellClassName || ''}`}
                                    >
                                        {col.render ? col.render(row[col.accessor], row) : row[col.accessor]}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {(data || []).length === 0 && (
                <div className="p-8 text-center text-text-secondary">{emptyMessage}</div>
            )}
        </div>
    );
}
