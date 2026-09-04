import { useMemo, useState } from 'react';
import { CheckCircle2, Info, LockKeyhole } from 'lucide-react';
import ApprovedClinicalToothRenderer from './ApprovedClinicalToothRenderer';
import { ADULT_FDI_ROWS } from './approvedArtwork';
import { hasProgrammaticToothEffect } from './programmaticToothEffects';
import { PROCEDURE_LIFECYCLE, PROCEDURE_TYPE } from './toothTypes';

const PROCEDURE_LABELS = Object.freeze({
    [PROCEDURE_TYPE.CARIES]: 'تسوس',
    [PROCEDURE_TYPE.COMPOSITE]: 'حشو تجميلي',
    [PROCEDURE_TYPE.AMALGAM]: 'حشو أملغم',
    [PROCEDURE_TYPE.RCT]: 'علاج عصب',
    [PROCEDURE_TYPE.CROWN]: 'تاج',
    [PROCEDURE_TYPE.IMPLANT]: 'زرعة',
    [PROCEDURE_TYPE.BRIDGE]: 'جسر',
    [PROCEDURE_TYPE.MISSING]: 'سن مفقود',
    [PROCEDURE_TYPE.FRACTURE]: 'كسر بالتاج',
});

const CLINICAL_OPTIONS = Object.freeze([
    { id: 'healthy', label: 'سليم', group: 'أساسي', procedure: null },
    { id: 'caries-o', label: 'تسوس إطباقي', group: 'حالة مرضية', procedure: { type: PROCEDURE_TYPE.CARIES, surfaces: ['O'] } },
    { id: 'composite-o', label: 'حشو تجميلي', group: 'إجراء', procedure: { type: PROCEDURE_TYPE.COMPOSITE, surfaces: ['O'] } },
    { id: 'amalgam-o', label: 'حشو أملغم', group: 'إجراء', procedure: { type: PROCEDURE_TYPE.AMALGAM, surfaces: ['O'] } },
    { id: 'rct', label: 'علاج عصب', group: 'إجراء', procedure: { type: PROCEDURE_TYPE.RCT } },
    { id: 'crown', label: 'تاج', group: 'إجراء', procedure: { type: PROCEDURE_TYPE.CROWN } },
    { id: 'implant', label: 'زرعة', group: 'إجراء', procedure: { type: PROCEDURE_TYPE.IMPLANT } },
    { id: 'missing', label: 'سن مفقود', group: 'حالة', procedure: { type: PROCEDURE_TYPE.MISSING } },
    { id: 'fracture', label: 'كسر بالتاج', group: 'حالة مرضية', procedure: { type: PROCEDURE_TYPE.FRACTURE } },
]);

function buildClinicalState(option) {
    if (!option?.procedure) return Object.freeze({ procedures: [] });
    return Object.freeze({
        procedures: [Object.freeze({
            ...option.procedure,
            surfaces: option.procedure.surfaces || [],
            lifecycle: PROCEDURE_LIFECYCLE.COMPLETED,
        })],
    });
}

function isOptionAvailable(fdi, option) {
    if (!option.procedure) return true;
    return hasProgrammaticToothEffect({ fdi, ...option.procedure });
}

function ToothButton({ fdi, selectedTooth, showPlanned, onSelect, chartState }) {
    const state = chartState[fdi] || { procedures: [] };

    return (
        <button
            type="button"
            onClick={() => onSelect(fdi)}
            aria-label={`اختيار السن ${fdi}`}
            aria-pressed={selectedTooth === fdi}
            className="min-w-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
        >
            <ApprovedClinicalToothRenderer
                fdi={fdi}
                state={state}
                showPlanned={showPlanned}
                selected={selectedTooth === fdi}
            />
        </button>
    );
}

function ArchRow({ teeth, selectedTooth, showPlanned, onSelect, label, chartState }) {
    return (
        <section
            aria-label={label}
            className="relative grid grid-cols-4 gap-1 sm:grid-cols-8 md:grid-cols-[repeat(16,minmax(0,1fr))] md:gap-1.5"
            dir="ltr"
            data-arch-row
        >
            {teeth.map((fdi) => (
                <ToothButton
                    key={fdi}
                    fdi={fdi}
                    selectedTooth={selectedTooth}
                    showPlanned={showPlanned}
                    onSelect={onSelect}
                    chartState={chartState}
                />
            ))}
            <span
                className="pointer-events-none absolute inset-y-2 left-1/2 hidden border-l border-blue-200 md:block"
                aria-hidden="true"
            />
        </section>
    );
}

function SelectedToothSummary({ fdi, showPlanned, state }) {
    const allProcedures = state?.procedures || [];
    const procedures = allProcedures.filter((procedure) => (
        showPlanned || procedure.lifecycle !== PROCEDURE_LIFECYCLE.PLANNED
    ));

    return (
        <aside className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4" aria-live="polite">
            <div className="flex items-center justify-between gap-4">
                <div>
                    <span className="text-xs font-semibold text-blue-700">السن المحدد</span>
                    <strong className="mt-1 block font-mono text-3xl text-blue-900">{fdi}</strong>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                    {procedures.length ? procedures.map((procedure) => (
                        <span
                            key={`${procedure.type}-${procedure.lifecycle}`}
                            className="rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
                        >
                            {PROCEDURE_LABELS[procedure.type] || procedure.type}
                            {procedure.lifecycle === PROCEDURE_LIFECYCLE.PLANNED ? ' — مخطط' : ''}
                        </span>
                    )) : <span className="text-sm text-slate-500">سن سليم</span>}
                </div>
            </div>
        </aside>
    );
}

function ClinicalStatePicker({ fdi, state, onChange }) {
    const current = state?.procedures?.[0] || null;
    const currentId = current
        ? CLINICAL_OPTIONS.find((option) => (
            option.procedure?.type === current.type
            && (option.procedure.surfaces || []).join('-') === (current.surfaces || []).join('-')
        ))?.id
        : 'healthy';

    return (
        <section className="rounded-2xl border border-slate-200 bg-white p-4" aria-labelledby="clinical-state-picker-title">
            <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                    <h2 id="clinical-state-picker-title" className="text-lg font-bold !text-slate-900">شكل السن {fdi}</h2>
                    <p className="mt-1 text-xs leading-5 text-slate-500">لا يمكن اختيار حالة قبل توفر هندستها البرمجية المخصصة لهذا السن والسطح.</p>
                </div>
                <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">رسم برمجي تشريحي</span>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5" data-testid="clinical-state-picker">
                {CLINICAL_OPTIONS.map((option) => {
                    const available = isOptionAvailable(fdi, option);
                    const selected = currentId === option.id;
                    return (
                        <button
                            key={option.id}
                            type="button"
                            onClick={() => available && onChange(option)}
                            disabled={!available}
                            aria-pressed={selected}
                            aria-label={`${option.label} للسن ${fdi}${available ? '' : ' — غير متاح'}`}
                            className={`relative min-h-20 rounded-xl border p-3 text-right transition focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
                                selected
                                    ? 'border-blue-600 bg-blue-50 text-blue-900'
                                    : available
                                        ? 'border-slate-200 bg-white text-slate-800 hover:border-blue-300'
                                        : 'cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400'
                            }`}
                        >
                            {selected
                                ? <CheckCircle2 className="absolute left-2 top-2 text-blue-600" size={16} aria-hidden="true" />
                                : !available && <LockKeyhole className="absolute left-2 top-2" size={15} aria-hidden="true" />}
                            <strong className="block text-sm">{option.label}</strong>
                            <span className="mt-1 block text-xs">{available ? option.group : 'قيد الإنتاج'}</span>
                        </button>
                    );
                })}
            </div>
        </section>
    );
}

export default function ClinicalChartApproval() {
    const [selectedTooth, setSelectedTooth] = useState(46);
    const [chartState, setChartState] = useState(() => ({
        46: buildClinicalState(CLINICAL_OPTIONS.find((option) => option.id === 'caries-o')),
    }));
    const showPlanned = false;
    const selectedState = useMemo(() => chartState[selectedTooth] || { procedures: [] }, [chartState, selectedTooth]);
    const handleStateChange = (option) => {
        setChartState((current) => ({ ...current, [selectedTooth]: buildClinicalState(option) }));
    };

    return (
        <main className="min-h-screen bg-[#f5f7fb] px-3 py-5 text-slate-900 sm:px-6 lg:px-10" dir="rtl">
            <div className="mx-auto max-w-[1500px]">
                <header className="mb-6 rounded-3xl border border-blue-100 bg-white p-5 shadow-sm">
                    <div>
                        <p className="mb-1 text-sm font-semibold text-blue-700">المرحلة 1 — اعتماد الأصول الأساسية</p>
                        <h1 className="text-2xl font-bold !text-slate-900">مخطط الأسنان الشفاف — استراتيجية C</h1>
                        <p className="mt-2 text-sm text-slate-500">32 سنًا مستقلًا ونظيفًا بترقيم FDI. الإجراءات تُرسم برمجيًا فوق السن الأساسي ولا تستبدله بصورة حالة.</p>
                    </div>
                </header>

                <section className="rounded-3xl border border-slate-200 bg-white p-3 shadow-sm sm:p-5" data-testid="full-mouth-chart">
                    <div className="mb-3 flex items-center gap-2 text-xs text-slate-500">
                        <Info size={15} className="text-blue-600" aria-hidden="true" />
                        ترقيم FDI — اضغط على أي سن لمراجعة حالته
                    </div>

                    <ArchRow
                        teeth={ADULT_FDI_ROWS.maxillary}
                        selectedTooth={selectedTooth}
                        showPlanned={showPlanned}
                        onSelect={setSelectedTooth}
                        label="الفك العلوي"
                        chartState={chartState}
                    />

                    <div className="my-3 border-t border-blue-200" />

                    <ArchRow
                        teeth={ADULT_FDI_ROWS.mandibular}
                        selectedTooth={selectedTooth}
                        showPlanned={showPlanned}
                        onSelect={setSelectedTooth}
                        label="الفك السفلي"
                        chartState={chartState}
                    />
                </section>

                <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
                    <SelectedToothSummary fdi={selectedTooth} showPlanned={showPlanned} state={selectedState} />
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">
                        الحالة المرئية: {selectedState.procedures.length ? 'إجراء سريري' : 'سليم'}.
                        المحرك يحافظ على أصل السن ويضيف طبقات تشريحية برمجية قابلة لتحديد السطح.
                    </div>
                </div>

                <div className="mt-4">
                    <ClinicalStatePicker fdi={selectedTooth} state={selectedState} onChange={handleStateChange} />
                </div>
            </div>
        </main>
    );
}
