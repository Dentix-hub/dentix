export default function ClinicalChartInspector({ copy, title, selection, toothState }) {
    const hasSelection = Boolean(selection?.toothKey);
    const findingsCount = toothState?.findings?.length ?? 0;
    const proceduresCount = toothState?.procedures?.length ?? 0;

    return (
        <aside
            aria-label={title + ' - ' + copy.inspector}
            className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3"
            data-testid="clinical-chart-inspector"
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900">{copy.inspector}</h3>
                <span className="text-xs font-medium text-slate-500">{copy.previewOnly}</span>
            </div>
            <dl aria-live="polite" className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div>
                    <dt className="text-xs text-slate-500">{copy.selectedTooth}</dt>
                    <dd className="mt-1 font-bold text-slate-900">{hasSelection ? selection.toothKey : copy.none}</dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500">{copy.selectedSurface}</dt>
                    <dd className="mt-1 font-bold text-slate-900">
                        {selection?.surfaceCode ? copy.surfaces[selection.surfaceCode] : copy.none}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500">{copy.findings}</dt>
                    <dd className="mt-1 font-bold text-slate-900">{findingsCount}</dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500">{copy.procedures}</dt>
                    <dd className="mt-1 font-bold text-slate-900">{proceduresCount}</dd>
                </div>
            </dl>
        </aside>
    );
}
