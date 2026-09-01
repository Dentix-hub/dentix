const LEGEND_ITEMS = Object.freeze([
    Object.freeze({ label: 'Caries', color: '#b91c1c' }),
    Object.freeze({ label: 'Composite', color: '#2563eb' }),
    Object.freeze({ label: 'Endodontic therapy', color: '#7c3aed' }),
    Object.freeze({ label: 'Crown or bridge', color: '#ca8a04' }),
    Object.freeze({ label: 'Implant', color: '#0f766e' }),
    Object.freeze({ label: 'Missing tooth', color: '#64748b' }),
]);

export default function ClinicalChartWorkspaceShell() {
    return (
        <header className="mb-5 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <p className="text-sm font-semibold text-blue-700">Clinical chart</p>
                    <h1 className="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">
                        Odontogram comparison
                    </h1>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                        Compare the current projection with a historical snapshot without changing clinical data.
                    </p>
                </div>
                <span className="w-fit rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">
                    Read-only
                </span>
            </div>

            <div aria-label="Clinical chart legend" className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-100 pt-4" role="list">
                {LEGEND_ITEMS.map(({ label, color }) => (
                    <div className="flex items-center gap-2 text-sm text-slate-700" key={label} role="listitem">
                        <span aria-hidden="true" className="h-3 w-3 rounded-full border border-black/10" style={{ backgroundColor: color }} />
                        <span>{label}</span>
                    </div>
                ))}
            </div>
        </header>
    );
}
