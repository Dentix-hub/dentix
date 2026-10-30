import PropTypes from 'prop-types';
import { Check, RotateCcw, Sparkles } from 'lucide-react';
import {
    CHART_APPEARANCE_TEMPLATES,
    CHART_APPEARANCE_TEMPLATES_BY_KEY,
    resolveTemplatePreviewColors,
} from '@/features/clinical-chart/domain/procedureChartAppearance';
import { PROCEDURE_CHART_PALETTE_LIST } from '@/features/clinical-chart/domain/procedureChartPalette';

/**
 * Tiny 16x16 glyph representing a chart appearance template option.
 */
export function TemplateGlyph({ template, className = 'h-4 w-4' }) {
    const meta = CHART_APPEARANCE_TEMPLATES_BY_KEY[template];
    const glyphType = meta?.glyphType || 'none';

    return (
        <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            data-glyph-type={glyphType}
            className={className}
            fill="none"
        >
            {/* Base tooth outline */}
            <rect
                x="5"
                y="3"
                width="14"
                height="11"
                rx="3"
                stroke="currentColor"
                strokeWidth="1.5"
                opacity="0.45"
            />
            <path
                d="M8 14L9.5 21M16 14L14.5 21"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                opacity="0.45"
            />
            {glyphType === 'surface' && (
                <rect x="8.5" y="6" width="7" height="5" rx="1.2" fill="currentColor" />
            )}
            {glyphType === 'root' && (
                <path
                    d="M10 13.5L9.5 20.5M14 13.5L14.5 20.5"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                />
            )}
            {glyphType === 'crown' && (
                <rect
                    x="4.5"
                    y="2.5"
                    width="15"
                    height="11.5"
                    rx="3.2"
                    fill="currentColor"
                    fillOpacity="0.25"
                    stroke="currentColor"
                    strokeWidth="2"
                />
            )}
            {glyphType === 'bridge' && (
                <>
                    <rect
                        x="5"
                        y="3"
                        width="14"
                        height="11"
                        rx="3"
                        stroke="currentColor"
                        strokeWidth="2"
                    />
                    <line x1="2" y1="8.5" x2="22" y2="8.5" stroke="currentColor" strokeWidth="2" />
                </>
            )}
            {glyphType === 'implant-fixture' && (
                <g stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                    <line x1="12" y1="13" x2="12" y2="21" />
                    <line x1="9.5" y1="15.5" x2="14.5" y2="15.5" />
                    <line x1="10" y1="18" x2="14" y2="18" />
                </g>
            )}
            {glyphType === 'implant-crown' && (
                <>
                    <rect
                        x="5"
                        y="3"
                        width="14"
                        height="10.5"
                        rx="3"
                        fill="currentColor"
                        fillOpacity="0.25"
                        stroke="currentColor"
                        strokeWidth="1.8"
                    />
                    <line x1="12" y1="13.5" x2="12" y2="21" stroke="currentColor" strokeWidth="1.8" />
                    <line x1="9.5" y1="16.5" x2="14.5" y2="16.5" stroke="currentColor" strokeWidth="1.8" />
                </>
            )}
            {glyphType === 'extraction' && (
                <path
                    d="M6 4L18 19M18 4L6 19"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                />
            )}
            {glyphType === 'marker' && (
                <circle cx="16.5" cy="6.5" r="3.5" fill="currentColor" />
            )}
            {glyphType === 'none' && (
                <line
                    x1="5"
                    y1="19"
                    x2="19"
                    y2="5"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeDasharray="2 2"
                />
            )}
        </svg>
    );
}

TemplateGlyph.propTypes = {
    template: PropTypes.string,
    className: PropTypes.string,
};

/**
 * Live mini-tooth SVG preview matching the selected `(template, colorKey)` pair.
 */
export function MiniToothPreview({ template, colorKey, testId = 'chart-style-mini-preview' }) {
    const effectiveTemplate = template || 'NONE';
    const meta = CHART_APPEARANCE_TEMPLATES_BY_KEY[effectiveTemplate];
    const glyphType = meta?.glyphType || 'none';
    const { fill, stroke } = resolveTemplatePreviewColors(effectiveTemplate, colorKey);

    return (
        <div
            data-testid={testId}
            data-preview-template={effectiveTemplate}
            data-preview-color-key={colorKey || 'default'}
            data-preview-glyph={glyphType}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800"
            title={meta ? `${meta.labelAr} / ${meta.labelEn}` : 'بدون ظهور على الرسم / Billing only'}
        >
            <svg viewBox="0 0 36 42" className="h-9 w-9" aria-hidden="true">
                {/* Base crown */}
                <rect
                    x="7"
                    y="4"
                    width="22"
                    height="18"
                    rx="5"
                    fill={glyphType === 'crown' || glyphType === 'bridge' || glyphType === 'implant-crown' ? fill : '#f8fafc'}
                    stroke={glyphType === 'crown' || glyphType === 'bridge' || glyphType === 'implant-crown' ? stroke : '#94a3b8'}
                    strokeWidth={glyphType === 'crown' || glyphType === 'bridge' || glyphType === 'implant-crown' ? '2.2' : '1.4'}
                />
                {/* Base roots */}
                <path
                    d="M12 22 L14 36 M24 22 L22 36"
                    stroke={glyphType === 'root' ? stroke : '#94a3b8'}
                    strokeWidth={glyphType === 'root' ? '3' : '1.5'}
                    strokeLinecap="round"
                />

                {/* Surface filling */}
                {glyphType === 'surface' && (
                    <rect
                        data-testid={`${testId}-surface`}
                        x="12"
                        y="8.5"
                        width="12"
                        height="9"
                        rx="2.5"
                        fill={fill}
                        stroke={stroke}
                        strokeWidth="1.6"
                    />
                )}

                {/* Bridge connector bar */}
                {glyphType === 'bridge' && (
                    <line
                        data-testid={`${testId}-bridge-bar`}
                        x1="2"
                        y1="13"
                        x2="34"
                        y2="13"
                        stroke={stroke}
                        strokeWidth="2.5"
                        strokeLinecap="round"
                    />
                )}

                {/* Implant threads */}
                {(glyphType === 'implant-fixture' || glyphType === 'implant-crown') && (
                    <g data-testid={`${testId}-implant`} stroke={stroke} strokeWidth="2" strokeLinecap="round">
                        <line x1="18" y1="22" x2="18" y2="37" />
                        <line x1="14" y1="26" x2="22" y2="26" />
                        <line x1="14.5" y1="30" x2="21.5" y2="30" />
                        <line x1="15.5" y1="34" x2="20.5" y2="34" />
                    </g>
                )}

                {/* Extraction X */}
                {glyphType === 'extraction' && (
                    <path
                        data-testid={`${testId}-extraction`}
                        d="M8 6 L28 35 M28 6 L8 35"
                        stroke={stroke}
                        strokeWidth="2.8"
                        strokeLinecap="round"
                    />
                )}

                {/* Marker dot */}
                {glyphType === 'marker' && (
                    <circle
                        data-testid={`${testId}-marker`}
                        cx="25"
                        cy="9"
                        r="4.5"
                        fill={fill}
                        stroke={stroke}
                        strokeWidth="1.6"
                    />
                )}
            </svg>
        </div>
    );
}

MiniToothPreview.propTypes = {
    template: PropTypes.string,
    colorKey: PropTypes.string,
    testId: PropTypes.string,
};

/**
 * Reusable chart appearance control used in both the per-procedure row and the
 * "Add new procedure" modal in `ProceduresSettings.jsx`.
 */
export default function ProcedureChartAppearanceControl({
    controlId,
    template,
    colorKey,
    onChangeTemplate,
    onChangeColorKey,
    suggestion = null,
    onApplySuggestion = null,
    onSave = null,
    onClear = null,
    hasSavedOverride = false,
    isDirty = false,
    isSaving = false,
    showCreateDefaultHint = false,
}) {
    const isColorDisabled = !template || template === 'NONE';

    return (
        <div
            data-testid={`chart-appearance-control-${controlId}`}
            className="mt-3 space-y-2.5 rounded-xl border border-slate-200/80 bg-white/90 p-3 dark:border-slate-700/80 dark:bg-slate-800/70"
        >
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                        الظهور على مخطط الأسنان (Chart appearance)
                    </span>
                    <TemplateGlyph
                        template={template || 'NONE'}
                        className="h-4 w-4 text-indigo-600 dark:text-indigo-400"
                    />
                </div>

                {/* Save / Clear actions for existing procedure rows */}
                {(onSave || onClear) && (
                    <div className="flex items-center gap-1.5">
                        {onClear && hasSavedOverride && (
                            <button
                                type="button"
                                data-testid={`clear-chart-style-${controlId}`}
                                disabled={isSaving}
                                onClick={onClear}
                                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-bold text-slate-600 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                title="استعادة الإعداد الافتراضي / Reset to default"
                            >
                                <RotateCcw className="h-3.5 w-3.5" />
                                <span>استعادة</span>
                            </button>
                        )}
                        {onSave && (
                            <button
                                type="button"
                                data-testid={`save-chart-style-${controlId}`}
                                disabled={isSaving || (!isDirty && !template)}
                                onClick={onSave}
                                className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1 text-xs font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
                            >
                                <Check className="h-3.5 w-3.5" />
                                <span>{isSaving ? 'جاري الحفظ...' : 'حفظ المظهر'}</span>
                            </button>
                        )}
                    </div>
                )}
            </div>

            {showCreateDefaultHint && (
                <p
                    data-testid={`chart-style-default-hint-${controlId}`}
                    className="rounded-lg bg-indigo-50/80 px-2.5 py-1.5 text-xs text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300"
                >
                    تظهر الإجراءات الجديدة افتراضيًا كعلامة على السن (Tooth marker) حتى تظهر على مخطط الأسنان مباشرة، ويمكنك تغيير القالب أو اللون أدناه.
                </p>
            )}

            {/* Suggestion chip (U4C #3): never auto-applied */}
            {suggestion && (
                <div
                    data-testid={`chart-style-suggestion-${controlId}`}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50/80 px-2.5 py-1.5 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
                >
                    <span className="inline-flex items-center gap-1.5 font-semibold">
                        <Sparkles className="h-3.5 w-3.5 text-amber-500" />
                        <span>
                            Suggested: {suggestion.labelAr} ({suggestion.labelEn}) — apply? / مقترح: {suggestion.labelAr} — تطبيق؟
                        </span>
                    </span>
                    <button
                        type="button"
                        data-testid={`apply-chart-style-suggestion-${controlId}`}
                        onClick={() => onApplySuggestion && onApplySuggestion(suggestion.template)}
                        className="rounded-md bg-amber-600 px-2.5 py-0.5 text-xs font-bold text-white hover:bg-amber-700"
                    >
                        تطبيق / Apply
                    </button>
                </div>
            )}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                {/* Live mini-tooth preview */}
                <MiniToothPreview
                    template={template}
                    colorKey={colorKey}
                    testId={`chart-style-mini-preview-${controlId}`}
                />

                <div className="flex-1 space-y-2">
                    {/* Template selector */}
                    <div>
                        <label
                            htmlFor={`chart-style-template-select-${controlId}`}
                            className="sr-only"
                        >
                            قالب الظهور على المخطط
                        </label>
                        <select
                            id={`chart-style-template-select-${controlId}`}
                            data-testid={`chart-style-template-select-${controlId}`}
                            value={template || ''}
                            onChange={(e) => {
                                const nextTemplate = e.target.value || '';
                                onChangeTemplate(nextTemplate);
                            }}
                            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-bold text-slate-800 outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                        >
                            <option value="">غير محدد (تلقائي / بدون تخصيص)</option>
                            {CHART_APPEARANCE_TEMPLATES.map((opt) => (
                                <option key={opt.template} value={opt.template}>
                                    {opt.labelAr} / {opt.labelEn}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* 12-swatch palette + Default (null) swatch */}
                    <div
                        data-testid={`chart-style-palette-${controlId}`}
                        className="flex flex-wrap items-center gap-1.5"
                    >
                        <button
                            type="button"
                            data-testid={`chart-style-color-${controlId}-default`}
                            disabled={isColorDisabled}
                            aria-pressed={!colorKey}
                            onClick={() => onChangeColorKey(null)}
                            title="اللون الافتراضي للقالب / Default template color"
                            className={`inline-flex h-6 items-center rounded-md border px-2 text-xs font-bold transition ${
                                !colorKey
                                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700 dark:border-indigo-400 dark:bg-indigo-950/60 dark:text-indigo-200'
                                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                            } disabled:cursor-not-allowed disabled:opacity-40`}
                        >
                            افتراضي
                        </button>

                        {PROCEDURE_CHART_PALETTE_LIST.map((swatch) => {
                            const isSelected = colorKey === swatch.key;
                            return (
                                <button
                                    key={swatch.key}
                                    type="button"
                                    data-testid={`chart-style-color-${controlId}-${swatch.key}`}
                                    disabled={isColorDisabled}
                                    aria-pressed={isSelected}
                                    aria-label={`${swatch.labelAr} (${swatch.labelEn})`}
                                    title={`${swatch.labelAr} / ${swatch.labelEn}`}
                                    onClick={() => onChangeColorKey(swatch.key)}
                                    style={{
                                        backgroundColor: swatch.fill,
                                        borderColor: swatch.stroke,
                                    }}
                                    className={`h-6 w-6 rounded-full border-2 transition-transform ${
                                        isSelected ? 'scale-110 ring-2 ring-indigo-500 ring-offset-1' : 'hover:scale-105'
                                    } disabled:cursor-not-allowed disabled:opacity-35`}
                                />
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

ProcedureChartAppearanceControl.propTypes = {
    controlId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    template: PropTypes.string,
    colorKey: PropTypes.string,
    onChangeTemplate: PropTypes.func.isRequired,
    onChangeColorKey: PropTypes.func.isRequired,
    suggestion: PropTypes.shape({
        template: PropTypes.string,
        labelAr: PropTypes.string,
        labelEn: PropTypes.string,
    }),
    onApplySuggestion: PropTypes.func,
    onSave: PropTypes.func,
    onClear: PropTypes.func,
    hasSavedOverride: PropTypes.bool,
    isDirty: PropTypes.bool,
    isSaving: PropTypes.bool,
    showCreateDefaultHint: PropTypes.bool,
};
