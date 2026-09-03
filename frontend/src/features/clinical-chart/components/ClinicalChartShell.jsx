import { useCallback, useMemo, useState } from 'react';
import ClinicalChartRenderer from './ClinicalChartRenderer';
import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
    TOOTH_TYPES,
} from '../domain/dentalAnatomyRegistry';
import {
    CHART_NOTATION_MODES,
    NOTATION_MODE_LABELS,
    formatToothLabel,
} from '../domain/toothNotation';
import { getSurfaceGeometry } from '../rendering/surfaceGeometry';
import {
    CHART_INTERACTION_MODES,
    CHART_INTENT_TYPES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';
import { TARGET_COVERAGE_PROJECTION } from '../fixtures/demoProjectionFixtures';

const TOOTH_FAMILY_NAMES = Object.freeze({
    [TOOTH_TYPES.INCISOR]: 'قاطع (Incisor)',
    [TOOTH_TYPES.CANINE]: 'ناب (Canine)',
    [TOOTH_TYPES.PREMOLAR]: 'ضاحك (Premolar)',
    [TOOTH_TYPES.MOLAR]: 'طاحن (Molar)',
});

const ARCH_NAMES = Object.freeze({
    maxillary: 'الفك العلوي (Maxillary)',
    mandibular: 'الفك السفلي (Mandibular)',
});

const SIDE_NAMES = Object.freeze({
    right: 'الأيمن (Right)',
    left: 'الأيسر (Left)',
});

export function ClinicalChartLegend() {
    const legendItems = [
        { label: 'تسوس سريري (Caries)', color: 'border-red-500 bg-red-50 text-red-700', badge: '● تسوس' },
        { label: 'حشوة مركبة (Composite)', color: 'border-blue-500 bg-blue-50 text-blue-700', badge: '■ حشوة' },
        { label: 'علاج جذور (RCT)', color: 'border-purple-500 bg-purple-50 text-purple-700', badge: '▲ قناة عصب' },
        { label: 'تاج تركيبي (Crown)', color: 'border-amber-500 bg-amber-50 text-amber-700', badge: '◆ تاج' },
        { label: 'جسر أسنان (Bridge)', color: 'border-amber-600 bg-amber-100 text-amber-800', badge: '▬ جسر' },
        { label: 'زراعة سنية (Implant)', color: 'border-teal-500 bg-teal-50 text-teal-700', badge: '✦ زرعة' },
        { label: 'خلع مخطط (Planned Extract)', color: 'border-blue-400 border-dashed bg-blue-50 text-blue-800', badge: '✖ مخطط' },
        { label: 'سن مخلوع / مفقود (Missing)', color: 'border-slate-400 bg-slate-100 text-slate-600', badge: '✕ مفقود' },
    ];

    return (
        <div
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs"
            data-testid="clinical-chart-legend"
        >
            <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    دليل الرموز والقواعد البصرية (Clinical Visual Legend)
                </h4>
                <span className="text-[11px] text-slate-400">ترميز موحد</span>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {legendItems.map((item) => (
                    <div
                        className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs font-medium ${item.color}`}
                        key={item.label}
                    >
                        <span className="shrink-0 text-xs font-bold">{item.badge}</span>
                        <span className="truncate">{item.label}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

export function ClinicalChartInspector({
    selection,
    projection,
    notationMode = CHART_NOTATION_MODES.PALMER,
    anatomyRegistry = DENTAL_ANATOMY_REGISTRY,
    onClearSelection,
}) {
    const selectedToothKey = selection?.toothKey;
    const anatomy = selectedToothKey ? anatomyRegistry[selectedToothKey] : null;
    const toothVisualState = selectedToothKey ? projection?.teeth?.[selectedToothKey] : null;

    if (!selectedToothKey || !anatomy) {
        return (
            <div
                className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center text-slate-400"
                data-testid="clinical-chart-inspector"
            >
                <div className="mb-2 text-2xl">🦷</div>
                <h4 className="text-sm font-semibold text-slate-600">لوحة فحص الأسنان (Inspector)</h4>
                <p className="mt-1 text-xs text-slate-400">
                    انقر على أي سن أو سطح في المخطط لعرض تشريحه الدقيق وإجراءاته السريرية
                </p>
            </div>
        );
    }

    const surfaceGeometry = getSurfaceGeometry(selectedToothKey);
    const selectedSurface = selection.kind === 'surface'
        ? surfaceGeometry.surfaces.find((s) => s.surfaceCode === selection.surfaceCode)
        : null;

    const palmerLabel = formatToothLabel(selectedToothKey, { notationMode: CHART_NOTATION_MODES.PALMER });
    const fdiLabel = formatToothLabel(selectedToothKey, { notationMode: CHART_NOTATION_MODES.FDI });
    const universalLabel = formatToothLabel(selectedToothKey, { notationMode: CHART_NOTATION_MODES.UNIVERSAL });

    const findings = toothVisualState?.findings || [];
    const procedures = toothVisualState?.procedures || [];

    return (
        <div
            className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-xs"
            data-testid="clinical-chart-inspector"
        >
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                    <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-700">
                        FDI: {fdiLabel}
                    </span>
                    <span className="rounded-md bg-indigo-100 px-2 py-0.5 text-xs font-bold text-indigo-700">
                        Palmer: {palmerLabel}
                    </span>
                    <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-700">
                        Univ: #{universalLabel}
                    </span>
                </div>
                {onClearSelection && (
                    <button
                        className="rounded-md px-2 py-1 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                        data-testid="inspector-clear-btn"
                        onClick={onClearSelection}
                        type="button"
                    >
                        إلغاء التحديد ✕
                    </button>
                )}
            </div>

            <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                <div>
                    <span className="block text-slate-400">التصنيف التشريحي:</span>
                    <strong className="text-slate-700">{TOOTH_FAMILY_NAMES[anatomy.toothType]}</strong>
                </div>
                <div>
                    <span className="block text-slate-400">الموقع والفك:</span>
                    <strong className="text-slate-700">
                        {ARCH_NAMES[anatomy.arch]} — {SIDE_NAMES[anatomy.side]}
                    </strong>
                </div>
                <div>
                    <span className="block text-slate-400">عدد الجذور التشريحية:</span>
                    <strong className="text-slate-700">{anatomy.rootCount}</strong>
                </div>
                <div>
                    <span className="block text-slate-400">العنصر المحدد:</span>
                    <strong className="text-blue-600">
                        {selectedSurface
                            ? `السطح ${selectedSurface.surfaceCode} (${selectedSurface.label})`
                            : 'السن بالكامل (Whole Tooth)'}
                    </strong>
                </div>
            </div>

            <div className="mt-4 border-t border-slate-100 pt-3">
                <span className="mb-1 block text-xs font-semibold text-slate-500">
                    التشخيصات والإجراءات السريرية المسجلة:
                </span>
                {findings.length === 0 && procedures.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">لا توجد إجراءات مسجلة على هذا السن (سليم)</p>
                ) : (
                    <div className="flex flex-wrap gap-1.5 mt-1">
                        {findings.map((f, i) => (
                            <span
                                className="rounded-md bg-red-50 border border-red-200 px-2 py-0.5 text-xs font-medium text-red-700"
                                key={f.visualId || i}
                            >
                                تشخيص: {f.code} {f.phase ? `(${f.phase})` : ''}
                            </span>
                        ))}
                        {procedures.map((p, i) => (
                            <span
                                className="rounded-md bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs font-medium text-blue-700"
                                key={p.visualId || i}
                            >
                                إجراء: {p.code} ({p.phase || 'active'})
                            </span>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export function ClinicalChartSelectionSummary({ selection, onClear }) {
    if (!selection) {
        return (
            <div
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500"
                data-testid="selection-summary-banner"
            >
                <span>لم يتم تحديد أي سن أو سطح — انقر على أي سن في المخطط لتحديده وفحصه</span>
            </div>
        );
    }

    const palmer = formatToothLabel(selection.toothKey, { notationMode: CHART_NOTATION_MODES.PALMER });
    const fdi = formatToothLabel(selection.toothKey, { notationMode: CHART_NOTATION_MODES.FDI });

    return (
        <div
            className="flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50/70 px-4 py-2 text-xs text-blue-900 shadow-2xs"
            data-testid="selection-summary-banner"
        >
            <div className="flex items-center gap-2">
                <span className="font-bold text-blue-700">السن المحدد:</span>
                <span className="rounded bg-white px-2 py-0.5 font-bold text-blue-800 shadow-2xs">
                    FDI: {fdi} ({palmer})
                </span>
                {selection.kind === 'surface' && (
                    <>
                        <span className="text-slate-400">|</span>
                        <span className="font-bold text-blue-700">السطح:</span>
                        <span className="rounded bg-white px-2 py-0.5 font-bold text-blue-800 shadow-2xs">
                            {selection.surfaceCode}
                        </span>
                    </>
                )}
            </div>

            {onClear && (
                <button
                    className="rounded-md bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 shadow-2xs hover:bg-slate-100 hover:text-slate-900"
                    data-testid="clear-selection-summary-btn"
                    onClick={onClear}
                    type="button"
                >
                    إلغاء التحديد ✕
                </button>
            )}
        </div>
    );
}

export default function ClinicalChartShell({
    projection = TARGET_COVERAGE_PROJECTION,
    initialNotationMode = CHART_NOTATION_MODES.PALMER,
    initialDentition = DENTITIONS.PERMANENT,
    initialLayers = { roots: true, surfaces: true },
    interactionMode = CHART_INTERACTION_MODES.EDIT,
}) {
    const [notationMode, setNotationMode] = useState(initialNotationMode);
    const [layers, setLayers] = useState(initialLayers);
    const [selection, setSelection] = useState(projection?.selection || null);

    const handleIntent = useCallback((intent) => {
        if (intent.type !== CHART_INTENT_TYPES.SURFACE_SELECTED) return;
        setSelection((current) => (
            current?.kind === 'surface'
            && current.toothKey === intent.target.toothKey
            && current.surfaceCode === intent.target.surfaceCode
                ? null
                : intent.target
        ));
    }, []);

    const clearSelection = useCallback(() => {
        setSelection(null);
    }, []);

    const rendererInput = useMemo(() => createClinicalChartRendererInput({
        chartId: 'clinical-chart-shell-view',
        anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
        dentition: initialDentition,
        visualState: {
            ...projection,
            selection,
        },
        notationMode,
        interactionMode,
        layers,
        callbacks: {
            onIntent: handleIntent,
        },
    }), [handleIntent, initialDentition, interactionMode, layers, notationMode, projection, selection]);

    return (
        <div
            className="flex flex-col gap-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
            data-testid="clinical-chart-shell"
        >
            {/* A14-M01: Shell Header Controls */}
            <header
                className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4"
                data-testid="chart-shell-header"
            >
                <div>
                    <h2 className="text-lg font-bold text-slate-800">
                        مخطط الأسنان السريري (Clinical Odontogram)
                    </h2>
                    <p className="text-xs text-slate-500">
                        عرض سريري دقيق مع إمكانية فحص التيجان، الأسطح، والجذور التشريحية
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {/* Notation Toggle */}
                    <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 p-1">
                        <span className="px-1.5 text-xs font-semibold text-slate-400">الترقيم:</span>
                        <select
                            aria-label="Notation mode"
                            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 shadow-2xs focus:border-primary focus:outline-none"
                            data-testid="shell-notation-select"
                            onChange={(e) => setNotationMode(e.target.value)}
                            value={notationMode}
                        >
                            <option value={CHART_NOTATION_MODES.PALMER}>
                                {NOTATION_MODE_LABELS[CHART_NOTATION_MODES.PALMER]}
                            </option>
                            <option value={CHART_NOTATION_MODES.FDI}>
                                {NOTATION_MODE_LABELS[CHART_NOTATION_MODES.FDI]}
                            </option>
                            <option value={CHART_NOTATION_MODES.UNIVERSAL}>
                                {NOTATION_MODE_LABELS[CHART_NOTATION_MODES.UNIVERSAL]}
                            </option>
                        </select>
                    </div>

                    {/* Layer Toggles */}
                    <button
                        className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${layers.roots ? 'bg-indigo-600 text-white shadow-2xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                        data-testid="shell-toggle-roots"
                        onClick={() => setLayers((prev) => ({ ...prev, roots: !prev.roots }))}
                        type="button"
                    >
                        الجذور: {layers.roots ? 'ظاهرة' : 'مخفية'}
                    </button>

                    <button
                        className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${layers.surfaces ? 'bg-blue-600 text-white shadow-2xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                        data-testid="shell-toggle-surfaces"
                        onClick={() => setLayers((prev) => ({ ...prev, surfaces: !prev.surfaces }))}
                        type="button"
                    >
                        الأسطح: {layers.surfaces ? 'مفعلة' : 'معطلة'}
                    </button>

                    {/* Clear selection control */}
                    <button
                        className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-2xs transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                        data-testid="shell-clear-selection"
                        disabled={!selection}
                        onClick={clearSelection}
                        type="button"
                    >
                        مسح التحديد
                    </button>
                </div>
            </header>

            {/* A14-M04: Selection Summary Bar */}
            <ClinicalChartSelectionSummary onClear={clearSelection} selection={selection} />

            {/* Chart Canvas */}
            <div className="overflow-x-auto rounded-xl border border-slate-100 bg-slate-50/30 p-2">
                <ClinicalChartRenderer input={rendererInput} />
            </div>

            {/* A14-M02 & A14-M03: Legend & Inspector Footer */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="lg:col-span-2">
                    <ClinicalChartLegend />
                </div>
                <div className="lg:col-span-1">
                    <ClinicalChartInspector
                        anatomyRegistry={DENTAL_ANATOMY_REGISTRY}
                        notationMode={notationMode}
                        onClearSelection={clearSelection}
                        projection={projection}
                        selection={selection}
                    />
                </div>
            </div>
        </div>
    );
}
