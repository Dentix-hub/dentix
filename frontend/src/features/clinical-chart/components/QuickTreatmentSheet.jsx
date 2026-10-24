import { useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { Check, Package, SlidersHorizontal } from 'lucide-react';
import DentixBottomSheet from '@/shared/ui/DentixBottomSheet';
import { resolveProcedureSelection } from '@/features/patients/utils/resolveProcedureSelection';
import { buildTreatmentPayload } from '@/features/patients/utils/buildTreatmentPayload';
import { resolveEffectiveProcedureChartBehavior } from '@/features/clinical-chart/domain/procedureChartAppearance';
import { palmerToFdi } from '@/utils/toothUtils';

const normalizeSheetData = (data) => {
    if (!data) return null;
    const rawSurfaces = Array.isArray(data.surfaces)
        ? data.surfaces
        : (data.surface ? String(data.surface).replace(/[^A-Za-z]/g, '').toUpperCase().split('') : []);
    return {
        ...data,
        status: data.status || 'Done',
        surface: data.surface || rawSurfaces.join(''),
        surfaces: rawSurfaces,
        target_kind: data.target_kind || (rawSurfaces.length > 0 ? 'surface' : 'tooth'),
    };
};

/**
 * Compact Quick Treatment Confirm Sheet (U4D / D1).
 * Built on `DentixBottomSheet`. Used by Quick Action Launcher Flow B so chairside
 * charting confirms in a compact sheet instead of opening the giant `TreatmentModal`.
 * Escalates to `TreatmentModal` on "More details" or any stock/session/link/validation error.
 */
export default function QuickTreatmentSheet({
    isOpen,
    onClose,
    onSave,
    onOpenDetails,
    initialData,
    procedures = [],
}) {
    const { t } = useTranslation();
    const [treatment, setTreatment] = useState(() => normalizeSheetData(initialData));
    const [consumedMaterials, setConsumedMaterials] = useState([]);
    const [isSaving, setIsSaving] = useState(false);
    const isSavingRef = useRef(false);

    const safeProcedures = useMemo(
        () => (Array.isArray(procedures) ? procedures : []),
        [procedures],
    );

    const matchedProcedure = useMemo(() => {
        if (!treatment?.procedure) return null;
        return safeProcedures.find((p) => p.name === treatment.procedure) || null;
    }, [safeProcedures, treatment?.procedure]);

    const paletteSwatch = useMemo(() => {
        if (!matchedProcedure) return null;
        return resolveEffectiveProcedureChartBehavior(matchedProcedure).paletteSwatch;
    }, [matchedProcedure]);

    useEffect(() => {
        if (!isOpen) return;
        const normalized = normalizeSheetData(initialData);
        setTreatment(normalized);
        setConsumedMaterials([]);

        const procName = normalized?.procedure;
        if (procName) {
            resolveProcedureSelection({
                procedureName: procName,
                procedures: safeProcedures,
                defaultPriceListId: normalized?.default_price_list_id,
                currentPriceListId: normalized?.price_list_id,
            }).then(({ found, cost, price_list_id, autoMaterials }) => {
                if (!found) {
                    setTreatment((prev) => (prev ? {
                        ...prev,
                        procedure: procName,
                        cost: prev.cost ?? '',
                        price_list_id: null,
                    } : prev));
                    setConsumedMaterials([]);
                } else {
                    setTreatment((prev) => (prev ? {
                        ...prev,
                        procedure: procName,
                        cost,
                        price_list_id,
                    } : prev));
                    setConsumedMaterials(Array.isArray(autoMaterials) ? autoMaterials : []);
                }
            });
        }
    }, [isOpen, initialData, safeProcedures]);

    if (!isOpen || !treatment) return null;

    const fdiTooth = palmerToFdi(treatment.tooth_number) || treatment.tooth_number || '';
    const surfaceList = Array.isArray(treatment.surfaces) ? treatment.surfaces : [];
    const numericCost = parseFloat(treatment.cost) || 0;
    const isUnpriced = numericCost === 0;
    const currentStatus = treatment.status || 'Done';

    const handleOpenFullModal = (escalationError = null) => {
        const escalatedData = {
            ...treatment,
            status: currentStatus,
            consumedMaterials,
            escalated_from_quick_sheet: true,
            ...(escalationError ? { escalation_error: escalationError } : {}),
        };
        onClose?.();
        onOpenDetails?.(escalatedData);
    };

    const handleSave = async (e) => {
        if (e) e.preventDefault();
        if (isSavingRef.current) return;
        isSavingRef.current = true;
        setIsSaving(true);

        const payload = buildTreatmentPayload(
            {
                ...treatment,
                status: currentStatus,
            },
            {
                consumedMaterials,
                procedures: safeProcedures,
                isEditing: false,
                forceSkipStock: false,
            },
        );

        try {
            await onSave(payload);
            onClose?.();
        } catch (error) {
            // U4D #4: Escalate any stock shortage, open-session conflict, clinical link error,
            // or validation error to TreatmentModal with the current edited state + error.
            handleOpenFullModal(error);
        } finally {
            isSavingRef.current = false;
            setIsSaving(false);
        }
    };

    const headerTitle = (
        <span className="inline-flex items-center gap-2" data-testid="quick-treatment-sheet-header">
            {paletteSwatch && (
                <span
                    data-testid="quick-treatment-sheet-swatch"
                    data-color-key={paletteSwatch.key}
                    style={{
                        backgroundColor: paletteSwatch.fill,
                        borderColor: paletteSwatch.stroke,
                    }}
                    className="inline-block h-3.5 w-3.5 shrink-0 rounded-full border"
                    title={`${paletteSwatch.labelAr} / ${paletteSwatch.labelEn}`}
                />
            )}
            <span data-testid="quick-treatment-sheet-procedure-name">
                {treatment.procedure || t('quick_treatment_sheet.default_procedure_name', 'تأكيد الإجراء السريع')}
            </span>
        </span>
    );

    return (
        <DentixBottomSheet
            open={isOpen}
            onOpenChange={(nextOpen) => {
                if (!nextOpen) onClose?.();
            }}
            title={headerTitle}
            closeLabel={t('quick_treatment_sheet.close_button_label', 'إغلاق نافذة التأكيد السريع')}
        >
            <form
                onSubmit={handleSave}
                data-testid="quick-treatment-sheet"
                className="space-y-4"
            >
                {/* Read-only Tooth & Surface chips */}
                <div className="flex flex-wrap items-center gap-2" data-testid="quick-treatment-sheet-targets">
                    {treatment.tooth_number && (
                        <span
                            data-testid="quick-treatment-tooth-chip"
                            data-palmer-tooth={treatment.tooth_number}
                            data-fdi-tooth={fdiTooth}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold text-blue-800 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-200"
                        >
                            <span>{t('quick_treatment_sheet.tooth_label', 'السن:')}</span>
                            <span className="font-mono">{fdiTooth}</span>
                            {String(fdiTooth) !== String(treatment.tooth_number) && (
                                <span className="text-blue-600/80 dark:text-blue-300/80 font-mono">
                                    ({treatment.tooth_number})
                                </span>
                            )}
                        </span>
                    )}

                    {surfaceList.length > 0 ? (
                        <div className="flex flex-wrap items-center gap-1" data-testid="quick-treatment-surface-chips">
                            <span className="text-xs font-bold text-slate-500 dark:text-slate-400">{t('quick_treatment_sheet.surfaces_label', 'الأسطح:')}</span>
                            {surfaceList.map((surf) => (
                                <span
                                    key={surf}
                                    data-testid={`quick-treatment-surface-chip-${surf}`}
                                    className="inline-flex items-center rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 font-mono text-xs font-bold text-indigo-800 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-200"
                                >
                                    {surf}
                                </span>
                            ))}
                        </div>
                    ) : (
                        <span
                            data-testid="quick-treatment-whole-tooth-chip"
                            className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                        >
                            {t('quick_treatment_sheet.whole_tooth', 'كامل السن (Whole tooth)')}
                        </span>
                    )}
                </div>

                {/* Price (editable numeric) + Status segmented control */}
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div>
                        <div className="mb-1 flex items-center justify-between">
                            <label
                                htmlFor="quick-treatment-cost"
                                className="text-xs font-bold text-slate-600 dark:text-slate-300"
                            >
                                {t('quick_treatment_sheet.cost_label', 'التكلفة')}
                            </label>
                            {isUnpriced && (
                                <span
                                    data-testid="quick-treatment-unpriced-hint"
                                    className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-bold text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                                >
                                    {t('quick_treatment_sheet.unpriced_hint', 'غير مسعّر')}
                                </span>
                            )}
                        </div>
                        <input
                            id="quick-treatment-cost"
                            data-testid="quick-treatment-cost-input"
                            type="number"
                            value={treatment.cost ?? ''}
                            onChange={(e) => setTreatment((prev) => ({
                                ...prev,
                                cost: e.target.value,
                            }))}
                            placeholder="0.00"
                            className="w-full rounded-xl border border-slate-200 bg-slate-50 p-2.5 font-bold text-slate-900 outline-none focus:border-blue-500 focus:bg-white dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                        />
                    </div>

                    <div>
                        <span className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                            {t('quick_treatment_sheet.status_label', 'حالة الإجراء')}
                        </span>
                        <div
                            data-testid="quick-treatment-status-control"
                            className="flex gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-900"
                        >
                            {[
                                { id: 'Done', label: t('quick_treatment_sheet.status_done', 'تم الانتهاء'), activeClass: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' },
                                { id: 'Pending', label: t('quick_treatment_sheet.status_pending', 'قيد التنفيذ'), activeClass: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300' },
                            ].map((opt) => {
                                const isActive = currentStatus === opt.id;
                                return (
                                    <button
                                        key={opt.id}
                                        type="button"
                                        data-testid={`quick-treatment-status-${opt.id}`}
                                        aria-pressed={isActive}
                                        onClick={() => setTreatment((prev) => ({
                                            ...prev,
                                            status: opt.id,
                                        }))}
                                        className={`flex-1 rounded-lg py-2 text-xs font-bold transition-all ${
                                            isActive
                                                ? `${opt.activeClass} border shadow-sm`
                                                : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'
                                        }`}
                                    >
                                        {opt.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* One-line BOM summary when materials exist */}
                {consumedMaterials.length > 0 && (
                    <div
                        data-testid="quick-treatment-bom-summary"
                        className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-200/80 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-900 dark:border-indigo-900/50 dark:bg-indigo-950/30 dark:text-indigo-200"
                    >
                        <span className="inline-flex items-center gap-1.5 font-semibold">
                            <Package className="h-4 w-4 text-indigo-600 dark:text-indigo-400" aria-hidden="true" />
                            <span>
                                {t('quick_treatment_sheet.bom_summary', 'سيتم خصم {{count}} مواد ({{count}} materials will be deducted)', { count: consumedMaterials.length })}
                            </span>
                        </span>
                        <button
                            type="button"
                            data-testid="quick-treatment-bom-details-link"
                            onClick={() => handleOpenFullModal(null)}
                            className="font-bold text-indigo-700 underline hover:text-indigo-900 dark:text-indigo-300"
                        >
                            {t('quick_treatment_sheet.bom_details_link', 'تعديل المواد / Details')}
                        </button>
                    </div>
                )}

                {/* Action buttons: Save, More details, Cancel */}
                <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                    <button
                        type="button"
                        data-testid="quick-treatment-cancel-button"
                        onClick={() => onClose?.()}
                        className="min-h-11 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                    >
                        {t('quick_treatment_sheet.cancel_button', 'إلغاء')}
                    </button>
                    <button
                        type="button"
                        data-testid="quick-treatment-more-details-button"
                        onClick={() => handleOpenFullModal(null)}
                        className="inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                    >
                        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>{t('quick_treatment_sheet.more_details_button', 'تفاصيل إضافية (More details)')}</span>
                    </button>
                    <button
                        type="submit"
                        data-testid="quick-treatment-save-button"
                        disabled={isSaving}
                        className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60"
                    >
                        <Check className="h-4 w-4" aria-hidden="true" />
                        <span>{isSaving ? t('quick_treatment_sheet.saving_button', 'جاري الحفظ...') : t('quick_treatment_sheet.save_button', 'حفظ')}</span>
                    </button>
                </div>
            </form>
        </DentixBottomSheet>
    );
}

QuickTreatmentSheet.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    onOpenDetails: PropTypes.func.isRequired,
    initialData: PropTypes.object,
    procedures: PropTypes.arrayOf(PropTypes.object),
};
