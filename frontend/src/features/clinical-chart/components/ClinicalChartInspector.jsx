const SURFACE_LABELS = Object.freeze({
    M: 'Mesial (M)',
    D: 'Distal (D)',
    O: 'Occlusal (O)',
    I: 'Incisal (I)',
    B: 'Buccal (B)',
    L: 'Lingual (L)',
    P: 'Palatal (P)',
});

export default function ClinicalChartInspector({ title, selection, toothState }) {
    const hasSelection = Boolean(selection?.toothKey);
    const findingsCount = toothState?.findings?.length ?? 0;
    const proceduresCount = toothState?.procedures?.length ?? 0;

    return (
        <aside
            aria-label={title + ' inspector'}
            className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-3"
            data-testid="clinical-chart-inspector"
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-slate-900">Inspector</h3>
                <span className="text-xs font-medium text-slate-500">Preview only</span>
            </div>
            <dl aria-live="polite" className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div>
                    <dt className="text-xs text-slate-500">Selected tooth</dt>
                    <dd className="mt-1 font-bold text-slate-900">{hasSelection ? selection.toothKey : 'None'}</dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500">Selected surface</dt>
                    <dd className="mt-1 font-bold text-slate-900">
                        {selection?.surfaceCode ? SURFACE_LABELS[selection.surfaceCode] : 'None'}
                    </dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500">Findings</dt>
                    <dd className="mt-1 font-bold text-slate-900">{findingsCount}</dd>
                </div>
                <div>
                    <dt className="text-xs text-slate-500">Procedures</dt>
                    <dd className="mt-1 font-bold text-slate-900">{proceduresCount}</dd>
                </div>
            </dl>
        </aside>
    );
}
