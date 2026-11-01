import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
    CheckCircle,
    Clock,
    AlertCircle,
    FileText,
    Ruler,
    Loader2,
    CalendarPlus,
    Info,
    FlaskConical,
} from 'lucide-react';
import Modal from '@/shared/ui/Modal';
import { isLabReadyStep } from '@/features/clinical-chart/domain';
import LabHandoffSheet from './LabHandoffSheet';

/**
 * Compact Finish-Session Sheet (Slice S20 / G10-M11 & S22 / G11-M02, G11-M06..M08).
 * Compact chairside drawer/sheet to review steps, canal observations,
 * add finalization notes, optionally queue next-visit request for reception,
 * and complete the active care session.
 */
export default function FinishCareSessionSheet({
    isOpen,
    onClose,
    session,
    onFinishSession,
    isFinishing = false,
    draftData = null,
    onDraftChange = null,
    t = (k, f) => f || k,
}) {
    const [notes, setNotes] = useState(draftData?.notes ?? session?.notes ?? '');

    const steps = session?.steps || [];
    const observations = session?.observations || [];

    const completedSteps = steps.filter((s) => s.status === 'completed');
    const partialSteps = steps.filter((s) => s.status === 'partial');
    const pendingSteps = steps.filter((s) => s.status === 'pending');
    const skippedSteps = steps.filter((s) => s.status === 'skipped');

    const workingLengthObs = observations.filter(
        (o) => o.observation_code === 'working_length'
    );

    const extractedTooth =
        observations.find((o) => o.tooth_key)?.tooth_key ||
        steps.find((s) => s.work_item?.targets?.[0]?.tooth_key)?.work_item?.targets?.[0]?.tooth_key ||
        session?.tooth_key ||
        '';

    const firstRemainingStep = pendingSteps[0] || partialSteps[0];
    const associatedIds = [...new Set((session?.procedures || []).map((procedure) => procedure.work_item_id))];
    const primaryWorkItemId = firstRemainingStep?.work_item_id || associatedIds[0] || null;
    const procedureName = session?.procedures?.find((procedure) => procedure.work_item_id === primaryWorkItemId)?.template_snapshot?.title || firstRemainingStep?.work_item?.code || 'Dental care';
    const defaultReason = firstRemainingStep
        ? (extractedTooth
            ? `Tooth ${extractedTooth}: ${procedureName} - ${firstRemainingStep.title}`
            : `${procedureName} - ${firstRemainingStep.title}`)
        : (extractedTooth
            ? `Follow-up: Tooth ${extractedTooth}`
            : 'Dental Follow-up Visit');

    const isRctSession =
        steps.some((s) => (s.step_code || '').toLowerCase().includes('rct') || (s.title || '').toLowerCase().includes('canal')) ||
        observations.some((o) => o.observation_code === 'working_length');

    const defaultDuration = isRctSession ? 45 : 30;

    const [requestNextVisit, setRequestNextVisit] = useState(Boolean(draftData?.requestNextVisit));
    const [nextVisitReason, setNextVisitReason] = useState(draftData?.nextVisitReason ?? defaultReason);
    const [nextVisitDuration, setNextVisitDuration] = useState(draftData?.nextVisitDuration ?? defaultDuration);
    const [nextVisitNotes, setNextVisitNotes] = useState(draftData?.nextVisitNotes ?? '');
    const [isLabHandoffOpen, setIsLabHandoffOpen] = useState(false);
    const [nextVisitDate, setNextVisitDate] = useState(draftData?.nextVisitDate || '');

    // Sync from server draftData when recovered
    useEffect(() => {
        if (draftData) {
            if (typeof draftData.notes === 'string') {
                setNotes(draftData.notes);
            }
            if (typeof draftData.nextVisitNotes === 'string') {
                setNextVisitNotes(draftData.nextVisitNotes);
            }
            if (typeof draftData.nextVisitReason === 'string') {
                setNextVisitReason(draftData.nextVisitReason);
            }
            if (draftData.nextVisitDuration !== undefined) {
                setNextVisitDuration(draftData.nextVisitDuration);
            }
            if (draftData.requestNextVisit !== undefined) {
                setRequestNextVisit(Boolean(draftData.requestNextVisit));
            }
            if (typeof draftData.nextVisitDate === 'string') setNextVisitDate(draftData.nextVisitDate);
        }
    }, [draftData]);

    const handleNotesChange = (e) => {
        const val = e.target.value;
        setNotes(val);
        if (onDraftChange) {
            onDraftChange({ notes: val });
        }
    };

    const handleNextVisitReasonChange = (e) => {
        const val = e.target.value;
        setNextVisitReason(val);
        if (onDraftChange) {
            onDraftChange({ nextVisitReason: val });
        }
    };

    const handleNextVisitDurationChange = (dur) => {
        setNextVisitDuration(dur);
        if (onDraftChange) {
            onDraftChange({ nextVisitDuration: dur });
        }
    };

    const handleNextVisitNotesChange = (e) => {
        const val = e.target.value;
        setNextVisitNotes(val);
        if (onDraftChange) {
            onDraftChange({ nextVisitNotes: val });
        }
    };

    const handleToggleRequestNextVisit = (e) => {
        const val = e.target.checked;
        setRequestNextVisit(val);
        if (onDraftChange) {
            onDraftChange({ requestNextVisit: val });
        }
    };

    const hasLabReadyStep = steps.some(
        (s) => (s.status === 'completed' || s.status === 'in_progress') && isLabReadyStep(s.step_code)
    );

    if (!session) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        const payload = {
            notes: notes.trim() || undefined,
        };
        if (requestNextVisit && nextVisitReason.trim()) {
            payload.next_visit_request = {
                care_session_id: session.id,
                work_item_id: primaryWorkItemId,
                associated_work_item_ids: associatedIds,
                reason: nextVisitReason.trim(),
                suggested_duration_minutes: Number(nextVisitDuration) || 30,
                notes: nextVisitNotes.trim() || undefined,
            };
            if (nextVisitDate) payload.next_visit_request.preferred_time_window_start = new Date(nextVisitDate).toISOString();
        }
        const result = await onFinishSession(payload);
        if (result === false) return;
        setNotes('');
        onClose();
    };

    const formatStartTime = (isoString) => {
        if (!isoString) return '--';
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return isoString;
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('care_session.finish_sheet_title', 'Finish Care Session')}
            size="md"
        >
            <form onSubmit={handleSubmit} className="space-y-4" data-testid="finish-care-session-form">
                {/* Session Header Status */}
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/50">
                    <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" aria-hidden="true" />
                        <div>
                            <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                                Session #{session.id}
                            </span>
                            <span className="ms-2 text-xs text-slate-500 dark:text-slate-400">
                                Started: {formatStartTime(session.started_at)}
                            </span>
                        </div>
                    </div>
                    <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-bold text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                        {session.status}
                    </span>
                </div>

                {/* Steps Completion Breakdown */}
                <div className="space-y-2 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                            {t('care_session.steps_summary', 'Workflow Steps Breakdown')}
                        </span>
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                            {completedSteps.length + partialSteps.length}/{steps.length} {t('care_session.performed', 'addressed')}
                        </span>
                    </div>

                    <div className="grid grid-cols-4 gap-2 pt-1 text-center">
                        <div className="rounded-lg bg-emerald-50 p-2 dark:bg-emerald-950/30">
                            <div className="text-sm font-extrabold text-emerald-700 dark:text-emerald-400">
                                {completedSteps.length}
                            </div>
                            <div className="text-[10px] font-medium text-emerald-600 dark:text-emerald-500">
                                Completed
                            </div>
                        </div>
                        <div className="rounded-lg bg-amber-50 p-2 dark:bg-amber-950/30">
                            <div className="text-sm font-extrabold text-amber-700 dark:text-amber-400">
                                {partialSteps.length}
                            </div>
                            <div className="text-[10px] font-medium text-amber-600 dark:text-amber-500">
                                Partial
                            </div>
                        </div>
                        <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                            <div className="text-sm font-extrabold text-slate-700 dark:text-slate-300">
                                {pendingSteps.length}
                            </div>
                            <div className="text-[10px] font-medium text-slate-500 dark:text-slate-400">
                                Pending
                            </div>
                        </div>
                        <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                            <div className="text-sm font-extrabold text-slate-600 dark:text-slate-400">
                                {skippedSteps.length}
                            </div>
                            <div className="text-[10px] font-medium text-slate-500 dark:text-slate-400">
                                Skipped
                            </div>
                        </div>
                    </div>

                    {pendingSteps.length > 0 && (
                        <div className="mt-2 flex items-center gap-1.5 rounded-lg bg-amber-50/80 px-2.5 py-1.5 text-xs text-amber-800 dark:bg-amber-950/20 dark:text-amber-300">
                            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                            <span>
                                {pendingSteps.length} {t('care_session.uncompleted_notice', 'step(s) remain pending. Finishing will close the session.')}
                            </span>
                        </div>
                    )}
                </div>

                {/* Canal Observations Summary */}
                {workingLengthObs.length > 0 && (
                    <div className="space-y-2 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
                        <div className="flex items-center gap-1.5">
                            <Ruler className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                                {t('care_session.recorded_measurements', 'Recorded Canal Lengths')}
                            </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 pt-1" data-testid="finish-sheet-canal-measurements">
                            {workingLengthObs.map((obs) => {
                                const val = obs.structured_value || {};
                                return (
                                    <span
                                        key={obs.id}
                                        className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                                    >
                                        <span className="font-bold">{obs.canal_id || 'Canal'}:</span>
                                        <span>{val.length_mm ?? obs.length_mm} mm</span>
                                        {val.maf && <span className="text-[10px] opacity-75">({val.maf})</span>}
                                        {val.taper != null && <span>{t('care_session.maf_taper', 'Master file taper')}: {val.taper}</span>}
                                    </span>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Free Text Notes Entry (G10-M15) */}
                <div className="space-y-1.5">
                    <label
                        htmlFor="finish-session-notes"
                        className="flex items-center gap-1.5 text-xs font-bold text-slate-700 dark:text-slate-300"
                    >
                        <FileText className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
                        <span>{t('care_session.final_notes_label', 'Clinical Summary / Finalization Notes')}</span>
                    </label>
                    <textarea
                        id="finish-session-notes"
                        rows={3}
                        value={notes}
                        onChange={handleNotesChange}
                        placeholder={t(
                            'care_session.final_notes_placeholder',
                            'Document patient tolerance, clinical observations, or instructions for the next visit...'
                        )}
                        data-testid="finish-session-notes-input"
                        className="w-full rounded-xl border border-slate-300 bg-white p-3 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                    />
                </div>

                {/* Chairside Lab Handoff Trigger (Slice S28 / G12-M05, G12-M06) */}
                <div
                    className="flex items-center justify-between rounded-card border border-teal-200 bg-teal-50/50 p-3 dark:border-teal-900/40 dark:bg-teal-950/20"
                    data-testid="lab-handoff-trigger-section"
                >
                    <div className="flex items-center gap-2">
                        <FlaskConical className="h-4 w-4 text-teal-600 dark:text-teal-400" aria-hidden="true" />
                        <div>
                            <span className="text-xs font-bold text-teal-950 dark:text-teal-200">
                                {t('care_session.lab_handoff_label', 'Dental Lab Order')}
                            </span>
                            <p className="text-[11px] text-teal-800 dark:text-teal-300">
                                {hasLabReadyStep
                                    ? t('care_session.lab_ready_prompt', 'Preparation / impression step recorded — dispatch lab handoff.')
                                    : t('care_session.lab_optional_prompt', 'Dispatch 1-tap prosthetic prescription with non-duplicating billing.')}
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => setIsLabHandoffOpen(true)}
                        data-testid="open-lab-handoff-button"
                        className="inline-flex items-center gap-1.5 rounded-control bg-teal-600 px-3 py-1.5 text-xs font-bold text-white shadow-low hover:bg-teal-700"
                    >
                        <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
                        <span>{t('care_session.send_to_lab', 'Send to Lab')}</span>
                    </button>
                </div>

                {/* Chairside Next-Visit Request (Slice S22 / G11-M02, G11-M06, G11-M07, G11-M08) */}
                <div
                    className="space-y-3 rounded-xl border border-blue-200 bg-blue-50/40 p-3.5 dark:border-blue-900/40 dark:bg-blue-950/20"
                    data-testid="next-visit-request-section"
                >
                    <div className="flex items-center justify-between">
                        <label
                            htmlFor="toggle-request-next-visit"
                            className="flex cursor-pointer items-center gap-2 text-xs font-bold text-blue-900 dark:text-blue-300"
                        >
                            <CalendarPlus className="h-4 w-4 text-blue-600 dark:text-blue-400" aria-hidden="true" />
                            <span>{t('care_session.request_next_visit_label', 'Request Next Appointment for Reception')}</span>
                        </label>
                        <input
                            type="checkbox"
                            id="toggle-request-next-visit"
                            checked={requestNextVisit}
                            onChange={handleToggleRequestNextVisit}
                            data-testid="request-next-visit-toggle"
                            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900"
                        />
                    </div>

                    {requestNextVisit && (
                        <div className="space-y-3 pt-2 text-xs">
                            {/* Invariant G11-M08 Notice */}
                            <div
                                data-testid="no-auto-booking-badge"
                                className="flex items-center gap-1.5 rounded-lg border border-blue-200/80 bg-white/80 px-2.5 py-1.5 text-[11px] font-medium text-blue-800 dark:border-blue-900/60 dark:bg-slate-900/80 dark:text-blue-300"
                            >
                                <Info className="h-3.5 w-3.5 shrink-0 text-blue-600 dark:text-blue-400" aria-hidden="true" />
                                <span>
                                    {t(
                                        'care_session.no_auto_booking_notice',
                                        'Queued for reception scheduling. Invariant: No appointment is booked automatically.'
                                    )}
                                </span>
                            </div>

                            {/* Reason for Next Visit (G11-M06) */}
                            <div className="space-y-1">
                                <label
                                    htmlFor="next-visit-reason"
                                    className="block font-semibold text-slate-700 dark:text-slate-300"
                                >
                                    {t('care_session.next_visit_reason_label', 'Appointment Reason')}
                                </label>
                                <input
                                    type="text"
                                    id="next-visit-reason"
                                    value={nextVisitReason}
                                    onChange={handleNextVisitReasonChange}
                                    placeholder={t(
                                        'care_session.next_visit_reason_placeholder',
                                        'e.g. Tooth 46: Root Canal Treatment - Obturation'
                                    )}
                                    data-testid="next-visit-reason-input"
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>

                            <label className="block space-y-1 text-xs font-semibold text-slate-700 dark:text-slate-300">
                                <span>{t('care_session.preferred_follow_up_date', 'Preferred follow-up date and time (optional)')}</span>
                                <input type="datetime-local" data-testid="next-visit-date-input" value={nextVisitDate} onChange={(event) => {
                                    setNextVisitDate(event.target.value);
                                    onDraftChange?.({ nextVisitDate: event.target.value });
                                }} className="w-full rounded-lg border border-border bg-surface p-2" />
                            </label>

                            {/* Suggested Duration (G11-M07) */}
                            <div className="space-y-1">
                                <label className="block font-semibold text-slate-700 dark:text-slate-300">
                                    {t('care_session.suggested_duration_label', 'Suggested Duration')}
                                </label>
                                <div className="flex flex-wrap items-center gap-1.5" data-testid="next-visit-duration-chips">
                                    {[15, 30, 45, 60].map((dur) => (
                                        <button
                                            key={dur}
                                            type="button"
                                            onClick={() => handleNextVisitDurationChange(dur)}
                                            data-testid={`duration-chip-${dur}`}
                                            className={`rounded-lg px-2.5 py-1 text-xs font-bold transition-colors ${
                                                Number(nextVisitDuration) === dur
                                                    ? 'bg-blue-600 text-white shadow-sm'
                                                    : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
                                            }`}
                                        >
                                            {dur} {t('common.minutes_short', 'min')}
                                        </button>
                                    ))}
                                    <select
                                        value={nextVisitDuration}
                                        onChange={(e) => handleNextVisitDurationChange(Number(e.target.value))}
                                        data-testid="next-visit-duration-select"
                                        className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                    >
                                        <option value={15}>15 min</option>
                                        <option value={30}>30 min</option>
                                        <option value={45}>45 min</option>
                                        <option value={60}>60 min</option>
                                        <option value={90}>90 min</option>
                                    </select>
                                </div>
                            </div>

                            {/* Instructions for Reception */}
                            <div className="space-y-1">
                                <label
                                    htmlFor="next-visit-notes"
                                    className="block font-semibold text-slate-700 dark:text-slate-300"
                                >
                                    {t('care_session.reception_instructions', 'Reception Instructions (optional)')}
                                </label>
                                <input
                                    type="text"
                                    id="next-visit-notes"
                                    value={nextVisitNotes}
                                    onChange={handleNextVisitNotesChange}
                                    placeholder={t(
                                        'care_session.reception_instructions_placeholder',
                                        'e.g. Schedule after 7 days, check symptoms'
                                    )}
                                    data-testid="next-visit-notes-input"
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                        </div>
                    )}
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isFinishing}
                        className="min-h-10 rounded-xl border border-slate-300 px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        data-testid="cancel-finish-session-button"
                    >
                        {t('common.cancel', 'Cancel')}
                    </button>
                    <button
                        type="submit"
                        disabled={isFinishing}
                        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-emerald-600 bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:opacity-50"
                        data-testid="confirm-finish-session-button"
                    >
                        {isFinishing ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                <span>{t('care_session.finishing', 'Finishing...')}</span>
                            </>
                        ) : (
                            <>
                                <CheckCircle className="h-4 w-4" aria-hidden="true" />
                                <span>{t('care_session.confirm_finish', 'Complete Session')}</span>
                            </>
                        )}
                    </button>
                </div>
            </form>

            {isLabHandoffOpen && (
                <LabHandoffSheet
                    isOpen={isLabHandoffOpen}
                    onClose={() => setIsLabHandoffOpen(false)}
                    patientId={session.patient_id}
                    toothKey={extractedTooth}
                    workItem={steps.find((s) => s.work_item)?.work_item || null}
                    t={t}
                />
            )}
        </Modal>
    );
}

FinishCareSessionSheet.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    session: PropTypes.object,
    onFinishSession: PropTypes.func.isRequired,
    isFinishing: PropTypes.bool,
    draftData: PropTypes.object,
    onDraftChange: PropTypes.func,
    t: PropTypes.func,
};
