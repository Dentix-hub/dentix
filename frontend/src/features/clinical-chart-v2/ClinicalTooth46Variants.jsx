import { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import healthy from './assets/tooth-46-approval-v1/tooth-46-healthy.png';
import caries from './assets/tooth-46-approval-v1/tooth-46-caries-v1.png';
import composite from './assets/tooth-46-approval-v1/tooth-46-composite-v2.png';
import amalgam from './assets/tooth-46-approval-v1/tooth-46-amalgam-v1.png';
import rct from './assets/tooth-46-approval-v1/tooth-46-rct-v1.png';
import crown from './assets/tooth-46-approval-v1/tooth-46-crown-v1.png';
import implant from './assets/tooth-46-approval-v1/tooth-46-implant-v1.png';
import missing from './assets/tooth-46-approval-v1/tooth-46-missing-v1.png';
import fracture from './assets/tooth-46-approval-v1/tooth-46-fracture-v1.png';

const VARIANTS = Object.freeze([
    { id: 'healthy', label: 'سليم', group: 'أساسي', src: healthy, description: 'الأصل التشريحي الشفاف للسن 46.' },
    { id: 'caries', label: 'تسوس إطباقي', group: 'حالة مرضية', src: caries, description: 'تسوس مدمج داخل شقوق تاج السن فقط، ولا يمتد إلى الجذر.' },
    { id: 'composite', label: 'حشو تجميلي', group: 'إجراء', src: composite, description: 'ترميم تجميلي يتبع تحضير السطح الإطباقي وحدود المينا.' },
    { id: 'amalgam', label: 'حشو أملغم', group: 'إجراء', src: amalgam, description: 'ترميم معدني داخل تحضير تشريحي محدود في التاج.' },
    { id: 'rct', label: 'علاج عصب', group: 'إجراء', src: rct, description: 'حجرة لب وقناتان متوافقتان مع جذري السن 46.' },
    { id: 'crown', label: 'تاج', group: 'إجراء', src: crown, description: 'غلاف تاج كامل مطابق للتشريح مع بقاء الجذور الطبيعية.' },
    { id: 'implant', label: 'زرعة', group: 'إجراء', src: implant, description: 'تاج ضرس ودعامة وجسم زرعة ملولب بدل الجذور.' },
    { id: 'missing', label: 'سن مفقود', group: 'حالة', src: missing, description: 'شبح هادئ لنفس السن مع علامة X للحفاظ على المحاذاة.' },
    { id: 'fracture', label: 'كسر بالتاج', group: 'حالة مرضية', src: fracture, description: 'كسر موضعي في حدبة التاج مع بقاء الجذور سليمة.' },
]);

function ToothImage({ src, alt, testId }) {
    return (
        <img
            src={src}
            alt={alt}
            data-testid={testId}
            className="h-full w-full object-contain"
            draggable="false"
        />
    );
}

export default function ClinicalTooth46Variants() {
    const [selectedId, setSelectedId] = useState('caries');
    const selected = useMemo(
        () => VARIANTS.find((variant) => variant.id === selectedId) || VARIANTS[1],
        [selectedId],
    );

    return (
        <main className="min-h-screen bg-[#f5f7fb] px-3 py-5 text-slate-900 sm:px-6 lg:px-10" dir="rtl">
            <div className="mx-auto max-w-[1440px]">
                <header className="mb-5 rounded-3xl border border-blue-100 bg-white p-5 shadow-sm sm:p-6">
                    <p className="text-sm font-semibold text-blue-700">حزمة اعتماد مخصصة — FDI 46</p>
                    <h1 className="mt-1 text-2xl font-bold !text-slate-900">شكل الإجراءات والحالات المرضية</h1>
                    <p className="mt-2 max-w-4xl text-sm leading-7 text-slate-600">
                        كل صورة أصل مستقل لنفس نوع السن، وليست صورة إجراء عامة موضوعة فوق المخطط.
                        هذه الحزمة لاعتماد الأسلوب قبل تعميمه على الأسنان الأخرى والأسطح المختلفة.
                    </p>
                </header>

                <section className="mb-5 grid gap-4 lg:grid-cols-2" aria-label="مقارنة الحالة المختارة بالسن السليم">
                    <article className="rounded-3xl border border-slate-200 bg-white p-4 text-center shadow-sm">
                        <span className="text-sm font-semibold text-slate-500">قبل — سن سليم</span>
                        <div className="mx-auto mt-3 h-[360px] max-w-md sm:h-[460px]">
                            <ToothImage src={healthy} alt="السن 46 سليم" testId="healthy-tooth-preview" />
                        </div>
                    </article>

                    <article className="rounded-3xl border border-blue-200 bg-blue-50/40 p-4 text-center shadow-sm" aria-live="polite">
                        <span className="text-sm font-semibold text-blue-700">بعد — {selected.label}</span>
                        <div className="mx-auto mt-3 h-[360px] max-w-md sm:h-[460px]">
                            <ToothImage src={selected.src} alt={`السن 46: ${selected.label}`} testId="selected-variant-preview" />
                        </div>
                        <strong className="block text-lg text-slate-900">{selected.label}</strong>
                        <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-600">{selected.description}</p>
                    </article>
                </section>

                <section aria-labelledby="variant-grid-title">
                    <div className="mb-3 flex items-center justify-between gap-3">
                        <h2 id="variant-grid-title" className="text-xl font-bold !text-slate-900">اختر الحالة</h2>
                        <span className="rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-slate-500 shadow-sm">9 أصول شفافة</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5" data-testid="tooth-46-variant-grid">
                        {VARIANTS.map((variant) => {
                            const selectedVariant = variant.id === selected.id;
                            return (
                                <button
                                    key={variant.id}
                                    type="button"
                                    onClick={() => setSelectedId(variant.id)}
                                    aria-pressed={selectedVariant}
                                    aria-label={`عرض ${variant.label}`}
                                    className={`relative rounded-2xl border bg-white p-3 text-center shadow-sm transition focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
                                        selectedVariant ? 'border-blue-600 ring-2 ring-blue-100' : 'border-slate-200 hover:border-blue-300'
                                    }`}
                                >
                                    {selectedVariant && (
                                        <CheckCircle2 className="absolute left-2 top-2 text-blue-600" size={18} aria-hidden="true" />
                                    )}
                                    <div className="h-36 sm:h-44">
                                        <ToothImage src={variant.src} alt="" />
                                    </div>
                                    <strong className="mt-2 block text-sm text-slate-900">{variant.label}</strong>
                                    <span className="mt-1 block text-xs text-slate-500">{variant.group}</span>
                                </button>
                            );
                        })}
                    </div>
                </section>

                <footer className="mt-5 flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
                    <AlertTriangle className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
                    لم تُعمم هذه الأصول على بقية الأسنان بعد. الاعتماد هنا لشكل سن 46 فقط؛ وبعد الموافقة تُنتج نسخة تشريحية مخصصة لكل FDI وسطح.
                </footer>
            </div>
        </main>
    );
}
