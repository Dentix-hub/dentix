import { useMemo, useState } from 'react';
import { Check, CircleDot, Layers3 } from 'lucide-react';
import ApprovedArtworkCrop from './ApprovedArtworkCrop';
import { APPROVED_ARTWORK } from './approvedArtwork';

const ANATOMY_SAMPLES = [
    { id: 'maxillary-molar', label: 'ضرس علوي', fdi: 27, crop: [1120, 130, 86, 174] },
    { id: 'maxillary-premolar', label: 'ضاحك علوي', fdi: 25, crop: [960, 125, 72, 182] },
    { id: 'maxillary-canine', label: 'ناب علوي', fdi: 23, crop: [830, 120, 70, 190] },
    { id: 'maxillary-incisor', label: 'قاطع علوي', fdi: 21, crop: [720, 125, 65, 184] },
    { id: 'mandibular-molar', label: 'ضرس سفلي', fdi: 36, crop: [1025, 382, 75, 145] },
    { id: 'mandibular-premolar', label: 'ضاحك سفلي', fdi: 35, crop: [962, 382, 62, 145] },
    { id: 'mandibular-canine', label: 'ناب سفلي', fdi: 33, crop: [835, 382, 60, 145] },
    { id: 'mandibular-incisor', label: 'قاطع سفلي', fdi: 31, crop: [720, 382, 54, 145] },
];

const PROCEDURES = [
    {
        id: 'caries',
        label: 'تسوس',
        rule: 'آفة غير منتظمة داخل تاج السن وعلى السطح المصاب فقط، ولا تمتد إلى الجذر.',
        crop: [145, 0, 255, 260],
        color: 'bg-red-600',
    },
    {
        id: 'composite',
        label: 'حشو تجميلي',
        rule: 'ترميم أزرق يتبع حدود تحضير السطح، وليس نقطة أو تلوينًا للسن كله.',
        crop: [642, 0, 260, 260],
        color: 'bg-blue-600',
    },
    {
        id: 'amalgam',
        label: 'حشو أملغم',
        rule: 'ترميم معدني فضي داخل حدود التحضير التشريحية على التاج.',
        crop: [1137, 0, 260, 260],
        color: 'bg-slate-500',
    },
    {
        id: 'rct',
        label: 'علاج عصب',
        rule: 'حجرة اللب والقنوات الفعلية داخل الجذور، مع بقاء تشريح السن ظاهرًا.',
        crop: [140, 316, 270, 270],
        color: 'bg-purple-600',
    },
    {
        id: 'crown',
        label: 'تاج',
        rule: 'غلاف كامل يطابق التاج التشريحي، والجذور الطبيعية تظل ظاهرة.',
        crop: [638, 316, 270, 270],
        color: 'bg-amber-500',
    },
    {
        id: 'implant',
        label: 'زرعة',
        rule: 'جسم زرعة ملولب ودعامة وتاج مطابق للتشريح، بدل الجذور الطبيعية.',
        crop: [1135, 316, 270, 270],
        color: 'bg-teal-600',
    },
    {
        id: 'bridge',
        label: 'جسر',
        rule: 'تاجا دعامة وPontic بلا جذر ووصلات قصيرة، كوحدة علاجية واحدة.',
        crop: [70, 640, 440, 270],
        color: 'bg-orange-600',
    },
    {
        id: 'missing',
        label: 'سن مفقود',
        rule: 'شبح خافت للسن مع X هادئة للحفاظ على موضعه وترقيمه.',
        crop: [638, 640, 270, 270],
        color: 'bg-slate-600',
    },
    {
        id: 'planned',
        label: 'علاج مخطط',
        rule: 'نفس لون وشكل الإجراء، مع شفافية أقل وحد متقطع لدورة الحياة.',
        crop: [1134, 640, 270, 270],
        color: 'bg-orange-500',
    },
];

const HEALTHY_MOLAR = Object.freeze({ crop: [1025, 382, 75, 145] });

function AnatomyCard({ sample }) {
    return (
        <article className="rounded-2xl border border-slate-200 bg-white p-3 text-center shadow-sm">
            <div className="mx-auto h-36 w-full" dir="ltr">
                <ApprovedArtworkCrop
                    artwork={APPROVED_ARTWORK.anatomy}
                    crop={sample.crop}
                    label={`${sample.label} من التشريح المعتمد`}
                />
            </div>
            <strong className="mt-2 block text-sm text-slate-900">{sample.label}</strong>
            <span className="mt-1 block font-mono text-xs text-slate-400">FDI {sample.fdi}</span>
        </article>
    );
}

function ProcedureButton({ procedure, selected, onSelect }) {
    return (
        <button
            type="button"
            onClick={onSelect}
            aria-pressed={selected}
            className={`relative flex min-h-[190px] flex-col items-center rounded-2xl border bg-white p-3 text-center shadow-sm transition focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
                selected
                    ? 'border-blue-600 ring-2 ring-blue-100'
                    : 'border-slate-200 hover:border-blue-300 hover:shadow-md'
            }`}
        >
            {selected && (
                <span className="absolute left-2 top-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-white">
                    <Check size={14} aria-hidden="true" />
                </span>
            )}
            <div className="h-32 w-full" dir="ltr">
                <ApprovedArtworkCrop
                    artwork={APPROVED_ARTWORK.procedures}
                    crop={procedure.crop}
                    label={`${procedure.label} على السن المعتمد`}
                />
            </div>
            <span className="mt-2 inline-flex items-center gap-2 text-sm font-bold text-slate-900">
                <span className={`h-2.5 w-2.5 rounded-full ${procedure.color}`} aria-hidden="true" />
                {procedure.label}
            </span>
        </button>
    );
}

export default function ClinicalToothSpecimen() {
    const [selectedProcedureId, setSelectedProcedureId] = useState('caries');
    const selectedProcedure = useMemo(
        () => PROCEDURES.find((procedure) => procedure.id === selectedProcedureId) || PROCEDURES[0],
        [selectedProcedureId],
    );

    return (
        <main
            className="min-h-screen bg-[#f5f7fb] px-4 py-6 text-slate-900 sm:px-6 lg:px-10"
            data-testid="clinical-tooth-specimen"
            dir="rtl"
        >
            <div className="mx-auto max-w-[1440px]">
                <header className="mb-7 rounded-3xl border border-blue-100 bg-white p-6 shadow-sm">
                    <p className="mb-2 text-sm font-semibold text-blue-700">DENTIX Native Renderer — Approved Strategy C</p>
                    <h1 className="text-2xl font-bold !text-slate-900 sm:text-3xl">معاينة تأثير الإجراءات على الأسنان المعتمدة</h1>
                    <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-600">
                        اختر الإجراء لمشاهدة التغيير السريري على السن. هذه الصفحة مخصصة لاعتماد التشريح ولغة الإجراءات
                        قبل بناء مخطط الفم الكامل وربطه بالبيانات.
                    </p>
                </header>

                <section aria-labelledby="interactive-preview-title" className="mb-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h2 id="interactive-preview-title" className="text-xl font-bold !text-slate-900">المقارنة التفاعلية</h2>
                            <p className="mt-1 text-sm text-slate-500">سن سليم قبل الإجراء مقابل النتيجة المرئية بعده.</p>
                        </div>
                        <div className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-800">
                            <Layers3 size={17} aria-hidden="true" />
                            {selectedProcedure.label}
                        </div>
                    </div>

                    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:items-center">
                        <article className="rounded-2xl border border-slate-200 bg-[#fbfcfe] p-4 text-center">
                            <span className="text-sm font-semibold text-slate-500">قبل</span>
                            <div className="mx-auto mt-3 h-72 max-w-sm" dir="ltr">
                                <ApprovedArtworkCrop
                                    artwork={APPROVED_ARTWORK.anatomy}
                                    crop={HEALTHY_MOLAR.crop}
                                    label="ضرس سليم من التشريح المعتمد"
                                    testId="healthy-preview"
                                />
                            </div>
                            <strong className="mt-2 block text-slate-900">سن سليم</strong>
                        </article>

                        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-blue-600 text-white" aria-hidden="true">
                            <span className="text-xl">←</span>
                        </div>

                        <article className="rounded-2xl border border-blue-200 bg-blue-50/40 p-4 text-center" aria-live="polite">
                            <span className="text-sm font-semibold text-blue-700">بعد</span>
                            <div className="mx-auto mt-3 h-72 max-w-md" dir="ltr">
                                <ApprovedArtworkCrop
                                    artwork={APPROVED_ARTWORK.procedures}
                                    crop={selectedProcedure.crop}
                                    label={`${selectedProcedure.label} على السن المعتمد`}
                                    testId="procedure-preview"
                                />
                            </div>
                            <strong className="mt-2 block text-lg text-slate-900">{selectedProcedure.label}</strong>
                            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600">{selectedProcedure.rule}</p>
                        </article>
                    </div>
                </section>

                <section aria-labelledby="procedures-title" className="mb-8">
                    <div className="mb-4 flex items-center gap-2">
                        <CircleDot size={19} className="text-blue-600" aria-hidden="true" />
                        <h2 id="procedures-title" className="text-xl font-bold !text-slate-900">اختر الإجراء</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" data-testid="procedure-grid">
                        {PROCEDURES.map((procedure) => (
                            <ProcedureButton
                                key={procedure.id}
                                procedure={procedure}
                                selected={selectedProcedure.id === procedure.id}
                                onSelect={() => setSelectedProcedureId(procedure.id)}
                            />
                        ))}
                    </div>
                </section>

                <section aria-labelledby="anatomy-title" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                    <h2 id="anatomy-title" className="text-xl font-bold !text-slate-900">التشريح المقفول</h2>
                    <p className="mt-2 text-sm text-slate-500">الإجراءات تُركّب فوق هذه الهوية التشريحية ولا تغيّر شكل السن الأساسي.</p>
                    <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-8" data-testid="anatomy-grid">
                        {ANATOMY_SAMPLES.map((sample) => <AnatomyCard key={sample.id} sample={sample} />)}
                    </div>
                </section>

                <footer className="mt-7 rounded-2xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm leading-7 text-blue-950">
                    نطاق الجولة: اعتماد الـrenderer البصري التفاعلي فقط. لا توجد كتابة بيانات، ولا تعديل Backend أو Database،
                    ولا دمج في مخطط المريض الكامل حتى اجتياز المراجعة البصرية التالية.
                </footer>
            </div>
        </main>
    );
}
