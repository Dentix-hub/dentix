import { useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { CheckCircle2, Ruler, Save } from 'lucide-react';
import { REFERENCE_POINTS, MAF_SIZES } from './canalAnatomy';
import ObservationSummary from './ObservationSummary';

const FILE_SIZES = [...new Set(MAF_SIZES.map((size) => size.split(' / ')[0]))];

/** One entry sheet and save action, while each canal retains its clinical identity. */
export default function WorkingLengthEntryTable({
    toothKey,
    selectedCanals = [],
    recordedObservations = [],
    onSaveMeasurement,
    isLoading = false,
    showRecorded = true,
    isStaging = false,
    onSavingChange,
    t = (key, fallback) => fallback || key,
}) {
    const [drafts, setDrafts] = useState({});
    const [savedSignatures, setSavedSignatures] = useState({});
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);
    const savingRef = useRef(false);
    const targetKey = (canal) => `${toothKey}:${canal.rootId}:${canal.canalId.toLowerCase()}`;
    const getDraft = (canal) =>
        drafts[targetKey(canal)] || {
            length_mm: '',
            reference_point: REFERENCE_POINTS[0],
            maf: '#25',
            taper: '',
            notes: '',
        };
    const payloadFor = (canal, draft) => ({
        canal_id: canal.canalId,
        root_id: canal.rootId,
        tooth_key: String(toothKey),
        length_mm: Number(draft.length_mm),
        reference_point: draft.reference_point,
        maf: draft.maf,
        ...(draft.taper !== '' ? { taper: Number(draft.taper) } : {}),
        notes: draft.notes.trim() || null,
    });
    const isSaved = (canal, draft) => {
        const payload = payloadFor(canal, draft);
        if (savedSignatures[targetKey(canal)] !== JSON.stringify(payload)) return false;
        // Removing a locally queued observation must make it possible to add it again.
        return (
            !isStaging ||
            recordedObservations.some((observation) => {
                const value = observation.structured_value || {};
                return (
                    observation.canal_id === payload.canal_id &&
                    String(observation.tooth_key) === payload.tooth_key &&
                    value.root_id === payload.root_id &&
                    value.length_mm === payload.length_mm &&
                    value.maf === payload.maf &&
                    value.taper === payload.taper &&
                    (observation.notes || null) === payload.notes
                );
            })
        );
    };
    const pending = selectedCanals.filter((canal) => {
        const draft = drafts[targetKey(canal)];
        return draft && !isSaved(canal, draft);
    });
    const update = (canal, field, value) => {
        const draft = getDraft(canal);
        setDrafts((previous) => ({ ...previous, [targetKey(canal)]: { ...draft, [field]: value } }));
        setError(null);
    };

    const saveAll = async () => {
        if (savingRef.current || isLoading || pending.length === 0) return;
        // Validate the entire entry before making the first request.
        for (const canal of pending) {
            const draft = getDraft(canal);
            if (
                !draft.length_mm ||
                !Number.isFinite(Number(draft.length_mm)) ||
                Number(draft.length_mm) <= 0
            ) {
                setError(
                    `${canal.canalId}: ${t('care_session.invalid_length', 'Enter a positive numeric working length.')}`,
                );
                return;
            }
            if (draft.taper !== '' && (!Number.isFinite(Number(draft.taper)) || Number(draft.taper) <= 0)) {
                setError(
                    `${canal.canalId}: ${t('care_session.invalid_taper', 'Enter a positive numeric taper.')}`,
                );
                return;
            }
        }
        savingRef.current = true;
        setIsSaving(true);
        onSavingChange?.(true);
        setError(null);
        try {
            for (const canal of pending) {
                const payload = payloadFor(canal, getDraft(canal));
                const result = await onSaveMeasurement(payload, { batch: true });
                if (result === false) throw new Error('MEASUREMENT_NOT_SAVED');
                // Remember successful rows so retry never records them a second time.
                setSavedSignatures((previous) => ({
                    ...previous,
                    [targetKey(canal)]: JSON.stringify(payload),
                }));
            }
        } catch {
            setError(
                t(
                    'care_session.canal_batch_retry',
                    'Some measurements could not be saved. Retry saves only the remaining entries.',
                ),
            );
        } finally {
            savingRef.current = false;
            setIsSaving(false);
            onSavingChange?.(false);
        }
    };

    if (selectedCanals.length === 0) {
        return (
            <p
                data-testid="working-length-empty"
                className="rounded-card border border-dashed border-border p-4 text-sm text-text-secondary"
            >
                {t(
                    'care_session.no_canals_selected_msg',
                    'Select one or more canals above to record working lengths.',
                )}
            </p>
        );
    }

    return (
        <section data-testid="working-length-table" className="min-w-0 space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                    <h4 className="flex items-center gap-2 text-sm font-bold text-text-primary">
                        <Ruler className="h-4 w-4 shrink-0 text-primary" />
                        {t('care_session.working_length_title', 'Working Length & Apex Measurements')}
                    </h4>
                    <p className="mt-1 text-xs text-text-secondary">
                        {t(
                            'care_session.canal_batch_hint',
                            'Enter the measurements for each canal, then save them together.',
                        )}
                    </p>
                </div>
                <span className="shrink-0 rounded-control bg-primary/10 px-2 py-1 text-xs font-bold text-primary">
                    {t('care_sessions.tooth', 'Tooth')} <bdi>{toothKey}</bdi>
                </span>
            </div>
            <div className="overflow-hidden rounded-card border border-border bg-surface">
                <table
                    className="w-full table-fixed text-start text-xs"
                    aria-label={t('care_session.canal_entry_table', 'Canal measurement entry')}
                >
                    <colgroup>
                        <col className="w-14 sm:w-20" />
                        <col />
                        <col />
                        <col />
                    </colgroup>
                    <thead className="bg-surface-subtle text-text-secondary">
                        <tr>
                            {[
                                t('care_session.canal_label', 'Canal'),
                                t('care_session.length_mm', 'Length (mm)'),
                                t('care_session.maf_size_short', 'File size'),
                                t('care_session.taper_short', 'Taper'),
                            ].map((label) => (
                                <th
                                    key={label}
                                    scope="col"
                                    className="px-1.5 py-3 text-start font-semibold sm:px-3"
                                >
                                    {label}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    {selectedCanals.map((canal) => {
                        const draft = getDraft(canal);
                        const key = targetKey(canal);
                        const saved = isSaved(canal, draft);
                        return (
                            <tbody
                                key={key}
                                data-testid={`canal-entry-row-${canal.canalId}`}
                                className="border-t border-border"
                            >
                                <tr>
                                    <th
                                        scope="row"
                                        className="px-1.5 pt-3 text-start align-middle font-bold text-primary sm:px-3"
                                    >
                                        <bdi>{canal.canalId}</bdi>
                                        {saved && (
                                            <CheckCircle2
                                                aria-label={t('care_session.measurement_saved', 'Saved')}
                                                className="mt-1 h-3.5 w-3.5 text-emerald-600"
                                            />
                                        )}
                                    </th>
                                    <td className="px-1 py-3 sm:px-2">
                                        <input
                                            aria-label={`${canal.canalId} ${t('care_session.length_mm', 'Length (mm)')}`}
                                            type="number"
                                            min="0"
                                            step="any"
                                            inputMode="decimal"
                                            dir="ltr"
                                            value={draft.length_mm}
                                            disabled={isSaving}
                                            onChange={(event) =>
                                                update(canal, 'length_mm', event.target.value)
                                            }
                                            data-testid={`input-length-${canal.canalId}`}
                                            placeholder="21.5"
                                            className="min-h-11 w-full min-w-0 rounded-control border border-border bg-surface px-2 text-center font-semibold text-text-primary focus:border-primary focus:outline-none"
                                        />
                                    </td>
                                    <td className="px-1 py-3 sm:px-2">
                                        <select
                                            aria-label={`${canal.canalId} ${t('care_session.maf_size', 'Master Apical File (MAF)')}`}
                                            dir="ltr"
                                            value={draft.maf}
                                            disabled={isSaving}
                                            onChange={(event) => update(canal, 'maf', event.target.value)}
                                            data-testid={`select-maf-${canal.canalId}`}
                                            className="min-h-11 w-full min-w-0 rounded-control border border-border bg-surface px-1 text-text-primary"
                                        >
                                            {FILE_SIZES.map((size) => (
                                                <option key={size} value={size}>
                                                    {size}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="px-1 py-3 sm:px-2">
                                        <input
                                            aria-label={`${canal.canalId} ${t('care_session.maf_taper', 'Master file taper')}`}
                                            type="number"
                                            min="0"
                                            step="any"
                                            inputMode="decimal"
                                            dir="ltr"
                                            value={draft.taper}
                                            disabled={isSaving}
                                            onChange={(event) => update(canal, 'taper', event.target.value)}
                                            data-testid={`input-taper-${canal.canalId}`}
                                            placeholder="0.04"
                                            className="min-h-11 w-full min-w-0 rounded-control border border-border bg-surface px-2 text-center text-text-primary"
                                        />
                                    </td>
                                </tr>
                                <tr>
                                    <td colSpan={4} className="px-3 pb-3">
                                        <div className="grid min-w-0 gap-2 sm:grid-cols-2">
                                            <label className="min-w-0 space-y-1 text-text-secondary">
                                                <span>
                                                    {t('care_session.ref_point', 'Reference Point')} ·{' '}
                                                    {t(`care_session.roots.${canal.rootId}`, canal.rootId)}
                                                </span>
                                                <select
                                                    aria-label={`${canal.canalId} ${t('care_session.ref_point', 'Reference Point')}`}
                                                    value={draft.reference_point}
                                                    disabled={isSaving}
                                                    onChange={(event) =>
                                                        update(canal, 'reference_point', event.target.value)
                                                    }
                                                    data-testid={`select-ref-${canal.canalId}`}
                                                    className="min-h-10 w-full min-w-0 rounded-control border border-border bg-surface px-2 text-text-primary"
                                                >
                                                    {REFERENCE_POINTS.map((point) => (
                                                        <option key={point} value={point}>
                                                            {t(
                                                                `care_session.reference_points.${point.toLowerCase().replaceAll(' ', '_')}`,
                                                                point,
                                                            )}
                                                        </option>
                                                    ))}
                                                </select>
                                            </label>
                                            <label className="min-w-0 space-y-1 text-text-secondary">
                                                <span>
                                                    {t('care_session.canal_notes_label', 'Canal notes')}
                                                </span>
                                                <input
                                                    type="text"
                                                    aria-label={`${canal.canalId} ${t('care_session.canal_notes_label', 'Canal notes')}`}
                                                    value={draft.notes}
                                                    disabled={isSaving}
                                                    onChange={(event) =>
                                                        update(canal, 'notes', event.target.value)
                                                    }
                                                    data-testid={`input-notes-${canal.canalId}`}
                                                    placeholder={t(
                                                        'care_session.canal_notes_placeholder',
                                                        'Notes (e.g. curvature, calcification, apical tugback)...',
                                                    )}
                                                    className="min-h-10 w-full min-w-0 rounded-control border border-border bg-surface px-2 text-text-primary"
                                                />
                                            </label>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        );
                    })}
                </table>
            </div>
            {error && (
                <p
                    role="alert"
                    className="rounded-control bg-danger/10 p-3 text-xs font-semibold text-danger"
                >
                    {error}
                </p>
            )}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <p role="status" className="text-xs text-text-secondary">
                    {isSaving
                        ? t('care_session.saving_measurements', 'Saving measurements…')
                        : pending.length
                          ? `${pending.length} ${t('care_session.measurements_pending', 'measurements ready to save')}`
                          : t('care_session.no_pending_measurements', 'No unsaved measurements')}
                </p>
                <button
                    type="button"
                    onClick={saveAll}
                    disabled={isLoading || isSaving || !pending.length}
                    aria-busy={isSaving}
                    data-testid="save-canal-measurements"
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-control bg-primary px-4 py-2 text-sm font-bold text-white hover:bg-primary-600 disabled:opacity-50"
                >
                    <Save className="h-4 w-4" />
                    {t('care_session.save_canal_measurements', 'Save canal measurements')}
                </button>
            </div>
            {showRecorded && recordedObservations.length > 0 && (
                <ObservationSummary observations={recordedObservations} t={t} />
            )}
        </section>
    );
}

WorkingLengthEntryTable.propTypes = {
    toothKey: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    selectedCanals: PropTypes.array.isRequired,
    recordedObservations: PropTypes.array,
    onSaveMeasurement: PropTypes.func.isRequired,
    isLoading: PropTypes.bool,
    showRecorded: PropTypes.bool,
    isStaging: PropTypes.bool,
    onSavingChange: PropTypes.func,
    t: PropTypes.func,
};
