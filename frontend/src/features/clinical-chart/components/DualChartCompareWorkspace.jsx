import { useCallback, useMemo, useState } from 'react';
import ClinicalChartRenderer from './ClinicalChartRenderer';
import { DENTAL_ANATOMY_REGISTRY, DENTITIONS } from '../domain/dentalAnatomyRegistry';
import {
    CARIES_ON_SURFACE_FIXTURE,
    CLINICAL_DEMO_FIXTURES,
    MOD_RESTORATION_FIXTURE,
} from '../fixtures/demoProjectionFixtures';
import {
    CHART_INTERACTION_MODES,
    CHART_INTENT_TYPES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';

export default function DualChartCompareWorkspace({
    defaultFixtureA = CARIES_ON_SURFACE_FIXTURE,
    defaultFixtureB = MOD_RESTORATION_FIXTURE,
    initialReadOnly = false,
}) {
    // Chart A state (Left: Visit A / Historical)
    const [fixtureKeyA, setFixtureKeyA] = useState('cariesOnSurface');
    const [selectionA, setSelectionA] = useState(null);
    const [layersA, setLayersA] = useState({ roots: true, surfaces: true });
    const [readOnlyA, setReadOnlyA] = useState(initialReadOnly);

    // Chart B state (Right: Visit B / Current & Plan)
    const [fixtureKeyB, setFixtureKeyB] = useState('modRestoration');
    const [selectionB, setSelectionB] = useState(null);
    const [layersB, setLayersB] = useState({ roots: true, surfaces: true });
    const [readOnlyB, setReadOnlyB] = useState(initialReadOnly);

    const activeFixtureA = CLINICAL_DEMO_FIXTURES[fixtureKeyA] || defaultFixtureA;
    const activeFixtureB = CLINICAL_DEMO_FIXTURES[fixtureKeyB] || defaultFixtureB;

    const handleIntentA = useCallback((intent) => {
        if (intent.type !== CHART_INTENT_TYPES.SURFACE_SELECTED) return;
        setSelectionA((current) => (
            current?.kind === 'surface'
            && current.toothKey === intent.target.toothKey
            && current.surfaceCode === intent.target.surfaceCode
                ? null
                : intent.target
        ));
    }, []);

    const handleIntentB = useCallback((intent) => {
        if (intent.type !== CHART_INTENT_TYPES.SURFACE_SELECTED) return;
        setSelectionB((current) => (
            current?.kind === 'surface'
            && current.toothKey === intent.target.toothKey
            && current.surfaceCode === intent.target.surfaceCode
                ? null
                : intent.target
        ));
    }, []);

    const rendererInputA = useMemo(() => createClinicalChartRendererInput({
        chartId: 'dual-chart-instance-a',
        anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
        dentition: activeFixtureA.dentition || DENTITIONS.PERMANENT,
        visualState: {
            ...activeFixtureA,
            selection: selectionA,
        },
        notationMode: CHART_NOTATION_MODES.PALMER,
        interactionMode: readOnlyA ? CHART_INTERACTION_MODES.READ_ONLY : CHART_INTERACTION_MODES.EDIT,
        layers: layersA,
        callbacks: {
            onIntent: handleIntentA,
        },
    }), [activeFixtureA, handleIntentA, layersA, readOnlyA, selectionA]);

    const rendererInputB = useMemo(() => createClinicalChartRendererInput({
        chartId: 'dual-chart-instance-b',
        anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
        dentition: activeFixtureB.dentition || DENTITIONS.PERMANENT,
        visualState: {
            ...activeFixtureB,
            selection: selectionB,
        },
        notationMode: CHART_NOTATION_MODES.PALMER,
        interactionMode: readOnlyB ? CHART_INTERACTION_MODES.READ_ONLY : CHART_INTERACTION_MODES.EDIT,
        layers: layersB,
        callbacks: {
            onIntent: handleIntentB,
        },
    }), [activeFixtureB, handleIntentB, layersB, readOnlyB, selectionB]);

    return (
        <section className="space-y-6" data-testid="dual-chart-compare-workspace">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                <div className="flex flex-col gap-2 border-b border-slate-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-800">
                            مقارنة السجل والمخططات السريرية (Dual-Chart History Compare)
                        </h2>
                        <p className="text-sm text-slate-500">
                            مقارنة تاريخية جنباً إلى جنب مع عزل تام لحالة المخططين وتصفية مستقلة للطبقات
                        </p>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                        <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800">
                            عزل كامل (State Isolated)
                        </span>
                        <span className="rounded-full bg-blue-100 px-3 py-1 text-blue-800">
                            تصفية مستقلة (Independent Layers)
                        </span>
                    </div>
                </div>

                <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-2">
                    {/* CHART A: Left / History */}
                    <div
                        className="flex flex-col rounded-2xl border border-slate-200 bg-slate-50/50 p-4 shadow-sm"
                        data-testid="dual-chart-panel-a"
                    >
                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
                            <div>
                                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                    المخطط الأول (Instance A)
                                </span>
                                <h3 className="text-base font-bold text-slate-700">
                                    الزيارة السابقة / التشخيص الأولي
                                </h3>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                                <select
                                    aria-label="Select scenario for Chart A"
                                    className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm focus:border-primary focus:outline-none"
                                    data-testid="select-fixture-a"
                                    onChange={(e) => setFixtureKeyA(e.target.value)}
                                    value={fixtureKeyA}
                                >
                                    <option value="cariesOnSurface">تسوس سطحي (Caries on surface)</option>
                                    <option value="adultDentition">أسنان طبيعية (Adult baseline)</option>
                                    <option value="primaryDentition">أسنان أطفال (Primary)</option>
                                    <option value="mixedDentition">أسنان مختلطة (Mixed)</option>
                                    <option value="rct">علاج جذور (RCT)</option>
                                    <option value="extractionPlanned">خلع مخطط (Planned extraction)</option>
                                </select>

                                <button
                                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${layersA.roots ? 'bg-indigo-600 text-white shadow-xs' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'}`}
                                    data-testid="toggle-roots-a"
                                    onClick={() => setLayersA((prev) => ({ ...prev, roots: !prev.roots }))}
                                    type="button"
                                >
                                    الجذور: {layersA.roots ? 'ظاهرة' : 'مخفية'}
                                </button>

                                <button
                                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${layersA.surfaces ? 'bg-blue-600 text-white shadow-xs' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'}`}
                                    data-testid="toggle-surfaces-a"
                                    onClick={() => setLayersA((prev) => ({ ...prev, surfaces: !prev.surfaces }))}
                                    type="button"
                                >
                                    الأسطح: {layersA.surfaces ? 'مفعلة' : 'معطلة'}
                                </button>

                                <button
                                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${readOnlyA ? 'bg-amber-600 text-white shadow-xs' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'}`}
                                    data-testid="toggle-readonly-a"
                                    onClick={() => setReadOnlyA((prev) => !prev)}
                                    type="button"
                                >
                                    {readOnlyA ? 'قراءة فقط' : 'تفاعلي'}
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-x-auto">
                            <ClinicalChartRenderer input={rendererInputA} />
                        </div>
                    </div>

                    {/* CHART B: Right / Current & Plan */}
                    <div
                        className="flex flex-col rounded-2xl border border-slate-200 bg-slate-50/50 p-4 shadow-sm"
                        data-testid="dual-chart-panel-b"
                    >
                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
                            <div>
                                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                    المخطط الثاني (Instance B)
                                </span>
                                <h3 className="text-base font-bold text-slate-700">
                                    الزيارة الحالية / خطة العلاج المنجزة
                                </h3>
                            </div>

                            <div className="flex flex-wrap items-center gap-2">
                                <select
                                    aria-label="Select scenario for Chart B"
                                    className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm focus:border-primary focus:outline-none"
                                    data-testid="select-fixture-b"
                                    onChange={(e) => setFixtureKeyB(e.target.value)}
                                    value={fixtureKeyB}
                                >
                                    <option value="modRestoration">حشوة مركبة MOD (Restoration)</option>
                                    <option value="crown">تركيب تاج (Crown)</option>
                                    <option value="bridge">تركيب جسر (Bridge)</option>
                                    <option value="implant">زراعة سنية (Implant)</option>
                                    <option value="rct">علاج جذور منجز (RCT)</option>
                                    <option value="extractionCompleted">سن مخلوع (Extracted)</option>
                                </select>

                                <button
                                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${layersB.roots ? 'bg-indigo-600 text-white shadow-xs' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'}`}
                                    data-testid="toggle-roots-b"
                                    onClick={() => setLayersB((prev) => ({ ...prev, roots: !prev.roots }))}
                                    type="button"
                                >
                                    الجذور: {layersB.roots ? 'ظاهرة' : 'مخفية'}
                                </button>

                                <button
                                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${layersB.surfaces ? 'bg-blue-600 text-white shadow-xs' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'}`}
                                    data-testid="toggle-surfaces-b"
                                    onClick={() => setLayersB((prev) => ({ ...prev, surfaces: !prev.surfaces }))}
                                    type="button"
                                >
                                    الأسطح: {layersB.surfaces ? 'مفعلة' : 'معطلة'}
                                </button>

                                <button
                                    className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${readOnlyB ? 'bg-amber-600 text-white shadow-xs' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'}`}
                                    data-testid="toggle-readonly-b"
                                    onClick={() => setReadOnlyB((prev) => !prev)}
                                    type="button"
                                >
                                    {readOnlyB ? 'قراءة فقط' : 'تفاعلي'}
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-x-auto">
                            <ClinicalChartRenderer input={rendererInputB} />
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
