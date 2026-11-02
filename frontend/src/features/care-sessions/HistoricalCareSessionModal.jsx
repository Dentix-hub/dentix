import { useState, useMemo, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import PropTypes from 'prop-types';
import { Calendar, User, FileText, AlertCircle, History, Save } from 'lucide-react';
import { Button, Modal, Badge } from '@/shared/ui';
import { startCareSession } from '@/api/patients';
import CanalTargetSelector from './CanalTargetSelector';
import WorkingLengthEntryTable from './WorkingLengthEntryTable';
import ObservationSummary from './ObservationSummary';
import { suggestProcedureChartTemplate } from '@/features/clinical-chart/domain/procedureChartAppearance';

/**
 * Historical Care Session Entry Modal (Requirement 4).
 * Allows doctors to record a retrospective visit with distinct actual visit date,
 * performing clinician, associated procedures, and notes.
 * Directly completes the historical visit without creating an active session conflict.
 */
export default function HistoricalCareSessionModal({
    isOpen = false,
    onClose,
    patientId,
    patientWorkItems = [],
    doctors = [],
    currentUserId = null,
    nativeWritesEnabled = true,
    onRecheckNativeWrites,
    onSuccess,
    t: customT,
}) {
    const { t: translate } = useTranslation();
    const t = customT || translate;
    // Current local ISO date-time string truncated to minutes (YYYY-MM-DDTHH:MM)
    const nowIso = useMemo(() => {
        const d = new Date();
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().slice(0, 16);
    }, []);

    const [actualVisitDate, setActualVisitDate] = useState(() => {
        // Default to yesterday at 10:00 AM
        const d = new Date();
        d.setDate(d.getDate() - 1);
        d.setHours(10, 0, 0, 0);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().slice(0, 16);
    });

    const [providerUserId, setProviderUserId] = useState(() => {
        return doctors.some((doctor) => doctor.id === currentUserId) ? String(currentUserId) : '';
    });

    const [selectedWorkItemIds, setSelectedWorkItemIds] = useState(() => {
        return patientWorkItems.length > 0 ? [patientWorkItems[0].id] : [];
    });

    const [notes, setNotes] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMsg, setErrorMsg] = useState(null);
    const [nativeWritesRejected, setNativeWritesRejected] = useState(false);
    const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
    const recordingUnavailable = !nativeWritesEnabled || nativeWritesRejected;
    const recheckAvailability = async () => {
        setIsCheckingAvailability(true);
        try {
            setNativeWritesRejected((await onRecheckNativeWrites()) !== true);
        } catch {
            setNativeWritesRejected(true);
        } finally {
            setIsCheckingAvailability(false);
        }
    };
    const measurementEditorRef = useRef(null);
    const submittingRef = useRef(false);

    // Historical Steps State
    const [steps, setSteps] = useState([]);
    const [newStepTitle, setNewStepTitle] = useState('');
    const [newStepNotes, setNewStepNotes] = useState('');

    // Historical Observations State
    const [observations, setObservations] = useState([]);
    const [obsToothKey, setObsToothKey] = useState('');
    const [obsCode, setObsCode] = useState('measurement');
    const [obsValue, setObsValue] = useState('');
    const [obsCanal, setObsCanal] = useState('');
    const [obsNotes, setObsNotes] = useState('');
    const [observationError, setObservationError] = useState(null);
    const [selectedCanals, setSelectedCanals] = useState([]);
    const [entryWorkItemId, setEntryWorkItemId] = useState('');
    const selectedProcedures = patientWorkItems.filter((item) => selectedWorkItemIds.includes(item.id));
    const entryProcedureId = selectedWorkItemIds.includes(Number(entryWorkItemId))
        ? Number(entryWorkItemId)
        : selectedWorkItemIds[0];
    const entryToothKey = useMemo(() => {
        const procedure = patientWorkItems.find((item) => item.id === entryProcedureId);
        const teeth = [
            ...new Set(
                (procedure?.targets || [])
                    .map((target) => target.tooth_key)
                    .filter(Boolean)
                    .map(String),
            ),
        ];
        return procedure?.tooth_number ? String(procedure.tooth_number) : teeth.length === 1 ? teeth[0] : '';
    }, [entryProcedureId, patientWorkItems]);
    useEffect(() => {
        setObsToothKey(entryToothKey);
    }, [entryProcedureId, entryToothKey]);
    const entryCode = patientWorkItems.find((item) => item.id === entryProcedureId)?.code || '';
    const isEndo =
        entryCode === 'ENDO_RCT' || suggestProcedureChartTemplate(entryCode)?.template === 'ENDO_RCT';
    useEffect(() => {
        setObsCode(isEndo ? 'working_length' : 'measurement');
    }, [entryProcedureId, isEndo]);
    useEffect(() => {
        setSelectedCanals([]);
    }, [entryProcedureId, obsToothKey]);
    const toggleCanal = (canal) =>
        setSelectedCanals((previous) =>
            previous.some((item) => item.canalId === canal.canalId && item.rootId === canal.rootId)
                ? previous.filter((item) => item.canalId !== canal.canalId || item.rootId !== canal.rootId)
                : [...previous, canal],
        );
    const canalObservation = (measurement) => ({
        observation_code: 'working_length',
        work_item_id: entryProcedureId,
        tooth_key: obsToothKey,
        canal_id: measurement.canal_id,
        value: String(measurement.length_mm),
        notes: measurement.notes,
        structured_value: {
            length_mm: measurement.length_mm,
            canal_id: measurement.canal_id,
            root_id: measurement.root_id,
            reference_point: measurement.reference_point,
            maf: measurement.maf,
            ...(measurement.taper != null ? { taper: measurement.taper } : {}),
        },
    });
    const addCanalMeasurement = (measurement) => {
        if (!entryProcedureId || !obsToothKey) return false;
        setObservations((previous) => [...previous, canalObservation(measurement)]);
        return true;
    };
    const procedureLabel = (id) => {
        const item = patientWorkItems.find((candidate) => candidate.id === id);
        return item?.title || item?.code || `Procedure #${id}`;
    };

    const toggleWorkItem = (id) => {
        if (
            selectedWorkItemIds.includes(id) &&
            (steps.some((s) => s.work_item_id === id) || observations.some((o) => o.work_item_id === id))
        ) {
            setErrorMsg(
                t(
                    'care_session.remove_documentation_first',
                    'Remove this procedure’s steps and observations before deselecting it.',
                ),
            );
            return;
        }
        setErrorMsg(null);
        setSelectedWorkItemIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
    };

    const handleAddStep = (e) => {
        e?.preventDefault();
        if (!newStepTitle.trim() || !entryProcedureId) return;
        const title = newStepTitle.trim();
        setSteps((prev) => [
            ...prev,
            {
                title,
                notes: newStepNotes.trim() || null,
                status: 'completed',
                work_item_id: entryProcedureId,
            },
        ]);
        setNewStepTitle('');
        setNewStepNotes('');
    };

    const handleRemoveStep = (index) => {
        setSteps((prev) => prev.filter((_, i) => i !== index));
    };

    const handleAddObservation = (e) => {
        e?.preventDefault();
        if (!obsValue.trim() || !entryProcedureId) {
            setObservationError(
                t(
                    'care_session.observation_value_required',
                    'Enter an observation value and select its procedure before adding it.',
                ),
            );
            return;
        }
        const isLength = obsCode === 'working_length';
        const numVal = isLength ? Number(obsValue) : undefined;
        if (isLength && (!Number.isFinite(numVal) || numVal <= 0)) {
            setObservationError(t('care_session.invalid_length', 'Enter a positive numeric working length.'));
            return;
        }
        setObservationError(null);
        const canal = obsCanal.trim() || null;
        setObservations((prev) => [
            ...prev,
            {
                observation_code: obsCode,
                tooth_key: obsToothKey.trim() || null,
                canal_id: canal,
                value: obsValue.trim(),
                structured_value: isLength
                    ? {
                          length_mm: !Number.isNaN(numVal) ? numVal : undefined,
                          value: obsValue.trim(),
                          ...(canal ? { canal_id: canal } : {}),
                      }
                    : {
                          value: obsValue.trim(),
                          ...(canal ? { canal_id: canal } : {}),
                      },
                notes: obsNotes.trim() || null,
                work_item_id: entryProcedureId,
            },
        ]);
        setObsValue('');
        setObsCanal('');
        setObsNotes('');
    };

    const handleRemoveObservation = (index) => {
        setObservations((prev) => prev.filter((_, i) => i !== index));
    };

    const validate = () => {
        if (!actualVisitDate || Number.isNaN(new Date(actualVisitDate).getTime())) {
            return t('care_session.error_visit_date_required', 'Actual visit date is required.');
        }
        const selectedDate = new Date(actualVisitDate);
        if (selectedDate > new Date()) {
            return t('care_session.error_future_date', 'Historical visit date cannot be in the future.');
        }
        if (selectedWorkItemIds.length === 0) {
            return t(
                'care_session.error_select_procedure',
                'Please select at least one procedure worked on during this visit.',
            );
        }
        return null;
    };

    const handleSubmit = async (e) => {
        e?.preventDefault();
        if (submittingRef.current || recordingUnavailable) return;
        const err = validate();
        if (err) {
            setErrorMsg(err);
            return;
        }
        let pendingMeasurements;
        try {
            pendingMeasurements = measurementEditorRef.current?.collectPending() || [];
        } catch (validationError) {
            setErrorMsg(validationError.message);
            return;
        }
        if (pendingMeasurements.length && (!entryProcedureId || !obsToothKey)) {
            setErrorMsg(
                t(
                    'care_session.measurement_tooth_required',
                    'Select a tooth for this procedure before recording measurements.',
                ),
            );
            return;
        }
        const visitObservations = [...observations, ...pendingMeasurements.map(canalObservation)];
        if (obsCode !== 'working_length' && (obsValue.trim() || obsCanal.trim())) {
            if (!obsValue.trim() || !entryProcedureId) {
                setErrorMsg(
                    t(
                        'care_session.observation_value_required',
                        'Enter an observation value and select its procedure before adding it.',
                    ),
                );
                return;
            }
            visitObservations.push({
                observation_code: obsCode,
                work_item_id: entryProcedureId,
                tooth_key: obsToothKey || null,
                canal_id: obsCanal.trim() || null,
                structured_value: { value: obsValue.trim() },
                notes: obsNotes.trim() || null,
            });
        }
        setErrorMsg(null);
        submittingRef.current = true;
        setIsSubmitting(true);

        const payload = {
            is_historical: true,
            actual_visit_date: new Date(actualVisitDate).toISOString(),
            provider_user_id: providerUserId ? Number(providerUserId) : null,
            work_item_ids: selectedWorkItemIds,
            notes: notes.trim() || null,
            historical_steps: [
                ...steps,
                ...(newStepTitle.trim()
                    ? [
                          {
                              title: newStepTitle.trim(),
                              notes: newStepNotes.trim() || null,
                              work_item_id: entryProcedureId,
                          },
                      ]
                    : []),
            ].map((s, idx) => {
                const title = s.title.trim();
                return {
                    step_order: idx + 1,
                    title,
                    status: s.status || 'completed',
                    notes: s.notes || null,
                    work_item_id: s.work_item_id || selectedWorkItemIds[0],
                };
            }),
            historical_observations: visitObservations.map((o) => {
                const canal = o.canal_id || null;
                return {
                    observation_code: o.observation_code || 'measurement',
                    tooth_key: o.tooth_key || null,
                    canal_id: canal,
                    structured_value: {
                        ...(o.structured_value || {}),
                        value: o.value || o.structured_value?.value,
                        ...(canal ? { canal_id: canal } : {}),
                    },
                    notes: o.notes || null,
                    work_item_id: o.work_item_id || selectedWorkItemIds[0],
                };
            }),
        };

        try {
            await startCareSession(patientId, payload);
            if (onSuccess) onSuccess();
            onClose();
        } catch (err) {
            const detail = err?.response?.data?.detail;
            if (err?.response?.status === 404 && detail === 'Clinical native writes are disabled') {
                setNativeWritesRejected(true);
                return;
            }
            setErrorMsg(
                Array.isArray(detail)
                    ? detail
                          .map(
                              (item) =>
                                  `${(item.loc || []).filter((part) => part !== 'body').join('.')}: ${item.msg}`,
                          )
                          .join(' · ')
                    : typeof detail === 'string'
                      ? detail
                      : detail?.message ||
                        err.message ||
                        t(
                            'care_session.record_failed',
                            'Could not record the session. Your entries are kept; please try again.',
                        ),
            );
        } finally {
            submittingRef.current = false;
            setIsSubmitting(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('care_session.record_historical_visit_title', 'Record Session')}
            size="lg"
        >
            <form
                onSubmit={handleSubmit}
                data-testid="historical-care-session-form"
                noValidate
                className="min-w-0 space-y-5"
            >
                {/* Information Header Banner */}
                <div className="flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50/50 p-4 dark:border-blue-900/40 dark:bg-blue-950/20">
                    <History className="h-5 w-5 shrink-0 text-primary mt-0.5" />
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-text-primary">
                                {t('care_session.historical_entry_badge', 'Retrospective Documentation')}
                            </span>
                            <Badge variant="primary" size="xs">
                                {t('care_session.past_visit_badge', 'Past visit')}
                            </Badge>
                        </div>
                        <p className="text-xs text-text-secondary mt-1">
                            {t(
                                'care_session.historical_entry_desc',
                                'Documents care previously delivered. The visit is finalized immediately and will not interrupt any active chairside visit.',
                            )}
                        </p>
                    </div>
                </div>

                {/* Date & Doctor Selection */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                            <Calendar className="h-3.5 w-3.5 text-primary" />
                            <span>{t('care_session.actual_visit_date', 'Actual Visit Date & Time')} *</span>
                        </label>
                        <input
                            type="datetime-local"
                            value={actualVisitDate}
                            max={nowIso}
                            onChange={(e) => setActualVisitDate(e.target.value)}
                            data-testid="input-historical-visit-date"
                            required
                            className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                            <User className="h-3.5 w-3.5 text-primary" />
                            <span>{t('care_session.treating_provider', 'Treating Provider')}</span>
                        </label>
                        <select
                            value={providerUserId}
                            onChange={(e) => setProviderUserId(e.target.value)}
                            data-testid="select-historical-provider"
                            className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                        >
                            <option value="">
                                {t('care_session.select_provider_prompt', '-- Select Doctor --')}
                            </option>
                            {doctors.map((d) => (
                                <option key={d.id} value={d.id}>
                                    {d.full_name || d.name || d.username}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Procedure Association Checkboxes */}
                <div className="space-y-2">
                    <label className="block text-xs font-bold text-text-primary">
                        {t('care_session.associated_procedures', 'Procedures Addressed During This Visit')} *
                    </label>

                    {patientWorkItems.length === 0 ? (
                        <div className="rounded-xl border border-border bg-surface p-4 text-center text-xs text-text-secondary">
                            {t(
                                'care_session.no_patient_procedures',
                                'No clinical procedures found for this patient.',
                            )}
                        </div>
                    ) : (
                        <div className="max-h-48 overflow-y-auto rounded-xl border border-border bg-surface p-2 space-y-1">
                            {patientWorkItems.map((wi) => {
                                const isChecked = selectedWorkItemIds.includes(wi.id);
                                return (
                                    <label
                                        key={wi.id}
                                        data-testid={`checkbox-proc-${wi.id}`}
                                        className={`flex items-center justify-between gap-3 rounded-lg p-2 text-xs cursor-pointer transition-colors ${
                                            isChecked
                                                ? 'bg-primary/10 text-primary font-bold'
                                                : 'hover:bg-surface-elevated text-text-primary'
                                        }`}
                                    >
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={isChecked}
                                                onChange={() => toggleWorkItem(wi.id)}
                                                className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                                            />
                                            <span>
                                                {wi.title ||
                                                    wi.display_label ||
                                                    wi.name ||
                                                    wi.code ||
                                                    `Procedure #${wi.id}`}
                                            </span>
                                        </div>
                                        {wi.targets?.[0]?.tooth_key && (
                                            <Badge variant="neutral" size="xs">
                                                {t('care_sessions.tooth', 'Tooth')} #{wi.targets[0].tooth_key}
                                            </Badge>
                                        )}
                                    </label>
                                );
                            })}
                        </div>
                    )}
                </div>

                <label className="block space-y-1 text-xs font-bold text-text-primary">
                    <span>
                        {t('care_session.document_procedure', 'Procedure for new steps and observations')}
                    </span>
                    <select
                        value={entryProcedureId || ''}
                        onChange={(e) => setEntryWorkItemId(e.target.value)}
                        data-testid="historical-entry-procedure"
                        className="w-full rounded-xl border border-border bg-surface p-2"
                    >
                        {selectedProcedures.map((item) => (
                            <option key={item.id} value={item.id}>
                                {procedureLabel(item.id)}
                            </option>
                        ))}
                    </select>
                </label>

                {/* Delivered Steps Section */}
                <div className="space-y-2 rounded-xl border border-border bg-surface/50 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <label className="text-xs font-bold text-text-primary">
                            {t('care_session.delivered_steps', 'Delivered Clinical Steps')}
                        </label>
                        <span className="text-[10px] text-text-secondary">
                            {steps.length} {t('care_session.steps_added', 'steps recorded')}
                        </span>
                    </div>

                    {steps.length > 0 && (
                        <div className="space-y-1 max-h-36 overflow-y-auto">
                            {steps.map((st, idx) => (
                                <div
                                    key={idx}
                                    data-testid={`historical-step-item-${idx}`}
                                    className="flex items-center justify-between rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs"
                                >
                                    <div className="flex items-center gap-2">
                                        <Badge variant="success" size="xs">
                                            {t('care_session.step_completed', 'Completed')}
                                        </Badge>
                                        <span className="font-semibold text-text-primary">{st.title}</span>
                                        <span className="text-text-secondary">
                                            {procedureLabel(st.work_item_id)}
                                        </span>
                                        {st.notes && (
                                            <span className="text-text-secondary italic">({st.notes})</span>
                                        )}
                                    </div>
                                    <button
                                        type="button"
                                        data-testid={`btn-remove-step-${idx}`}
                                        onClick={() => handleRemoveStep(idx)}
                                        className="text-[11px] font-bold text-danger hover:underline"
                                    >
                                        {t('common.remove', 'Remove')}
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-2 pt-1">
                        <input
                            type="text"
                            value={newStepTitle}
                            onChange={(e) => setNewStepTitle(e.target.value)}
                            placeholder={t(
                                'care_session.step_title_placeholder',
                                'Step title (e.g. Access cavity, Instrumentation)',
                            )}
                            data-testid="input-historical-step-title"
                            className="sm:col-span-6 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary"
                        />
                        <input
                            type="text"
                            value={newStepNotes}
                            onChange={(e) => setNewStepNotes(e.target.value)}
                            placeholder={t('care_session.step_notes_placeholder', 'Optional notes')}
                            data-testid="input-historical-step-notes"
                            className="sm:col-span-4 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary"
                        />
                        <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={handleAddStep}
                            data-testid="btn-add-historical-step"
                            className="sm:col-span-2 text-xs"
                        >
                            + {t('common.add', 'Add')}
                        </Button>
                    </div>
                </div>

                {/* Measurements & Observations Section */}
                <div className="space-y-2 rounded-xl border border-border bg-surface/50 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <label className="text-xs font-bold text-text-primary">
                            {t(
                                'care_session.historical_measurements',
                                'Clinical Measurements & Observations',
                            )}
                        </label>
                        <span className="text-[10px] text-text-secondary">
                            {observations.length} {t('care_session.obs_added', 'measurements')}
                        </span>
                    </div>

                    <ObservationSummary
                        observations={observations}
                        onRemove={handleRemoveObservation}
                        procedureLabels={Object.fromEntries(
                            patientWorkItems.map((item) => [item.id, procedureLabel(item.id)]),
                        )}
                        testIdPrefix="historical-obs-item"
                        t={t}
                    />

                    <div className="grid grid-cols-2 sm:grid-cols-12 gap-2 pt-1">
                        <input
                            type="text"
                            value={obsToothKey}
                            onChange={(e) => setObsToothKey(e.target.value)}
                            placeholder={t('care_session.tooth_placeholder', 'Tooth # (e.g. 46)')}
                            data-testid="input-historical-obs-tooth"
                            className="sm:col-span-2 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary font-mono"
                        />
                        <select
                            value={obsCode}
                            onChange={(e) => setObsCode(e.target.value)}
                            data-testid="select-historical-obs-code"
                            className="sm:col-span-3 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary"
                        >
                            <option value="measurement">
                                {t('care_session.obs_measurement', 'Measurement')}
                            </option>
                            <option value="working_length">
                                {t('care_session.obs_working_length', 'Working Length')}
                            </option>
                            <option value="shade">{t('care_session.obs_shade', 'Shade')}</option>
                            <option value="vitality">{t('care_session.obs_vitality', 'Vitality')}</option>
                        </select>
                        {obsCode !== 'working_length' && (
                            <>
                                <input
                                    type="text"
                                    value={obsValue}
                                    onChange={(e) => setObsValue(e.target.value)}
                                    placeholder={t(
                                        'care_session.obs_val_placeholder',
                                        'Value (e.g. 21.5, A2)',
                                    )}
                                    data-testid="input-historical-obs-value"
                                    className="sm:col-span-3 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary"
                                />
                                <input
                                    type="text"
                                    value={obsCanal}
                                    onChange={(e) => setObsCanal(e.target.value)}
                                    placeholder={t('care_session.canal_placeholder', 'Canal (e.g. MB)')}
                                    data-testid="input-historical-obs-canal"
                                    className="sm:col-span-2 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-text-primary"
                                />
                                <Button
                                    type="button"
                                    variant="secondary"
                                    size="sm"
                                    onClick={handleAddObservation}
                                    data-testid="btn-add-historical-obs"
                                    className="col-span-2 sm:col-span-2 text-xs"
                                >
                                    + {t('common.add', 'Add')}
                                </Button>
                            </>
                        )}
                    </div>
                    {obsCode === 'working_length' && obsToothKey && (
                        <div key={`${entryProcedureId}-${obsToothKey}`} className="space-y-3">
                            <CanalTargetSelector
                                toothKey={obsToothKey}
                                selectedCanals={selectedCanals}
                                onToggleCanal={toggleCanal}
                                t={t}
                            />
                            <WorkingLengthEntryTable
                                ref={measurementEditorRef}
                                toothKey={obsToothKey}
                                selectedCanals={selectedCanals}
                                recordedObservations={observations.filter(
                                    (observation) => observation.work_item_id === entryProcedureId,
                                )}
                                onSaveMeasurement={addCanalMeasurement}
                                showRecorded={false}
                                isStaging
                                t={t}
                            />
                        </div>
                    )}
                </div>

                {observationError && (
                    <p role="alert" className="text-sm text-danger">
                        {observationError}
                    </p>
                )}

                {/* Clinical Notes */}
                <div className="space-y-1">
                    <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                        <FileText className="h-3.5 w-3.5 text-primary" />
                        <span>{t('care_session.visit_notes', 'Visit Clinical Notes & Findings')}</span>
                    </label>
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        data-testid="input-historical-notes"
                        rows={3}
                        placeholder={t(
                            'care_session.historical_notes_placeholder',
                            'Document treatment delivered, findings, anesthesia, materials...',
                        )}
                        className="w-full rounded-xl border border-border bg-surface p-3 text-xs text-text-primary focus:border-primary focus:outline-hidden"
                    />
                </div>

                {recordingUnavailable && (
                    <div role="alert" data-testid="native-session-unavailable" className="space-y-2 rounded-control border border-warning/20 bg-warning/10 p-3 text-sm text-text-primary">
                        <p>{t('care_session.native_writes_unavailable', 'Session recording is not enabled for this clinic. Ask the system administrator to enable clinical sessions, then check again.')}</p>
                        <p>{t('care_session.entries_kept_open', 'Your entries are kept in this form while it stays open.')}</p>
                        {onRecheckNativeWrites && (
                            <Button type="button" variant="outline" size="sm" onClick={recheckAvailability} disabled={isCheckingAvailability} data-testid="recheck-native-session">
                                {t('care_session.recheck_availability', 'Check again')}
                            </Button>
                        )}
                    </div>
                )}
                {errorMsg && (
                    <div
                        role="alert"
                        data-testid="historical-entry-error"
                        className="rounded-control border border-danger/20 bg-danger/10 p-3 text-sm text-danger"
                    >
                        <AlertCircle className="me-1 inline h-4 w-4" />
                        {errorMsg}
                    </div>
                )}
                <p className="text-xs text-text-secondary">
                    {t(
                        'care_session.measurement_type_help',
                        'General measurement records a value or note. Working Length records canal length in mm with file size, taper and reference point.',
                    )}
                </p>
                {/* Footer Buttons */}
                <div className="grid grid-cols-2 gap-2 border-t border-border pt-4 sm:flex sm:items-center sm:justify-end [&_button]:min-h-11">
                    <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
                        {t('common.cancel', 'Cancel')}
                    </Button>
                    <Button
                        variant="primary"
                        size="sm"
                        type="submit"
                        disabled={isSubmitting || recordingUnavailable}
                        data-testid="btn-submit-historical-session"
                        className="gap-1.5 font-bold"
                    >
                        <Save className="h-4 w-4" />
                        <span>
                            {isSubmitting
                                ? t('common.recording', 'Recording...')
                                : t('care_session.record_visit_btn', 'Record Session')}
                        </span>
                    </Button>
                </div>
            </form>
        </Modal>
    );
}

HistoricalCareSessionModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    patientWorkItems: PropTypes.array,
    doctors: PropTypes.array,
    currentUserId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    nativeWritesEnabled: PropTypes.bool,
    onRecheckNativeWrites: PropTypes.func,
    onSuccess: PropTypes.func,
    t: PropTypes.func,
};
