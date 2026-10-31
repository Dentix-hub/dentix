import { useState, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
    Activity,
    CheckCircle2,
    Clock,
    Plus,
    X,
    Calendar,
    AlertTriangle,
    Flag,
    RotateCcw,
    SkipForward,
    Play,
    Check,
    Sparkles,
    FileText,
    Layers,
    Sliders,
} from 'lucide-react';
import { Button, Badge, DentixDialog } from '@/shared/ui';
import ProcedureStatusControl from '@/features/clinical-chart/components/ProcedureStatusControl';
import WorkingLengthEntryTable from './WorkingLengthEntryTable';
import CanalTargetSelector from './CanalTargetSelector';
import {
    addCareSessionProcedure,
    removeCareSessionProcedure,
    addCareSessionStep,
} from '@/api/patients';

/**
 * Generic Visit Workspace (Requirement 1 & 3).
 * Multi-procedure chairside workspace supporting generic and specialty workflows,
 * template snapshot rendering, custom fields, procedure-scoped isolation,
 * intentional repeated steps, draft autosave, and conflict resolution.
 */
export default function GenericVisitWorkspace({
    session,
    patient,
    patientWorkItems = [],
    isOpen = false,
    onClose,
    onUpdateStepStatus,
    onSaveObservation,
    onOpenFinishSheet,
    onOpenMaterialsModal,
    onOpenLabHandoff,
    draftData = null,
    onDraftChange = null,
    careSessionDraftStatus = 'idle',
    resolveConflict = null,
    refetchSession = null,
    t = (k, f) => f || k,
}) {
    // Procedures associated with this session
    const sessionProcedures = useMemo(() => {
        return session?.procedures || [];
    }, [session?.procedures]);

    // Available procedures for this patient that are not yet in this session
    const availableWorkItems = useMemo(() => {
        const associatedIds = new Set(sessionProcedures.map((p) => p.work_item_id));
        return (patientWorkItems || []).filter(
            (wi) => !associatedIds.has(wi.id) && wi.status !== 'cancelled'
        );
    }, [sessionProcedures, patientWorkItems]);

    // Active selected procedure ID in workspace
    const [selectedWorkItemId, setSelectedWorkItemId] = useState(() => {
        if (sessionProcedures.length > 0) {
            return sessionProcedures[0].work_item_id;
        }
        return null;
    });

    useEffect(() => {
        if (sessionProcedures.length > 0) {
            if (!selectedWorkItemId || !sessionProcedures.some((p) => p.work_item_id === selectedWorkItemId)) {
                setSelectedWorkItemId(sessionProcedures[0].work_item_id);
            }
        }
    }, [sessionProcedures, selectedWorkItemId]);

    // Selected CareSessionProcedure row
    const selectedSessionProc = useMemo(() => {
        return sessionProcedures.find((p) => p.work_item_id === selectedWorkItemId) || null;
    }, [sessionProcedures, selectedWorkItemId]);

    // Selected ClinicalWorkItem row
    const selectedWorkItem = useMemo(() => {
        if (selectedSessionProc?.work_item) return selectedSessionProc.work_item;
        return (patientWorkItems || []).find((wi) => wi.id === selectedWorkItemId) || null;
    }, [selectedSessionProc, patientWorkItems, selectedWorkItemId]);

    // Template snapshot for selected procedure
    const templateSnapshot = useMemo(() => {
        return selectedSessionProc?.template_snapshot || null;
    }, [selectedSessionProc]);

    // Steps belonging to the selected procedure in this visit
    const procedureSteps = useMemo(() => {
        const steps = session?.steps || [];
        if (!selectedWorkItemId) return steps;
        return steps.filter((s) => s.work_item_id === selectedWorkItemId);
    }, [session?.steps, selectedWorkItemId]);

    // Observations belonging to the selected procedure in this visit
    const procedureObservations = useMemo(() => {
        const obs = session?.observations || [];
        if (!selectedWorkItemId) return obs;
        return obs.filter((o) => o.work_item_id === selectedWorkItemId);
    }, [session?.observations, selectedWorkItemId]);

    // Carried forward / previous observations
    const carriedObservations = useMemo(() => {
        return procedureObservations.filter((o) => o.reference_source_session_id != null);
    }, [procedureObservations]);

    // Procedure notes and next action local draft state
    const [procedureNotes, setProcedureNotes] = useState(() => {
        return draftData?.[`proc_notes_${selectedWorkItemId}`] || selectedSessionProc?.procedure_notes || '';
    });
    const [nextAction, setNextAction] = useState(() => {
        return draftData?.[`proc_next_action_${selectedWorkItemId}`] || selectedSessionProc?.next_action || '';
    });

    // Custom field values stored in draftData
    const customFieldValues = useMemo(() => {
        const prefix = `proc_custom_${selectedWorkItemId}_`;
        const res = {};
        if (draftData) {
            Object.keys(draftData).forEach((k) => {
                if (k.startsWith(prefix)) {
                    res[k.replace(prefix, '')] = draftData[k];
                }
            });
        }
        return res;
    }, [draftData, selectedWorkItemId]);

    // Update notes when selected procedure changes
    useEffect(() => {
        if (selectedWorkItemId) {
            setProcedureNotes(
                draftData?.[`proc_notes_${selectedWorkItemId}`] ?? selectedSessionProc?.procedure_notes ?? ''
            );
            setNextAction(
                draftData?.[`proc_next_action_${selectedWorkItemId}`] ?? selectedSessionProc?.next_action ?? ''
            );
        }
    }, [selectedWorkItemId, selectedSessionProc, draftData]);

    const handleNotesChange = (val) => {
        setProcedureNotes(val);
        if (onDraftChange && selectedWorkItemId) {
            onDraftChange({
                ...draftData,
                [`proc_notes_${selectedWorkItemId}`]: val,
            });
        }
    };

    const handleNextActionChange = (val) => {
        setNextAction(val);
        if (onDraftChange && selectedWorkItemId) {
            onDraftChange({
                ...draftData,
                [`proc_next_action_${selectedWorkItemId}`]: val,
            });
        }
    };

    const handleCustomFieldChange = (fieldId, val) => {
        if (onDraftChange && selectedWorkItemId) {
            onDraftChange({
                ...draftData,
                [`proc_custom_${selectedWorkItemId}_${fieldId}`]: val,
            });
        }
    };

    // Tooth key for the selected procedure
    const procedureToothKey = useMemo(() => {
        const canalTarget = selectedWorkItem?.targets?.find((t) => t.target_kind === 'canal' || t.tooth_key);
        return String(canalTarget?.tooth_key || selectedWorkItem?.tooth_number || '46');
    }, [selectedWorkItem]);

    // Initial canal targets from selected procedure work item
    const initialCanals = useMemo(() => {
        const canalTargets = selectedWorkItem?.targets?.filter((t) => t.target_kind === 'canal') || [];
        if (canalTargets.length > 0) {
            return canalTargets.map((t) => ({
                canalId: t.canal_id || t.canalId || 'MB',
                rootId: t.root_id || t.rootId || 'mesial',
            }));
        }
        return [];
    }, [selectedWorkItem]);

    const [selectedCanals, setSelectedCanals] = useState(initialCanals);

    useEffect(() => {
        setSelectedCanals(initialCanals);
    }, [initialCanals]);

    const handleToggleCanal = (canal) => {
        setSelectedCanals((prev) => {
            const exists = prev.some(
                (c) => c.canalId?.toLowerCase() === canal.canalId?.toLowerCase() && c.rootId === canal.rootId
            );
            if (exists) {
                return prev.filter(
                    (c) => !(c.canalId?.toLowerCase() === canal.canalId?.toLowerCase() && c.rootId === canal.rootId)
                );
            }
            return [...prev, canal];
        });
    };

    const handleSaveMeasurement = (measurement) => {
        if (onSaveObservation) {
            const lengthVal = measurement.length_mm != null ? Number(measurement.length_mm) : undefined;
            onSaveObservation({
                observation_code: 'working_length',
                work_item_id: selectedWorkItemId,
                tooth_key: String(procedureToothKey || measurement.tooth_key),
                canal_id: measurement.canal_id,
                root_id: measurement.root_id,
                structured_value: {
                    length_mm: lengthVal,
                    reference_point: measurement.reference_point,
                    maf: measurement.maf,
                },
                length_mm: lengthVal,
                reference_point: measurement.reference_point,
                maf: measurement.maf,
                notes: measurement.notes,
            });
        }
    };

    const [validationError, setValidationError] = useState(null);

    const handleFinishVisit = (e) => {
        e?.preventDefault?.();
        // F10: Enforce required custom fields
        for (const proc of sessionProcedures) {
            const fields = proc.template_snapshot?.custom_fields || [];
            for (const f of fields) {
                if (f.is_required) {
                    const key = `proc_custom_${proc.work_item_id}_${f.field_id}`;
                    const val = draftData?.[key] ?? proc.template_snapshot?.custom_field_values?.[f.field_id];
                    if (val === undefined || val === null || String(val).trim() === '') {
                        setValidationError(t('care_session.missing_required_field', `Required field missing: ${f.label}`));
                        return;
                    }
                }
            }
        }
        setValidationError(null);
        onOpenFinishSheet?.();
    };

    // UI state for adding a procedure dropdown
    const [isAddProcOpen, setIsAddProcOpen] = useState(false);
    const [isAddingProc, setIsAddingProc] = useState(false);
    const [actionError, setActionError] = useState(null);

    // Skip step prompt state
    const [skippingStepId, setSkippingStepId] = useState(null);
    const [skipReason, setSkipReason] = useState('');

    // Repeat step prompt state
    const [repeatingStep, setRepeatingStep] = useState(null);
    const [repeatReason, setRepeatReason] = useState('');

    const handleAddProcedure = async (workItemId) => {
        setIsAddingProc(true);
        setActionError(null);
        try {
            await addCareSessionProcedure(session.patient_id, session.id, workItemId);
            setIsAddProcOpen(false);
            if (refetchSession) await refetchSession();
            setSelectedWorkItemId(workItemId);
        } catch (err) {
            setActionError(err?.response?.data?.detail || err.message || 'Failed to add procedure');
        } finally {
            setIsAddingProc(false);
        }
    };

    const handleRemoveProcedure = async (workItemId) => {
        if (!window.confirm(t('care_session.confirm_remove_proc', 'Remove this procedure from the visit?'))) {
            return;
        }
        setActionError(null);
        try {
            await removeCareSessionProcedure(session.patient_id, session.id, workItemId);
            if (refetchSession) await refetchSession();
        } catch (err) {
            setActionError(err?.response?.data?.detail || err.message || 'Failed to remove procedure');
        }
    };

    const handleRepeatStepSubmit = async () => {
        if (!repeatingStep) return;
        try {
            await addCareSessionStep(session.patient_id, session.id, {
                step_code: repeatingStep.step_code,
                title: repeatingStep.title,
                work_item_id: selectedWorkItemId,
                is_repeat: true,
                repeat_reason: repeatReason || 'Repeated clinical step',
            });
            setRepeatingStep(null);
            setRepeatReason('');
            if (refetchSession) await refetchSession();
        } catch (err) {
            setActionError(err?.response?.data?.detail || err.message || 'Failed to repeat step');
        }
    };

    const handleSkipStepSubmit = async () => {
        if (!skippingStepId) return;
        if (onUpdateStepStatus) {
            await onUpdateStepStatus(skippingStepId, 'skipped', skipReason || 'Skipped by clinician');
        }
        setSkippingStepId(null);
        setSkipReason('');
        if (refetchSession) await refetchSession();
    };

    // Check if RCT procedure
    const isRctProcedure = useMemo(() => {
        const code = selectedWorkItem?.code || selectedWorkItem?.procedure_code || '';
        return code.toUpperCase() === 'ENDO_RCT';
    }, [selectedWorkItem]);

    const formatStartTime = (iso) => {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return '';
        }
    };

    if (!isOpen || !session) return null;

    return (
        <DentixDialog
            open={isOpen}
            onOpenChange={(nextOpen) => {
                if (!nextOpen) onClose?.();
            }}
            title={t('care_session.workspace_title', 'Chairside Visit Workspace')}
            size="5xl"
            maxWidth="w-[calc(100%-1rem)] max-w-7xl h-[calc(100dvh-1rem)]"
            scrollable={false}
            className="p-0 overflow-hidden"
        >
            <div
                role="region"
                aria-label={t('care_session.workspace_title', 'Chairside Visit Workspace')}
                data-testid="generic-visit-workspace"
                className="flex h-full w-full flex-col bg-surface overflow-hidden"
            >
                {/* ---------------- Top Header Bar ---------------- */}
                <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-surface-elevated px-4 py-3 sm:px-6">
                    <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-white shadow-xs">
                            <Activity className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h2 className="text-base font-bold text-text-primary">
                                    {t('care_session.visit_workspace', 'Visit Workspace')} #{session.id}
                                </h2>
                                <Badge variant="success" size="xs" className="font-bold gap-1">
                                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                    <span>{t('care_session.status_in_progress', 'Active Visit')}</span>
                                </Badge>
                                {session.appointment_id && (
                                    <Badge variant="neutral" size="xs" className="gap-1 font-semibold">
                                        <Calendar className="h-3 w-3" />
                                        <span>Appt #{session.appointment_id}</span>
                                    </Badge>
                                )}
                                {session.started_at && (
                                    <span className="flex items-center gap-1 text-xs text-text-secondary">
                                        <Clock className="h-3 w-3" />
                                        {formatStartTime(session.started_at)}
                                    </span>
                                )}
                            </div>
                            <p className="text-xs text-text-secondary">
                                {patient?.name || `Patient #${session.patient_id}`}
                            </p>
                        </div>
                    </div>

                    {/* Autosave & Conflict Indicators */}
                    <div className="flex items-center gap-3">
                        {careSessionDraftStatus === 'saving' && (
                            <span
                                data-testid="workspace-draft-saving"
                                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"
                            >
                                <span className="h-2 w-2 rounded-full bg-blue-600 animate-ping" />
                                {t('care_session.autosave_saving', 'Saving draft...')}
                            </span>
                        )}
                        {careSessionDraftStatus === 'saved' && (
                            <span
                                data-testid="workspace-draft-saved"
                                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                            >
                                <Check className="h-3.5 w-3.5 text-emerald-600" />
                                {t('care_session.autosave_saved', 'Draft saved')}
                            </span>
                        )}
                        {careSessionDraftStatus === 'error' && (
                            <span
                                data-testid="workspace-draft-error"
                                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                            >
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                                {t('care_session.autosave_offline', 'Offline (changes kept in page)')}
                            </span>
                        )}
                        {careSessionDraftStatus === 'conflict' && (
                            <div
                                data-testid="workspace-draft-conflict-bar"
                                className="inline-flex items-center gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-900 dark:border-amber-700 dark:bg-amber-950/50 dark:text-amber-200"
                            >
                                <span>{t('care_session.conflict_warning', 'Server modified elsewhere')}</span>
                                {resolveConflict && (
                                    <button
                                        type="button"
                                        onClick={() => resolveConflict({ overwrite: true })}
                                        className="rounded-md bg-amber-600 px-2 py-0.5 text-xs text-white hover:bg-amber-700"
                                    >
                                        {t('care_session.overwrite_btn', 'Overwrite')}
                                    </button>
                                )}
                            </div>
                        )}

                        {/* Finish Visit Button */}
                        <Button
                            variant="success"
                            size="sm"
                            onClick={handleFinishVisit}
                            data-testid="workspace-finish-visit-btn"
                            className="gap-1.5 font-bold shadow-xs"
                        >
                            <Flag className="h-4 w-4" />
                            <span>{t('care_session.finish_visit_btn', 'Finish Visit')}</span>
                        </Button>

                        {/* Close Workspace */}
                        <button
                            type="button"
                            onClick={onClose}
                            data-testid="workspace-close-btn"
                            aria-label="Close Workspace"
                            className="rounded-xl p-2 text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>
                </header>

                {validationError && (
                    <div
                        data-testid="workspace-validation-error"
                        className="mx-4 mt-2 rounded-lg bg-red-50 p-2.5 text-xs font-semibold text-red-700 dark:bg-red-950/40 dark:text-red-300 border border-red-200 dark:border-red-800"
                    >
                        {validationError}
                    </div>
                )}

                {actionError && (
                    <div
                        data-testid="workspace-error-banner"
                        className="flex items-center justify-between bg-danger/10 px-6 py-2 text-xs font-bold text-danger border-b border-danger/20"
                    >
                        <span>{actionError}</span>
                        <button type="button" onClick={() => setActionError(null)}>
                            <X className="h-4 w-4" />
                        </button>
                    </div>
                )}

                {/* ---------------- Procedures Navigation Strip ---------------- */}
                <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-2 sm:px-6">
                    <div className="flex items-center gap-2 overflow-x-auto py-1">
                        <span className="text-xs font-bold text-text-secondary uppercase tracking-wider me-1">
                            {t('care_session.procedures_label', 'Procedures in Visit')}:
                        </span>

                        {sessionProcedures.map((sp) => {
                            const isSelected = sp.work_item_id === selectedWorkItemId;
                            const wi = sp.work_item || (patientWorkItems || []).find((w) => w.id === sp.work_item_id);
                            const toothKey = wi?.targets?.[0]?.tooth_key || wi?.tooth_key;

                            return (
                                <div
                                    key={sp.work_item_id}
                                    className={`group flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-bold transition-all ${
                                        isSelected
                                            ? 'border-primary bg-primary/10 text-primary shadow-xs'
                                            : 'border-border bg-surface-elevated text-text-secondary hover:border-border-focus hover:text-text-primary'
                                    }`}
                                >
                                    <button
                                        type="button"
                                        onClick={() => setSelectedWorkItemId(sp.work_item_id)}
                                        data-testid={`tab-proc-${sp.work_item_id}`}
                                        className="flex items-center gap-1.5"
                                    >
                                        {toothKey && (
                                            <span className="rounded-md bg-surface px-1.5 py-0.5 text-xs font-black border border-border">
                                                #{toothKey}
                                            </span>
                                        )}
                                        <span>{wi?.title || wi?.code || `Proc #${sp.work_item_id}`}</span>
                                    </button>

                                    {/* Inline Procedure Status Control */}
                                    <ProcedureStatusControl
                                        patientId={session.patient_id}
                                        workItemId={sp.work_item_id}
                                        currentStatus={sp.work_item_status || wi?.status || 'active'}
                                        versionId={sp.work_item_version_id || wi?.version_id || 1}
                                        procedureCode={wi?.code || ''}
                                        procedureTitle={wi?.title || wi?.code || ''}
                                        onSuccess={() => refetchSession && refetchSession()}
                                        t={t}
                                    />

                                    {/* Remove procedure button (if 0 steps completed in this visit) */}
                                    {sessionProcedures.length > 1 && (
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveProcedure(sp.work_item_id)}
                                            data-testid={`btn-remove-proc-${sp.work_item_id}`}
                                            title={t('care_session.remove_proc_title', 'Remove procedure from visit')}
                                            className="opacity-0 group-hover:opacity-100 p-0.5 text-text-secondary hover:text-danger transition-opacity"
                                        >
                                            <X className="h-3.5 w-3.5" />
                                        </button>
                                    )}
                                </div>
                            );
                        })}

                        {/* Add Procedure Button */}
                        <div className="relative">
                            <button
                                type="button"
                                onClick={() => setIsAddProcOpen(!isAddProcOpen)}
                                data-testid="btn-add-proc-to-visit"
                                disabled={availableWorkItems.length === 0 || isAddingProc}
                                className="inline-flex items-center gap-1.5 rounded-xl border border-dashed border-border px-3 py-1.5 text-xs font-bold text-text-secondary hover:border-primary hover:text-primary transition-colors disabled:opacity-50"
                            >
                                <Plus className="h-3.5 w-3.5" />
                                <span>{t('care_session.add_procedure_btn', 'Add Procedure')}</span>
                            </button>

                            {isAddProcOpen && availableWorkItems.length > 0 && (
                                <div
                                    data-testid="dropdown-available-procedures"
                                    className="absolute left-0 mt-2 z-50 w-64 rounded-2xl border border-border bg-surface-elevated p-2 shadow-xl animate-in fade-in"
                                >
                                    <div className="text-xs font-bold text-text-secondary px-2 py-1 mb-1">
                                        {t('care_session.select_proc_to_add', 'Select Procedure')}:
                                    </div>
                                    <div className="max-h-48 overflow-y-auto space-y-1">
                                        {availableWorkItems.map((wi) => (
                                            <button
                                                key={wi.id}
                                                type="button"
                                                onClick={() => handleAddProcedure(wi.id)}
                                                className="w-full flex items-center justify-between gap-2 rounded-xl px-2.5 py-1.5 text-xs text-text-primary hover:bg-surface text-left"
                                            >
                                                <span className="font-bold truncate">
                                                    {wi.title || wi.code || `Procedure #${wi.id}`}
                                                </span>
                                                {wi.tooth_key && (
                                                    <span className="rounded bg-surface px-1 py-0.5 text-xs text-text-secondary">
                                                        #{wi.tooth_key}
                                                    </span>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Context actions */}
                    <div className="flex items-center gap-2">
                        {onOpenMaterialsModal && (
                            <Button
                                variant="outline"
                                size="xs"
                                onClick={onOpenMaterialsModal}
                                data-testid="workspace-materials-btn"
                                className="gap-1 text-xs"
                            >
                                <Layers className="h-3.5 w-3.5" />
                                <span>{t('care_session.materials_btn', 'Materials')}</span>
                            </Button>
                        )}
                        {onOpenLabHandoff && (
                            <Button
                                variant="outline"
                                size="xs"
                                onClick={onOpenLabHandoff}
                                data-testid="workspace-lab-btn"
                                className="gap-1 text-xs"
                            >
                                <Sliders className="h-3.5 w-3.5" />
                                <span>{t('care_session.lab_handoff_btn', 'Lab Work')}</span>
                            </Button>
                        )}
                    </div>
                </div>

                {/* ---------------- Main Content Body ---------------- */}
                <main className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
                    {/* Procedure Headline Card */}
                    <div className="rounded-2xl border border-border bg-surface-elevated p-4 shadow-xs">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <div className="flex items-center gap-2">
                                    <h3 className="text-lg font-bold text-text-primary">
                                        {selectedWorkItem?.title || selectedWorkItem?.code || 'Selected Procedure'}
                                    </h3>
                                    {selectedWorkItem?.targets?.[0]?.tooth_key && (
                                        <Badge variant="primary" size="sm" className="font-bold">
                                            Tooth #{selectedWorkItem.targets[0].tooth_key}
                                        </Badge>
                                    )}
                                </div>
                                <p className="text-xs text-text-secondary mt-0.5">
                                    {templateSnapshot?.title || t('care_session.standard_procedure_workflow', 'Standard Clinical Workflow')}
                                    {templateSnapshot?.version && ` (v${templateSnapshot.version})`}
                                </p>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="text-xs font-semibold text-text-secondary">
                                    {procedureSteps.filter((s) => s.status === 'completed').length} / {procedureSteps.length}{' '}
                                    {t('care_session.steps_done_label', 'steps completed')}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* 1. Previous Visit Context Card (Requirement 1 & 4) */}
                    {carriedObservations.length > 0 && (
                        <section
                            data-testid="workspace-previous-context"
                            aria-label="Previous Visit Context"
                            className="rounded-2xl border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-900/40 dark:bg-indigo-950/20"
                        >
                            <div className="flex items-center gap-2 text-xs font-bold text-indigo-900 dark:text-indigo-200 mb-2">
                                <RotateCcw className="h-4 w-4" />
                                <span>{t('care_session.previous_visit_context', 'Previous Visit Context & Carried Measurements')}</span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                                {carriedObservations.map((obs) => (
                                    <div
                                        key={obs.id}
                                        className="rounded-xl border border-indigo-200/80 bg-surface p-2.5 text-xs shadow-xs"
                                    >
                                        <div className="flex items-center justify-between text-text-secondary font-semibold">
                                            <span>{obs.observation_code}</span>
                                            {obs.reference_source_date && (
                                                <span className="text-xs">
                                                    {new Date(obs.reference_source_date).toLocaleDateString()}
                                                </span>
                                            )}
                                        </div>
                                        <div className="font-bold text-text-primary mt-1">
                                            {obs.structured_value ? JSON.stringify(obs.structured_value) : obs.notes}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* 2. Current Workflow Steps (Requirement 1) */}
                    <section
                        data-testid="workspace-workflow-steps"
                        aria-label="Workflow Steps"
                        className="rounded-2xl border border-border bg-surface-elevated p-4 shadow-xs"
                    >
                        <div className="flex items-center justify-between border-b border-border pb-3 mb-3">
                            <div className="flex items-center gap-2">
                                <CheckCircle2 className="h-4 w-4 text-primary" />
                                <h4 className="text-sm font-bold text-text-primary">
                                    {t('care_session.workflow_steps_title', 'Clinical Workflow Steps')}
                                </h4>
                            </div>
                            <span className="text-xs text-text-secondary">
                                {t('care_session.steps_guidance', 'Mark performed stages chairside')}
                            </span>
                        </div>

                        {procedureSteps.length === 0 ? (
                            <div className="py-6 text-center text-xs text-text-secondary">
                                {t('care_session.no_steps_for_proc', 'No steps defined for this procedure yet.')}
                            </div>
                        ) : (
                            <div className="space-y-2.5">
                                {procedureSteps.map((step) => {
                                    const isDone = step.status === 'completed';
                                    const isInProgress = step.status === 'in_progress';
                                    const isSkipped = step.status === 'skipped';

                                    return (
                                        <div
                                            key={step.id}
                                            data-testid={`step-row-${step.id}`}
                                            className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3 transition-colors ${
                                                isDone
                                                    ? 'border-emerald-200 bg-emerald-50/40 dark:border-emerald-900/40 dark:bg-emerald-950/20'
                                                    : isInProgress
                                                    ? 'border-blue-300 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20'
                                                    : isSkipped
                                                    ? 'border-slate-200 bg-slate-50 opacity-60 dark:border-slate-800 dark:bg-slate-900'
                                                    : 'border-border bg-surface'
                                            }`}
                                        >
                                            <div className="flex items-center gap-3">
                                                <button
                                                    type="button"
                                                    onClick={() =>
                                                        onUpdateStepStatus &&
                                                        onUpdateStepStatus(step.id, isDone ? 'pending' : 'completed')
                                                    }
                                                    data-testid={`btn-toggle-step-${step.id}`}
                                                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border transition-colors ${
                                                        isDone
                                                            ? 'border-emerald-600 bg-emerald-600 text-white'
                                                            : isInProgress
                                                            ? 'border-blue-600 bg-blue-600 text-white'
                                                            : 'border-border bg-surface text-transparent hover:border-primary'
                                                    }`}
                                                >
                                                    <Check className="h-4 w-4" />
                                                </button>

                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span
                                                            className={`text-xs font-bold ${
                                                                isDone
                                                                    ? 'text-emerald-900 line-through dark:text-emerald-300'
                                                                    : 'text-text-primary'
                                                            }`}
                                                        >
                                                            {step.title}
                                                        </span>
                                                        {step.is_repeat && (
                                                            <Badge variant="warning" size="xs">
                                                                {t('care_session.repeat_occurrence', 'Repetition')} #{step.occurrence_number}
                                                            </Badge>
                                                        )}
                                                        {isSkipped && (
                                                            <Badge variant="neutral" size="xs">
                                                                {t('care_session.skipped_badge', 'Skipped')}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    {step.notes && (
                                                        <p className="text-xs text-text-secondary mt-0.5">{step.notes}</p>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Step actions: In Progress, Skip, Repeat */}
                                            <div className="flex items-center gap-1.5">
                                                {!isDone && !isSkipped && (
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            onUpdateStepStatus &&
                                                            onUpdateStepStatus(
                                                                step.id,
                                                                isInProgress ? 'pending' : 'in_progress'
                                                            )
                                                        }
                                                        data-testid={`btn-in-progress-step-${step.id}`}
                                                        className={`rounded-lg border px-2.5 py-1 text-xs font-semibold ${
                                                            isInProgress
                                                                ? 'border-blue-600 bg-blue-600 text-white'
                                                                : 'border-border bg-surface text-text-secondary hover:text-text-primary'
                                                        }`}
                                                    >
                                                        <Play className="h-3 w-3 inline me-1" />
                                                        {isInProgress ? 'Active' : 'In Progress'}
                                                    </button>
                                                )}

                                                {!isDone && !isSkipped && (
                                                    <button
                                                        type="button"
                                                        onClick={() => setSkippingStepId(step.id)}
                                                        data-testid={`btn-skip-step-${step.id}`}
                                                        className="rounded-lg border border-border bg-surface px-2 py-1 text-xs font-semibold text-text-secondary hover:text-danger hover:border-danger"
                                                        title="Skip step"
                                                    >
                                                        <SkipForward className="h-3 w-3" />
                                                    </button>
                                                )}

                                                {/* Repeat step button */}
                                                <button
                                                    type="button"
                                                    onClick={() => setRepeatingStep(step)}
                                                    data-testid={`btn-repeat-step-${step.id}`}
                                                    className="rounded-lg border border-border bg-surface px-2 py-1 text-xs font-semibold text-text-secondary hover:text-primary hover:border-primary"
                                                    title={t('care_session.repeat_step_title', 'Repeat this step as new occurrence')}
                                                >
                                                    <RotateCcw className="h-3 w-3 inline me-1" />
                                                    <span>Repeat</span>
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </section>

                    {/* Skip Step Prompt Modal */}
                    {skippingStepId && (
                        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/40">
                            <h5 className="text-xs font-bold text-amber-900 dark:text-amber-200 mb-2">
                                {t('care_session.skip_reason_prompt', 'Please specify reason for skipping this step:')}
                            </h5>
                            <input
                                type="text"
                                value={skipReason}
                                onChange={(e) => setSkipReason(e.target.value)}
                                placeholder="e.g. Clinical assessment determined step not indicated"
                                className="w-full rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary"
                            />
                            <div className="flex justify-end gap-2 mt-2">
                                <Button size="xs" variant="outline" onClick={() => setSkippingStepId(null)}>
                                    Cancel
                                </Button>
                                <Button size="xs" variant="danger" onClick={handleSkipStepSubmit}>
                                    Confirm Skip
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* Repeat Step Prompt Modal */}
                    {repeatingStep && (
                        <div className="rounded-xl border border-primary/40 bg-primary/5 p-4">
                            <h5 className="text-xs font-bold text-text-primary mb-2">
                                {t('care_session.repeat_prompt', 'Repeat step:')} &quot;{repeatingStep.title}&quot;
                            </h5>
                            <input
                                type="text"
                                value={repeatReason}
                                onChange={(e) => setRepeatReason(e.target.value)}
                                placeholder="Reason for repetition (e.g. Second canal instrumentation pass)"
                                className="w-full rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-primary"
                            />
                            <div className="flex justify-end gap-2 mt-2">
                                <Button size="xs" variant="outline" onClick={() => setRepeatingStep(null)}>
                                    Cancel
                                </Button>
                                <Button size="xs" variant="primary" onClick={handleRepeatStepSubmit}>
                                    Add Repeated Occurrence
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* 3. Custom Fields from Template Snapshot (Requirement 2 & 3) */}
                    {templateSnapshot?.custom_fields?.length > 0 && (
                        <section
                            data-testid="workspace-custom-fields"
                            aria-label="Custom Template Fields"
                            className="rounded-2xl border border-border bg-surface-elevated p-4 shadow-xs"
                        >
                            <div className="flex items-center gap-2 border-b border-border pb-3 mb-3">
                                <Sliders className="h-4 w-4 text-primary" />
                                <h4 className="text-sm font-bold text-text-primary">
                                    {t('care_session.template_fields_title', 'Procedure Specifications & Custom Fields')}
                                </h4>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                                {templateSnapshot.custom_fields.map((field) => {
                                    const val = customFieldValues[field.field_id] ?? '';

                                    return (
                                        <div key={field.field_id} className="space-y-1">
                                            <label className="block text-xs font-bold text-text-primary">
                                                {field.label}
                                                {field.unit && (
                                                    <span className="text-text-secondary ms-1 font-normal">
                                                        ({field.unit})
                                                    </span>
                                                )}
                                                {field.is_required && (
                                                    <span className="text-danger ms-1">*</span>
                                                )}
                                            </label>

                                            {field.description && (
                                                <p className="text-2xs text-text-secondary">{field.description}</p>
                                            )}

                                            {field.field_type === 'choice' && field.choices?.length > 0 ? (
                                                <select
                                                    value={val}
                                                    onChange={(e) => handleCustomFieldChange(field.field_id, e.target.value)}
                                                    data-testid={`custom-field-${field.field_id}`}
                                                    className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                                                >
                                                    <option value="">{t('care_session.select_option', '-- Select --')}</option>
                                                    {field.choices.map((c) => (
                                                        <option key={c} value={c}>
                                                            {c}
                                                        </option>
                                                    ))}
                                                </select>
                                            ) : field.field_type === 'boolean' ? (
                                                <div className="flex items-center gap-2 pt-1">
                                                    <input
                                                        type="checkbox"
                                                        id={`field_${field.field_id}`}
                                                        checked={Boolean(val)}
                                                        onChange={(e) => handleCustomFieldChange(field.field_id, e.target.checked)}
                                                        data-testid={`custom-field-${field.field_id}`}
                                                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                                                    />
                                                    <label htmlFor={`field_${field.field_id}`} className="text-xs text-text-primary font-medium">
                                                        {val ? t('common.yes', 'Yes') : t('common.no', 'No')}
                                                    </label>
                                                </div>
                                            ) : field.field_type === 'number' ? (
                                                <div className="relative">
                                                    <input
                                                        type="number"
                                                        value={val}
                                                        onChange={(e) => handleCustomFieldChange(field.field_id, e.target.value)}
                                                        data-testid={`custom-field-${field.field_id}`}
                                                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                                                    />
                                                    {field.unit && (
                                                        <span className="absolute right-3 top-2 text-xs text-text-secondary">
                                                            {field.unit}
                                                        </span>
                                                    )}
                                                </div>
                                            ) : field.field_type === 'date' ? (
                                                <input
                                                    type="date"
                                                    value={val}
                                                    onChange={(e) => handleCustomFieldChange(field.field_id, e.target.value)}
                                                    data-testid={`custom-field-${field.field_id}`}
                                                    className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                                                />
                                            ) : (
                                                <input
                                                    type="text"
                                                    value={val}
                                                    onChange={(e) => handleCustomFieldChange(field.field_id, e.target.value)}
                                                    data-testid={`custom-field-${field.field_id}`}
                                                    placeholder={field.label}
                                                    className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                                                />
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </section>
                    )}

                    {/* 4. Specialized RCT Workspace (If procedure is ENDO_RCT) */}
                    {isRctProcedure && (
                        <section
                            data-testid="workspace-rct-tools"
                            aria-label="Root Canal Anatomy Tools"
                            className="rounded-2xl border border-primary/20 bg-primary/5 p-4 shadow-xs space-y-4"
                        >
                            <div className="flex items-center gap-2 border-b border-primary/20 pb-3 mb-1">
                                <Sparkles className="h-4 w-4 text-primary" />
                                <h4 className="text-sm font-bold text-text-primary">
                                    {t('care_session.rct_anatomy_title', 'Root Canal Anatomy & Working Length Measurements')}
                                </h4>
                            </div>
                            <CanalTargetSelector
                                toothKey={procedureToothKey}
                                selectedCanals={selectedCanals}
                                onToggleCanal={handleToggleCanal}
                                t={t}
                            />
                            <WorkingLengthEntryTable
                                toothKey={procedureToothKey}
                                selectedCanals={selectedCanals}
                                recordedObservations={procedureObservations}
                                onSaveMeasurement={handleSaveMeasurement}
                                t={t}
                            />
                        </section>
                    )}

                    {/* 5. Procedure Clinical Notes & Next Action */}
                    <section
                        data-testid="workspace-notes-next-action"
                        aria-label="Notes and Next Action"
                        className="rounded-2xl border border-border bg-surface-elevated p-4 shadow-xs space-y-4"
                    >
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <FileText className="h-4 w-4 text-primary" />
                                <span>{t('care_session.proc_notes_label', 'Procedure Visit Notes')}</span>
                            </label>
                            <textarea
                                value={procedureNotes}
                                onChange={(e) => handleNotesChange(e.target.value)}
                                data-testid="workspace-proc-notes-input"
                                rows={3}
                                placeholder={t('care_session.proc_notes_placeholder', 'Document clinical observations, anesthesia, techniques, materials used...')}
                                className="w-full rounded-xl border border-border bg-surface p-3 text-xs text-text-primary focus:border-primary focus:outline-hidden"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                                <Flag className="h-4 w-4 text-emerald-600" />
                                <span>{t('care_session.proc_next_action_label', 'Next Planned Clinical Action')}</span>
                            </label>
                            <input
                                type="text"
                                value={nextAction}
                                onChange={(e) => handleNextActionChange(e.target.value)}
                                data-testid="workspace-proc-next-action-input"
                                placeholder={t('care_session.proc_next_action_placeholder', 'e.g. Master cone fit and obturation')}
                                className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary focus:border-primary focus:outline-hidden"
                            />
                        </div>
                    </section>
                </main>
            </div>
        </DentixDialog>
    );
}

GenericVisitWorkspace.propTypes = {
    session: PropTypes.object.isRequired,
    patient: PropTypes.object,
    patientWorkItems: PropTypes.array,
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onUpdateStepStatus: PropTypes.func,
    onSaveObservation: PropTypes.func,
    onOpenFinishSheet: PropTypes.func.isRequired,
    onOpenMaterialsModal: PropTypes.func,
    onOpenLabHandoff: PropTypes.func,
    draftData: PropTypes.object,
    onDraftChange: PropTypes.func,
    careSessionDraftStatus: PropTypes.string,
    resolveConflict: PropTypes.func,
    refetchSession: PropTypes.func,
    t: PropTypes.func,
};
