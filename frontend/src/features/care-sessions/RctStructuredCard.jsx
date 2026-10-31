import ProtectedImage from '@/features/clinical-attachments/components/ProtectedImage';
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
    Camera,
    Plus,
    Eye,
} from 'lucide-react';
import CanalTargetSelector from './CanalTargetSelector';
import WorkingLengthEntryTable from './WorkingLengthEntryTable';
import FinishCareSessionSheet from './FinishCareSessionSheet';
import {
    getPurposeLabel,
    DiagnosticImageLightbox,
    LinkClinicalAttachmentModal,
} from '@/features/clinical-attachments';

/**
 * Minimal RCT Structured UI (Slice S20 & S24 / G10-M08, G15-M08).
 * Chairside interface for Root Canal Treatment workflow steps,
 * canal target selection (G10-M09), working length entry (G10-M10),
 * finish session sheet (G10-M11), and diagnostic image viewer (G15-M08).
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
    patientId = null,
    attachments = [],
    attachmentLinks = [],
    onCreateAttachmentLink = null,
    onDeleteAttachmentLink = null,
    draftData = null,
    onDraftChange = null,
    t = (k, f) => f || k,
}) {
    const [selectedCanals, setSelectedCanals] = useState([
        { canalId: 'MB', rootId: 'mesial' },
        { canalId: 'ML', rootId: 'mesial' },
        { canalId: 'D', rootId: 'distal' },
    ]);
    const [activeTab, setActiveTab] = useState('steps'); // 'steps' | 'canals' | 'images'
    const [isFinishSheetOpen, setIsFinishSheetOpen] = useState(false);
    const [partialPromptStepId, setPartialPromptStepId] = useState(null);
    const [partialNote, setPartialNote] = useState('');
    const [selectedImageForLightbox, setSelectedImageForLightbox] = useState(null);
    const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);

    const sessionImages = useMemo(() => {
        return (attachmentLinks || []).filter(
            (lnk) =>
                lnk.care_session_id != null &&
                (String(lnk.care_session_id) === String(session?.id) ||
                    Number(lnk.care_session_id) === Number(session?.id)) &&
                (lnk.file_type?.includes('image') ||
                    lnk.content_type?.includes('image') ||
                    lnk.filename?.match(/\.(png|jpg|jpeg|webp|gif|svg)$/i) ||
                    lnk.file_name?.match(/\.(png|jpg|jpeg|webp|gif|svg)$/i) ||
                    (!lnk.file_type && !lnk.content_type))
        );
    }, [session?.id, attachmentLinks]);

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
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-bold text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                        <CheckCircle2 className="h-3 w-3" />
                        Completed
                    </span>
                );
            case 'partial':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                        <AlertTriangle className="h-3 w-3" />
                        Partial
                    </span>
                );
            case 'in_progress':
                return (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-bold text-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
                        <Clock className="h-3 w-3 animate-pulse" />
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

            {/* Navigation tabs between Steps, Canals, and Images (G15-M08) */}
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
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'images'}
                    onClick={() => setActiveTab('images')}
                    data-testid="tab-rct-images"
                    className={`min-h-11 border-b-2 px-4 py-2 text-xs font-bold transition-all ${
                        activeTab === 'images'
                            ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                            : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                    }`}
                >
                    <span className="flex items-center gap-1.5">
                        <Camera className="h-3.5 w-3.5" />
                        <span>{t('care_session.images_tab', 'Images & X-Rays')}</span>
                        <span>({sessionImages.length})</span>
                    </span>
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
                                            data-testid={`btn-progress-${step.step_code}`}
                                            className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700 transition-colors hover:bg-blue-100 disabled:opacity-50 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-300"
                                        >
                                            <Play className="h-3 w-3" />
                                            <span>Start</span>
                                        </button>
                                    )}

                                    {step.status !== 'completed' && (
                                        <button
                                            type="button"
                                            disabled={isUpdatingStep}
                                            onClick={() => handleStepAction(step.id, 'completed')}
                                            data-testid={`btn-complete-${step.step_code}`}
                                            className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 transition-colors hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
                                        >
                                            <CheckCircle2 className="h-3 w-3" />
                                            <span>Complete</span>
                                        </button>
                                    )}

                                    {step.status !== 'partial' && (
                                        <button
                                            type="button"
                                            disabled={isUpdatingStep}
                                            onClick={() => handleStepAction(step.id, 'partial')}
                                            data-testid={`btn-partial-${step.step_code}`}
                                            className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700 transition-colors hover:bg-amber-100 disabled:opacity-50 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300"
                                        >
                                            <AlertTriangle className="h-3 w-3" />
                                            <span>Partial</span>
                                        </button>
                                    )}

                                    {step.status !== 'skipped' && step.status !== 'completed' && (
                                        <button
                                            type="button"
                                            disabled={isUpdatingStep}
                                            onClick={() => handleStepAction(step.id, 'skipped')}
                                            data-testid={`btn-skip-${step.step_code}`}
                                            className="inline-flex min-h-8 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                        >
                                            <SkipForward className="h-3 w-3" />
                                            <span>Skip</span>
                                        </button>
                                    )}
                                </div>
                            </div>

                            {partialPromptStepId === step.id && (
                                <div
                                    data-testid={`partial-prompt-${step.step_code}`}
                                    className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-2.5 dark:border-amber-900/40 dark:bg-amber-950/30"
                                >
                                    <label className="block text-xs font-bold text-amber-900 dark:text-amber-200">
                                        Note for partial completion:
                                    </label>
                                    <input
                                        type="text"
                                        value={partialNote}
                                        onChange={(e) => setPartialNote(e.target.value)}
                                        placeholder="e.g., Canal scouted, negotiation pending next visit"
                                        data-testid={`input-partial-note-${step.step_code}`}
                                        className="mt-1 block min-h-9 w-full rounded border border-amber-300 bg-white px-2 py-1 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500 dark:border-amber-700 dark:bg-slate-800 dark:text-slate-200"
                                    />
                                    <div className="mt-2 flex justify-end gap-2">
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

            {/* Tab 3: Diagnostic Images & Radiographs (G15-M08) */}
            {activeTab === 'images' && (
                <div className="space-y-4" data-testid="session-images-tab-content">
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                            {t('care_session.session_images_desc', 'Diagnostic radiographs and photos captured during this session')}
                        </p>
                        {attachments.length > 0 && (
                            <button
                                type="button"
                                onClick={() => setIsLinkModalOpen(true)}
                                data-testid="btn-link-session-image"
                                className="inline-flex min-h-9 items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700"
                            >
                                <Plus className="h-3.5 w-3.5" />
                                <span>{t('care_session.link_image', 'Link Image to Session')}</span>
                            </button>
                        )}
                    </div>

                    {sessionImages.length === 0 ? (
                        <div
                            data-testid="session-empty-images"
                            className="rounded-2xl border border-dashed border-slate-200 p-8 text-center text-slate-500 dark:border-slate-800 dark:text-slate-400"
                        >
                            <Camera className="mx-auto mb-2 h-8 w-8 opacity-30" />
                            <p className="text-xs">
                                {t('care_session.no_images', 'No diagnostic images linked to this care session yet.')}
                            </p>
                        </div>
                    ) : (
                        <div
                            data-testid="session-images-grid"
                            className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4"
                        >
                            {sessionImages.map((img) => (
                                <div
                                    key={img.id}
                                    data-testid={`session-image-thumbnail-${img.id}`}
                                    onClick={() => setSelectedImageForLightbox(img)}
                                    className="group relative aspect-square cursor-pointer overflow-hidden rounded-xl border border-slate-200 bg-slate-100 shadow-sm transition-transform hover:scale-[1.02] dark:border-slate-800 dark:bg-slate-800"
                                >
                                    <ProtectedImage
                                        filePath={img.file_path}
                                thumbnail
                                        alt={img.filename || 'Session radiograph'}
                                        className="h-full w-full object-cover"
                                    />
                                    <div className="absolute top-1.5 start-1.5 flex flex-wrap gap-1">
                                        <span
                                            data-testid={`session-image-purpose-${img.id}`}
                                            className="rounded bg-black/75 px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-xs"
                                        >
                                            {getPurposeLabel(img.purpose_code)}
                                        </span>
                                        {img.tooth_key && (
                                            <span className="rounded bg-purple-700/80 px-1.5 py-0.5 text-[9px] font-bold text-white backdrop-blur-xs">
                                                T{img.tooth_key}
                                            </span>
                                        )}
                                    </div>
                                    <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                                        <Eye className="h-5 w-5 text-white" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Finish Session Sheet Drawer */}
            <FinishCareSessionSheet
                isOpen={isFinishSheetOpen}
                onClose={() => setIsFinishSheetOpen(false)}
                session={session}
                onFinishSession={onFinishSession}
                isFinishing={isFinishingSession}
                draftData={draftData}
                onDraftChange={onDraftChange}
                t={t}
            />

            {/* Lightbox Preview */}
            {selectedImageForLightbox && (
                <DiagnosticImageLightbox
                    isOpen={Boolean(selectedImageForLightbox)}
                    onClose={() => setSelectedImageForLightbox(null)}
                    image={selectedImageForLightbox}
                />
            )}

            {/* Link Existing Attachment Modal */}
            {isLinkModalOpen && (
                <LinkClinicalAttachmentModal
                    isOpen={isLinkModalOpen}
                    onClose={() => setIsLinkModalOpen(false)}
                    attachment={attachments[0] || null}
                    patientId={patientId || session?.patient_id}
                    activeCareSession={session}
                    initialSessionId={session?.id}
                    initialToothKey={toothKey ? String(toothKey) : null}
                    existingLinks={attachmentLinks}
                    onLinkCreated={onCreateAttachmentLink}
                    onLinkDeleted={onDeleteAttachmentLink}
                />
            )}
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
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    attachments: PropTypes.array,
    attachmentLinks: PropTypes.array,
    onCreateAttachmentLink: PropTypes.func,
    onDeleteAttachmentLink: PropTypes.func,
    draftData: PropTypes.object,
    onDraftChange: PropTypes.func,
    t: PropTypes.func,
};
