import { useState } from 'react';
import PropTypes from 'prop-types';
import { Ruler, Save, CheckCircle2, History } from 'lucide-react';
import { REFERENCE_POINTS, MAF_SIZES } from './canalAnatomy';

const FILE_SIZES = [...new Set(MAF_SIZES.map((size) => size.split(' / ')[0]))];

/**
 * Working Length Structured Entry (Slice S20 / G10-M10).
 * Structured recording of root canal lengths, reference points, and MAF sizes chairside.
 */
export default function WorkingLengthEntryTable({
    toothKey,
    selectedCanals = [],
    recordedObservations = [],
    onSaveMeasurement,
    isLoading = false,
    t = (k, f) => f || k,
}) {
    // Keep each canal's length, file size, taper and notes independent.
    const [drafts, setDrafts] = useState({});
    const [savingCanal, setSavingCanal] = useState(null);
    const [saveError, setSaveError] = useState(false);

    const getDraft = (canalId, defaultRef) => {
        return (
            drafts[canalId] || {
                length_mm: '',
                reference_point: defaultRef || REFERENCE_POINTS[0],
                maf: MAF_SIZES[1].split(' / ')[0],
                taper: '',
                notes: '',
            }
        );
    };

    const handleUpdateField = (canalId, field, value, defaultRef) => {
        setDrafts((prev) => {
            const current = prev[canalId] || {
                length_mm: '',
                reference_point: defaultRef || REFERENCE_POINTS[0],
                maf: MAF_SIZES[1].split(' / ')[0],
                taper: '',
                notes: '',
            };
            return {
                ...prev,
                [canalId]: {
                    ...current,
                    [field]: value,
                },
            };
        });
    };

    const handleSave = async (canal) => {
        if (savingCanal) return;
        const draft = getDraft(canal.canalId);
        const lengthNum = Number.parseFloat(draft.length_mm);
        const invalidTaper = draft.taper !== '' && (!Number.isFinite(Number(draft.taper)) || Number(draft.taper) <= 0);
        if (!Number.isFinite(lengthNum) || lengthNum <= 0 || invalidTaper) {
            setSaveError(true);
            return;
        }

        setSavingCanal(canal.canalId);
        setSaveError(false);
        try {
            const result = await onSaveMeasurement({
                canal_id: canal.canalId,
                root_id: canal.rootId,
                tooth_key: String(toothKey),
                length_mm: lengthNum,
                reference_point: draft.reference_point,
                maf: draft.maf,
                ...(draft.taper !== '' ? { taper: Number(draft.taper) } : {}),
                notes: draft.notes?.trim() || null,
            });
            if (result === false) return;

            // Clear only notes after a confirmed save; retain measurement settings.
            setDrafts((prev) => ({
                ...prev,
                [canal.canalId]: { ...prev[canal.canalId], notes: '' },
            }));
        } catch {
            setSaveError(true);
        } finally {
            setSavingCanal(null);
        }
    };

    if (selectedCanals.length === 0) {
        return (
            <div
                data-testid="working-length-empty"
                className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400"
            >
                {t('care_session.no_canals_selected_msg', 'Select one or more canals above to record working lengths.')}
            </div>
        );
    }

    return (
        <div
            data-testid="working-length-table"
            className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
            {saveError && <p role="alert" className="text-xs text-danger">{t('care_session.measurement_save_failed', 'Measurement was not saved. Your entries are kept; please try again.')}</p>}
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 dark:border-slate-800">
                <div className="flex items-center gap-2">
                    <Ruler className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                    <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                        {t('care_session.working_length_title', 'Working Length & Apex Measurements')}
                    </h4>
                </div>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                    {t('care_sessions.tooth', 'Tooth')} {toothKey}
                </span>
            </div>

            <div className="space-y-3">
                {selectedCanals.map((canal) => {
                    const draft = getDraft(canal.canalId);
                    // Find previously recorded measurements for this canal
                    const canalObservations = (recordedObservations || []).filter(
                        (o) =>
                            o.observation_code === 'working_length' &&
                            String(o.tooth_key) === String(toothKey) &&
                            o.canal_id?.toLowerCase() === canal.canalId?.toLowerCase()
                    );
                    const latestObs = canalObservations[canalObservations.length - 1];

                    return (
                        <div
                            key={`${canal.rootId}-${canal.canalId}`}
                            data-testid={`canal-entry-row-${canal.canalId}`}
                            className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 transition-colors dark:border-slate-800 dark:bg-slate-800/40"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2 pb-2">
                                <div className="flex items-center gap-2">
                                    <span className="rounded-md bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                                        {t('care_session.canal_label', 'Canal')} {canal.canalId}
                                    </span>
                                    <span className="text-xs text-slate-500 dark:text-slate-400">
                                        ({t(`care_session.roots.${canal.rootId}`, canal.rootId)})
                                    </span>
                                </div>

                                {latestObs && (
                                    <div
                                        data-testid={`latest-measurement-${canal.canalId}`}
                                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400"
                                    >
                                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                                        <span>
                                            {t('care_session.recorded_label', 'Recorded')}: {latestObs.structured_value?.length_mm ?? latestObs.length_mm} mm
                                            ({latestObs.structured_value?.reference_point || latestObs.reference_point || 'Cusp'} / {latestObs.structured_value?.maf || latestObs.maf || 'MAF'})
                                            {latestObs.structured_value?.taper != null && <span> · {t('care_session.maf_taper', 'Master file taper')}: {latestObs.structured_value.taper}</span>}
                                        </span>
                                    </div>
                                )}
                            </div>

                            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
                                <div>
                                    <label
                                        htmlFor={`length-${canal.canalId}`}
                                        className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400"
                                    >
                                        {t('care_session.length_mm', 'Length (mm)')} *
                                    </label>
                                    <input
                                        id={`length-${canal.canalId}`}
                                        type="number"
                                        step="0.5"
                                        min="1"
                                        max="40"
                                        value={draft.length_mm}
                                        onChange={(e) =>
                                            handleUpdateField(canal.canalId, 'length_mm', e.target.value)
                                        }
                                        placeholder="21.5"
                                        data-testid={`input-length-${canal.canalId}`}
                                        className="mt-1 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                    />
                                </div>

                                <div>
                                    <label
                                        htmlFor={`ref-${canal.canalId}`}
                                        className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400"
                                    >
                                        {t('care_session.ref_point', 'Reference Point')}
                                    </label>
                                    <select
                                        id={`ref-${canal.canalId}`}
                                        value={draft.reference_point}
                                        onChange={(e) =>
                                            handleUpdateField(canal.canalId, 'reference_point', e.target.value)
                                        }
                                        data-testid={`select-ref-${canal.canalId}`}
                                        className="mt-1 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                    >
                                        {REFERENCE_POINTS.map((rp) => (
                                            <option key={rp} value={rp}>
                                                {t(`care_session.reference_points.${rp.toLowerCase().replaceAll(' ', '_')}`, rp)}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label
                                        htmlFor={`maf-${canal.canalId}`}
                                        className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400"
                                    >
                                        {t('care_session.maf_size', 'Master Apical File (MAF)')}
                                    </label>
                                    <select
                                        id={`maf-${canal.canalId}`}
                                        value={draft.maf}
                                        onChange={(e) =>
                                            handleUpdateField(canal.canalId, 'maf', e.target.value)
                                        }
                                        data-testid={`select-maf-${canal.canalId}`}
                                        className="mt-1 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                    >
                                        {FILE_SIZES.map((size) => (
                                            <option key={size} value={size}>
                                                {size}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label htmlFor={`taper-${canal.canalId}`} className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                                        {t('care_session.maf_taper', 'Master file taper')}
                                    </label>
                                    <input
                                        id={`taper-${canal.canalId}`}
                                        data-testid={`input-taper-${canal.canalId}`}
                                        type="number"
                                        min="0"
                                        step="any"
                                        placeholder="0.04"
                                        value={draft.taper}
                                        onChange={(e) => handleUpdateField(canal.canalId, 'taper', e.target.value)}
                                        className="mt-1 min-h-10 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-900"
                                    />
                                </div>
                                <div className="flex items-end">
                                    <button
                                        type="button"
                                        onClick={() => handleSave(canal)}
                                        disabled={!draft.length_mm || isLoading || savingCanal !== null}
                                        data-testid={`btn-save-measurement-${canal.canalId}`}
                                        className="inline-flex min-h-10 w-full items-center justify-center gap-1.5 rounded-lg border border-emerald-600 bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:opacity-50"
                                    >
                                        <Save className="h-3.5 w-3.5" aria-hidden="true" />
                                        <span>{t('care_session.save_measurement', 'Save Length')}</span>
                                    </button>
                                </div>
                            </div>

                            {/* Optional notes */}
                            <div className="mt-2">
                                <input
                                    type="text"
                                    value={draft.notes}
                                    onChange={(e) =>
                                        handleUpdateField(canal.canalId, 'notes', e.target.value)
                                    }
                                    placeholder={t('care_session.canal_notes_placeholder', 'Notes (e.g. curvature, calcification, apical tugback)...')}
                                    data-testid={`input-notes-${canal.canalId}`}
                                    className="min-h-9 w-full rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-700 placeholder-slate-400 focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                                />
                            </div>

                            {/* Measurement history for canal */}
                            {canalObservations.length > 1 && (
                                <div className="mt-2 flex items-center gap-2 border-t border-slate-200/60 pt-1.5 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">
                                    <History className="h-3 w-3" aria-hidden="true" />
                                    <span>{t('care_session.prior_readings', 'Prior readings')}:</span>
                                    {canalObservations.slice(0, -1).map((obs, idx) => (
                                        <span key={obs.id || idx} className="rounded bg-slate-200/70 px-1.5 py-0.5 dark:bg-slate-700">
                                            {obs.structured_value?.length_mm || obs.length_mm} mm
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

WorkingLengthEntryTable.propTypes = {
    toothKey: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    selectedCanals: PropTypes.arrayOf(
        PropTypes.shape({
            canalId: PropTypes.string.isRequired,
            rootId: PropTypes.string.isRequired,
        })
    ).isRequired,
    recordedObservations: PropTypes.array,
    onSaveMeasurement: PropTypes.func.isRequired,
    isLoading: PropTypes.bool,
    t: PropTypes.func,
};
