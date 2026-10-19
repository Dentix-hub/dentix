import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
    Activity,
    CheckCircle2,
    Clock,
    SkipForward,
    Play,
    AlertTriangle,
    Flag,
    ChevronDown,
    ChevronUp,
} from 'lucide-react';
import CanalTargetSelector from './CanalTargetSelector';
import WorkingLengthEntryTable from './WorkingLengthEntryTable';
import FinishCareSessionSheet from './FinishCareSessionSheet';

/**
 * Minimal RCT Structured UI (Slice S20 / G10-M08).
 * Chairside interface for Root Canal Treatment workflow steps,
 * canal target selection (G10-M09), working length entry (G10-M10),
 * and finish session sheet (G10-M11).
 */
export default function RctStructuredCard({
    session,
    toothKey,
    onUpdateStepStatus,
    onSaveObservation,
    onFinishSession,
    isUpdatingStep = false,
    isSavingObservation = false,
    isFinishingSession = false,
    t = (k, f) => f || k,
}) {
    const [selectedCanals, setSelectedCanals] = useState([
        { canalId: 'MB', rootId: 'mesial' },
        { canalId: 'ML', rootId: 'mesial' },
        { canalId: 'D', rootId: 'distal' },
    ]);
    const [activeTab, setActiveTab] = useState('steps'); // 'steps' | 'canals'
    const [isFinishSheetOpen, setIsFinishSheetOpen] = useState(false);
    const [partialPromptStepId, setPartialPromptStepId] = useState(null);
    const [partialNote, setPartialNote] = useState('');

    const steps = useMemo(() => {
        return session?.steps || [];
    }, [session]);

    const observations = useMemo(() => {
        return session?.observations || [];
    }, [session]);

    const handleToggleCanal = (canalInfo) => {
        setSelectedCanals((prev) => {
            const exists = prev.some(
                (c) =>
                    c.canalId.toLowerCase() === canalInfo.canalId.toLowerCase() &&
                    c.rootId === canalInfo.rootId
            );
            if (exists) {
                return prev.filter(
                    (c) =>
                        !(
                            c.canalId.toLowerCase() === canalInfo.canalId.toLowerCase() &&
                            c.rootId === canalInfo.rootId
                        )
                );
            }
            return [...prev, canalInfo];
        });
    };

    const handleStepAction = (stepId, status) => {
        if (status === 'partial') {
            setPartialPromptStepId(stepId);
            setPartialNote('');
            return;
        }
        onUpdateStepStatus(stepId, { status });
    };

    const handleConfirmPartial = (stepId) => {
        onUpdateStepStatus(stepId, {
            status: 'partial',
            notes: partialNote.trim() || undefined,
        });
        setPartialPromptStepId(null);
        setPartialNote('');
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case 'completed':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
                        <CheckCircle2 className="h-3 w-3" />
                        Completed
                    </span>
                );
            case 'partial':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
                        <AlertTriangle className="h-3 w-3" />
                        Partial
                    </span>
                );
            case 'in_progress':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-bold text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                        <Play className="h-3 w-3" />
                        In Progress
                    </span>
                );
            case 'skipped':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                        <SkipForward className="h-3 w-3" />
                        Skipped
                    </span>
                );
            default:
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        <Clock className="h-3 w-3" />
                        Pending
                    </span>
                );
        }
    };

    return (
        <div
            data-testid="rct-structured-card"
            className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                        <Activity className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                                {t('care_session.rct_title', 'Root Canal Treatment (RCT) Workflow')}
                            </h3>
                            <span className="rounded-md bg-purple-100 px-2 py-0.5 text-xs font-bold text-purple-800 dark:bg-purple-950/40 dark:text-purple-300">
                                Tooth {toothKey || '46'}
                            </span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                            {t('care_session.rct_subtitle', 'Chairside step execution, canal targeting, and length measurements')}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={() => setIsFinishSheetOpen(true)}
                        data-testid="btn-open-finish-sheet"
                        className="inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-emerald-600 bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm transition-colors hover:bg-emerald-700"
                    >
                        <Flag className="h-4 w-4" aria-hidden="true" />
                        <span>{t('care_session.finish_session_btn', 'Finish Session')}</span>
                    </button>
                </div>
            </div>

            {/* Navigation tabs between Steps and Canal Measurements */}
            <div className="flex border-b border-slate-200 dark:border-slate-800" role="tablist">
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'steps'}
                    onClick={() => setActiveTab('steps')}
                    data-testid="tab-rct-steps"
                    className={`min-h-11 border-b-2 px-4 py-2 text-xs font-bold transition-all ${
                        activeTab === 'steps'
                            ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                            : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                    }`}
                >
                    {t('care_session.steps_tab', 'Workflow Steps')} ({steps.length})
                </button>
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'canals'}
                    onClick={() => setActiveTab('canals')}
                    data-testid="tab-rct-canals"
                    className={`min-h-11 border-b-2 px-4 py-2 text-xs font-bold transition-all ${
                        activeTab === 'canals'
                            ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                            : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                    }`}
                >
                    {t('care_session.canals_tab', 'Canals & Working Lengths')} ({selectedCanals.length})
                </button>
            </div>

            {/* Tab 1: Workflow Steps */}
            {activeTab === 'steps' && (
                <div className="space-y-3" data-testid="rct-steps-container">
                    {steps.map((step, idx) => (
                        <div
                            key={step.id || step.step_code || idx}
                            data-testid={`rct-step-row-${step.step_code}`}
                            className="rounded-xl border border-slate-200 bg-slate-50/50 p-3.5 transition-colors dark:border-slate-800 dark:bg-slate-900/40"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2.5">
                                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-xs font-extrabold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                                        {step.step_order || idx + 1}
                                    </span>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                                                {step.title}
                                            </span>
                                            {getStatusBadge(step.status)}
                                        </div>
                                        {step.notes && (
                                            <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                                                {step.notes}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                <div className="flex flex-wrap items-center gap-1.5" data-testid={`step-actions-${step.step_code}`}>
                                    {step.status !== 'in_progress' && (
                                        <button
                                            type="button"
                                            disabled={isUpdatingStep}
                                            onClick={() => handleStepAction(step.id, 'in_progress')}
                                            data-testid={`btn-in-progress-${step.step_code}`}
                                            className="min-h-9 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                        >
                                            Start
                                        </button>
                                    )}
                                    {step.status !== 'completed' && (
                                        <button
                                            type="button"
                                            disabled={isUpdatingStep}
                                            onClick={() => handleStepAction(step.id, 'completed')}
                                            data-testid={`btn-complete-${step.step_code}`}
                                            className="min-h-9 rounded-lg border border-emerald-600 bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
                                        >
                                            Done
                                        </button>
                                    )}
                                    {step.status !== 'partial' && (
                                        <button
                                            type="button"
                                            disabled={isUpdatingStep}
                                            onClick={() => handleStepAction(step.id, 'partial')}
                                            data-testid={`btn-partial-${step.step_code}`}
                                            className="min-h-9 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-1 text-[11px] font-bold text-amber-700 hover:bg-amber-100 disabled:opacity-50 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300"
                                        >
                                            Partial
                                        </button>
                                    )}
                                    {step.status !== 'skipped' && step.status !== 'completed' && (
                                        <button
                                            type="button"
                                            disabled={isUpdatingStep}
                                            onClick={() => handleStepAction(step.id, 'skipped')}
                                            data-testid={`btn-skip-${step.step_code}`}
                                            className="min-h-9 rounded-lg border border-slate-200 bg-transparent px-2 py-1 text-[11px] font-medium text-slate-500 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:text-slate-400"
                                        >
                                            Skip
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Inline Partial Note Prompt */}
                            {partialPromptStepId === step.id && (
                                <div
                                    data-testid={`partial-prompt-${step.step_code}`}
                                    className="mt-3 rounded-lg border border-amber-200 bg-amber-50/60 p-3 dark:border-amber-900/50 dark:bg-amber-950/30"
                                >
                                    <label
                                        htmlFor={`partial-note-${step.id}`}
                                        className="block text-[11px] font-bold text-amber-900 dark:text-amber-300"
                                    >
                                        Partial Progress Reason / Remarks:
                                    </label>
                                    <input
                                        id={`partial-note-${step.id}`}
                                        type="text"
                                        value={partialNote}
                                        onChange={(e) => setPartialNote(e.target.value)}
                                        placeholder="e.g. MB/ML shaped, distal calcified - deferred to next visit..."
                                        data-testid={`input-partial-note-${step.step_code}`}
                                        className="mt-1 min-h-9 w-full rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs text-slate-800 focus:outline-none dark:border-amber-700 dark:bg-slate-900 dark:text-slate-200"
                                    />
                                    <div className="mt-2 flex items-center justify-end gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setPartialPromptStepId(null)}
                                            className="min-h-8 rounded px-2.5 py-1 text-xs text-slate-600 hover:bg-black/5 dark:text-slate-400"
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => handleConfirmPartial(step.id)}
                                            data-testid={`btn-confirm-partial-${step.step_code}`}
                                            className="min-h-8 rounded bg-amber-600 px-3 py-1 text-xs font-bold text-white hover:bg-amber-700"
                                        >
                                            Confirm Partial
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Tab 2: Canals & Measurements */}
            {activeTab === 'canals' && (
                <div className="space-y-4">
                    <CanalTargetSelector
                        toothKey={toothKey || '46'}
                        selectedCanals={selectedCanals}
                        onToggleCanal={handleToggleCanal}
                        t={t}
                    />

                    <WorkingLengthEntryTable
                        toothKey={toothKey || '46'}
                        selectedCanals={selectedCanals}
                        recordedObservations={observations}
                        onSaveMeasurement={onSaveObservation}
                        isLoading={isSavingObservation}
                        t={t}
                    />
                </div>
            )}

            {/* Finish Session Sheet Drawer */}
            <FinishCareSessionSheet
                isOpen={isFinishSheetOpen}
                onClose={() => setIsFinishSheetOpen(false)}
                session={session}
                onFinishSession={onFinishSession}
                isFinishing={isFinishingSession}
                t={t}
            />
        </div>
    );
}

RctStructuredCard.propTypes = {
    session: PropTypes.object,
    toothKey: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    onUpdateStepStatus: PropTypes.func.isRequired,
    onSaveObservation: PropTypes.func.isRequired,
    onFinishSession: PropTypes.func.isRequired,
    isUpdatingStep: PropTypes.bool,
    isSavingObservation: PropTypes.bool,
    isFinishingSession: PropTypes.bool,
    t: PropTypes.func,
};
