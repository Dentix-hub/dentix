import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/auth/useAuth';
import { useAuthStore } from '@/store/auth.store';
import ClinicalChartRenderer from '@/features/clinical-chart/components/ClinicalChartRenderer';
import ChartStickyToolBanner from '@/features/clinical-chart/components/ChartStickyToolBanner';
import ChartQuickActionLauncher from '@/features/clinical-chart/components/ChartQuickActionLauncher';
import QuickTreatmentSheet from '@/features/clinical-chart/components/QuickTreatmentSheet';
import { adaptWorkspaceSnapshotToRenderer } from '@/features/clinical-chart/adapters/workspaceSnapshotAdapter';
import PatientInfoCard from '@/features/patients/PatientInfoCard';
import { useProcedures } from '@/shared/context/ProceduresContext';
import PrescriptionModal from '@/shared/ui/modals/PrescriptionModal';
import PaymentModal from '@/shared/ui/modals/PaymentModal';
import EditPatientModal from '@/features/patients/modals/EditPatientModal.jsx';
import { recordOnboardingEvent } from '@/api/onboarding';
import OnboardingTooltip from '@/features/onboarding/components/OnboardingTooltip';
import { Breadcrumb, Modal, TabGroup, toast } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import { useHotkeys } from 'react-hotkeys-hook';
import {
    usePatient,
    usePatientTeeth,
    usePatientClinicalWorkspace,
    usePatientTreatments,
    usePatientPayments,
    usePatientLabOrders,
    usePatientAttachments,
    useCreatePayment,
    useDeletePayment,
    useTenantFeatures,
    usePatientClinicalPlans,
    useActiveCareSession,
    useResumableCareSession,
    useStartCareSession,
    useFinishCareSession,
    useTransitionCareSession,
    useUpdateCareSessionStep,
    useApplyCareSessionTemplate,
    useRecordCareObservation,
} from '@/hooks/usePatientDetails';
import TreatmentPlansCard from '@/features/clinical-plans/TreatmentPlansCard';
import {
    CareSessionActiveBanner,
    ContinueTreatmentCard,
    GenericVisitWorkspace,
    FinishCareSessionSheet,
    useCareSessionDraft,
} from '@/features/care-sessions';
import { useTreatmentOperations } from '@/features/patients/hooks/useTreatmentOperations';
import { Baby, Sparkles, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';

import { getTodayStr } from '../utils/toothUtils';
import {
    createPatientClinicalFinding,
    createPatientClinicalFindingsBulk,
    createPatientClinicalProcedure,
    createPatientClinicalProceduresBulk,
    updateToothStatus,
} from '../api';

import { TabSkeleton, PatientInfoSkeleton } from '@/features/patients/components/PatientDetailsSkeletons';
import { usePatientTouchScrollGuard } from '@/features/patients/hooks/usePatientTouchScrollGuard';
import { usePatientChartSelection } from '@/features/patients/hooks/usePatientChartSelection';
import { usePatientPlanOverlay } from '@/features/patients/hooks/usePatientPlanOverlay';
import { usePatientRecordActions } from '@/features/patients/hooks/usePatientRecordActions';
import { invalidatePatientClinicalQueries } from '@/features/patients/utils/invalidatePatientClinicalQueries';
import { buildTreatmentPrefill } from '@/features/patients/utils/buildTreatmentPrefill';
import ClinicalWorkspaceStatusBanner from '@/features/patients/components/ClinicalWorkspaceStatusBanner';
import PlanOverlayActiveBanner from '@/features/patients/components/PlanOverlayActiveBanner';
import ChairsideSelectionBar from '@/features/patients/components/ChairsideSelectionBar';

const TreatmentHistory = lazy(() => import('@/features/patients/PatientTabs/TreatmentHistory'));
const PatientFiles = lazy(() => import('@/features/patients/PatientTabs/PatientFiles'));
const PatientBilling = lazy(() => import('@/features/patients/PatientTabs/PatientBilling'));
const LabOrdersTab = lazy(() => import('@/features/lab/LabOrdersTab'));
const PatientTimeline = lazy(() => import('@/features/patients/PatientTabs/PatientTimeline'));

const isNativeWritesDisabledError = (err) => {
    if (err?.response?.status !== 404) return false;
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string') {
        return detail.includes('Clinical native writes are disabled');
    }
    if (detail && typeof detail === 'object') {
        return (
            (typeof detail.message === 'string' && detail.message.includes('Clinical native writes are disabled')) ||
            (typeof detail.detail === 'string' && detail.detail.includes('Clinical native writes are disabled'))
        );
    }
    return false;
};

export default function PatientDetails() {
    let authUser = null;
    try {
        const auth = useAuth();
        authUser = auth?.user;
    } catch {
        authUser = useAuthStore.getState?.()?.user || null;
    }
    const isSuperAdmin = authUser?.role === 'super_admin';

    const queryClient = useQueryClient();
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const { id } = useParams();
    const [searchParams, setSearchParams] = useSearchParams();
    const initialTab = searchParams.get('tab') || 'chart';
    const [activeTab, setActiveTab] = useState(initialTab);

    useEffect(() => {
        if (id) {
            recordOnboardingEvent('patient_file_opened').catch(() => {});
        }
    }, [id]);

    const handleTabChange = (tabId) => {
        setActiveTab(tabId);
        setSearchParams({ tab: tabId }, { replace: true });
    };

    const { procedures, loading: proceduresLoading } = useProcedures();
    const [isPediatric, setIsPediatric] = useState(false);
    const [isToothSelectModalOpen, setIsToothSelectModalOpen] = useState(false);

    const [isEditPatientOpen, setIsEditPatientOpen] = useState(false);
    const [isRxModalOpen, setIsRxModalOpen] = useState(false);
    const [isTreatmentSheetOpen, setIsTreatmentSheetOpen] = useState(false);
    const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);

    const getInitialTreatment = useCallback(() => ({
        date: getTodayStr(),
        diagnosis: '',
        procedure: '',
        cost: '',
        discount: '',
        tooth_number: '',
        surface: '',
        surfaces: [],
        target_kind: 'tooth',
        canal_count: '',
        canals: [{ name: '', length: '' }],
        sessions: '',
        complications: '',
        notes: '',
    }), []);

    const [newTreatment, setNewTreatment] = useState(getInitialTreatment);
    const [editingTreatmentId, setEditingTreatmentId] = useState(null);
    const [selectedToothCondition, setSelectedToothCondition] = useState('Healthy');

    const {
        data: patient,
        isLoading: patientLoading,
        isError: patientIsError,
        error: patientError,
        refetch: refetchPatient,
    } = usePatient(id);
    const { data: teethStatus = {}, refetch: refetchTeeth } = usePatientTeeth(id, activeTab !== 'chart');
    const {
        data: workspaceSnapshot,
        isLoading: workspaceLoading,
        isError: workspaceIsError,
        error: workspaceError,
        refetch: refetchWorkspace,
    } = usePatientClinicalWorkspace(id, { enabled: activeTab === 'chart' || isToothSelectModalOpen });

    const { data: tenantFeatures = [] } = useTenantFeatures();
    const isTreatmentPlansEnabled = Array.isArray(tenantFeatures) && tenantFeatures.includes('clinical_treatment_plans');
    const isNativeWritesEnabled = Array.isArray(tenantFeatures) && tenantFeatures.includes('clinical_vnext_native_writes');

    const effectiveTeethStatusRef = useRef({});
    const executeClinicalActionRef = useRef(null);

    const { isTouchScrollingRef, handleTouchStart, handleTouchMove, handleTouchEnd } = usePatientTouchScrollGuard();

    const {
        selectedTeeth,
        setSelectedTeeth,
        selectedSurfacesByTooth,
        isMultiSelectMode,
        setIsMultiSelectMode,
        setActiveToothKey,
        activeStickyTool,
        setActiveStickyTool,
        stickyAppliedCount,
        setStickyAppliedCount,
        isQuickLauncherOpen,
        setIsQuickLauncherOpen,
        activeOverlayPlanId,
        activeOverlayPhaseId,
        resolvedActiveTooth,
        activeSurfaces,
        handleModalToothSelect,
        handleToothClick,
        handleSurfaceClick,
        handleToggleSurface,
        handleRecordTreatmentFromSelection,
        handleClearSelection,
        handleRemoveToothFromSelection,
        handleTogglePlanOverlay,
    } = usePatientChartSelection({
        isPediatric,
        patient,
        effectiveTeethStatusRef,
        isTouchScrollingRef,
        executeClinicalActionRef,
        setNewTreatment,
        setIsTreatmentSheetOpen,
        setSelectedToothCondition,
        getInitialTreatment,
    });

    const effectiveSnapshot = useMemo(() => {
        if (workspaceSnapshot) return workspaceSnapshot;
        if (!teethStatus || Object.keys(teethStatus).length === 0) return null;
        const teeth = {};
        Object.entries(teethStatus).forEach(([num, item]) => {
            teeth[String(num)] = {
                condition: item?.condition,
                notes: item?.notes,
            };
        });
        return { teeth };
    }, [workspaceSnapshot, teethStatus]);

    const { data: treatmentPlans = [] } = usePatientClinicalPlans(id, {
        enabled: isTreatmentPlansEnabled && !!id,
    });

    const planOverlay = usePatientPlanOverlay({
        activeOverlayPlanId,
        activeOverlayPhaseId,
        treatmentPlans,
    });

    const { data: labOrders = [] } = usePatientLabOrders(
        id,
        activeTab === 'chart' || activeTab === 'labs'
    );

    const { data: activeCareSession, refetch: refetchActiveSession } = useActiveCareSession(id, {
        enabled: !!id && activeTab === 'chart' && isNativeWritesEnabled,
    });
    const { data: resumableCareSession, refetch: refetchResumableSession } = useResumableCareSession(id, {
        enabled: !!id && activeTab === 'chart' && isNativeWritesEnabled,
    });
    const startCareSessionMutation = useStartCareSession();
    const finishCareSessionMutation = useFinishCareSession();
    const transitionCareSessionMutation = useTransitionCareSession();
    const updateCareSessionStepMutation = useUpdateCareSessionStep();
    const applyCareSessionTemplateMutation = useApplyCareSessionTemplate();
    const recordCareObservationMutation = useRecordCareObservation();

    const {
        draftData: careSessionDraftData,
        updateDraft: updateCareSessionDraft,
        discardDraft: discardCareSessionDraft,
        status: careSessionDraftStatus,
        resolveConflict: resolveCareSessionDraftConflict,
    } = useCareSessionDraft({
        patientId: id ? Number(id) : null,
        careSessionId: activeCareSession?.id || null,
        enabled: Boolean(activeCareSession?.id && isNativeWritesEnabled),
    });

    const autosaveIndicator = useMemo(() => {
        if (!activeCareSession || careSessionDraftStatus === 'idle') return null;
        return (
            <div data-testid="care-session-autosave-indicator" className="inline-flex items-center gap-1.5 text-xs">
                {careSessionDraftStatus === 'saving' && (
                    <span className="flex items-center gap-1 text-slate-500 font-medium">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span>{t('care_session.saving_draft', 'Saving draft...')}</span>
                    </span>
                )}
                {careSessionDraftStatus === 'saved' && (
                    <span className="flex items-center gap-1 text-emerald-600 font-medium">
                        <CheckCircle2 className="h-3 w-3" />
                        <span>{t('care_session.draft_saved', 'Draft autosaved')}</span>
                    </span>
                )}
                {careSessionDraftStatus === 'conflict' && (
                    <span className="flex items-center gap-1 text-amber-600 font-bold">
                        <AlertTriangle className="h-3 w-3" />
                        <span>{t('care_session.draft_conflict', 'Draft conflict')}</span>
                        <button
                            type="button"
                            onClick={() => resolveCareSessionDraftConflict({ overwrite: true })}
                            className="underline text-[10px] ml-1 text-amber-700 hover:text-amber-900"
                        >
                            {t('common.overwrite', 'Overwrite')}
                        </button>
                    </span>
                )}
                {careSessionDraftStatus === 'error' && (
                    <span className="flex items-center gap-1 text-red-500 font-medium">
                        <AlertTriangle className="h-3 w-3" />
                        <span>{t('care_session.draft_error', 'Sync error')}</span>
                    </span>
                )}
            </div>
        );
    }, [activeCareSession, careSessionDraftStatus, resolveCareSessionDraftConflict, t]);

    const [isRctWorkflowOpen, setIsRctWorkflowOpen] = useState(false);
    const [isFinishSheetOpen, setIsFinishSheetOpen] = useState(false);
    const [careSessionDisabledNotice, setCareSessionDisabledNotice] = useState(null);

    const handleStartRctSession = useCallback(async (targetToothKey) => {
        try {
            const tooth = targetToothKey || resolvedActiveTooth || '46';
            const sessionRes = await startCareSessionMutation.mutateAsync({
                patientId: id,
                data: { notes: `Started RCT workflow on tooth ${tooth}` },
            });
            const createdSession = sessionRes.data;
            if (createdSession?.id) {
                await applyCareSessionTemplateMutation.mutateAsync({
                    patientId: id,
                    sessionId: createdSession.id,
                    data: { template_code: 'ENDO_RCT' },
                });
                await refetchActiveSession();
                await refetchResumableSession();
                setIsRctWorkflowOpen(true);
                toast.success(t('care_session.rct_started', 'RCT care session started successfully'));
            }
        } catch (err) {
            if (isNativeWritesDisabledError(err)) {
                const disabledMsg = t('care_session.disabled_message', 'ميزة الجلسات الجديدة غير مفعّلة لهذه العيادة');
                toast.error(disabledMsg);
                setCareSessionDisabledNotice(disabledMsg);
                return;
            }
            toast.error(err?.response?.data?.detail?.message || err?.response?.data?.detail || t('care_session.start_error', 'Failed to start care session'));
        }
    }, [id, resolvedActiveTooth, startCareSessionMutation, applyCareSessionTemplateMutation, refetchActiveSession, refetchResumableSession, t]);

    const handleResumeTreatment = useCallback(async ({ workItemId, workItemIds, sessionId, isPaused, toothKey, procedureCode }) => {
        try {
            if (isPaused && sessionId) {
                await transitionCareSessionMutation.mutateAsync({
                    patientId: id,
                    sessionId,
                    data: { to_status: 'in_progress' },
                });
            } else {
                const effectiveWorkItemIds = (workItemIds && workItemIds.length > 0)
                    ? workItemIds
                    : (workItemId ? [workItemId] : undefined);

                const sessionRes = await startCareSessionMutation.mutateAsync({
                    patientId: id,
                    data: {
                        resume_work_item_id: effectiveWorkItemIds?.[0] || workItemId || undefined,
                        resume_work_item_ids: effectiveWorkItemIds,
                        resume_from_session_id: sessionId || undefined,
                        notes: toothKey ? `Resumed treatment on tooth ${toothKey}` : undefined,
                    },
                });
                const createdSession = sessionRes.data;
                if (createdSession?.id) {
                    const existingWorkItemIdsWithSteps = new Set(
                        (createdSession.steps || []).map((s) => s.work_item_id).filter(Boolean)
                    );

                    const itemsToApply = (resumableCareSession?.items || []).filter(
                        (it) => !effectiveWorkItemIds || effectiveWorkItemIds.includes(it.work_item_id)
                    );

                    if (itemsToApply.length > 0) {
                        for (const it of itemsToApply) {
                            if (!existingWorkItemIdsWithSteps.has(it.work_item_id)) {
                                const templateCode = it.procedure_code || 'ENDO_RCT';
                                await applyCareSessionTemplateMutation.mutateAsync({
                                    patientId: id,
                                    sessionId: createdSession.id,
                                    data: { template_code: templateCode, work_item_id: it.work_item_id },
                                });
                            }
                        }
                    } else if (workItemId && !existingWorkItemIdsWithSteps.has(workItemId)) {
                        const templateCode = procedureCode || 'ENDO_RCT';
                        await applyCareSessionTemplateMutation.mutateAsync({
                            patientId: id,
                            sessionId: createdSession.id,
                            data: { template_code: templateCode, work_item_id: workItemId },
                        });
                    }
                }
            }
            await refetchActiveSession();
            await refetchResumableSession();
            setIsRctWorkflowOpen(true);
            toast.success(t('care_session.resumed_success', 'Treatment resumed successfully'));
        } catch (err) {
            if (isNativeWritesDisabledError(err)) {
                const disabledMsg = t('care_session.disabled_message', 'ميزة الجلسات الجديدة غير مفعّلة لهذه العيادة');
                toast.error(disabledMsg);
                setCareSessionDisabledNotice(disabledMsg);
                return;
            }
            toast.error(err?.response?.data?.detail?.message || err?.response?.data?.detail || t('care_session.resume_error', 'Failed to resume treatment'));
        }
    }, [id, resumableCareSession?.items, transitionCareSessionMutation, startCareSessionMutation, applyCareSessionTemplateMutation, refetchActiveSession, refetchResumableSession, t]);

    const handleUpdateStepStatus = useCallback(async (stepId, updateData) => {
        if (!activeCareSession?.id) return;
        try {
            await updateCareSessionStepMutation.mutateAsync({
                patientId: id,
                sessionId: activeCareSession.id,
                stepId,
                data: updateData,
            });
            await refetchActiveSession();
        } catch (err) {
            toast.error(err?.response?.data?.detail || 'Failed to update step');
        }
    }, [id, activeCareSession?.id, updateCareSessionStepMutation, refetchActiveSession]);

    const handleSaveObservation = useCallback(async (obsData) => {
        if (!activeCareSession?.id) return;
        try {
            await recordCareObservationMutation.mutateAsync({
                patientId: id,
                sessionId: activeCareSession.id,
                data: {
                    observation_code: 'working_length',
                    tooth_key: String(obsData.tooth_key),
                    root_id: obsData.root_id,
                    canal_id: obsData.canal_id,
                    structured_value: {
                        length_mm: obsData.length_mm,
                        reference_point: obsData.reference_point,
                        maf: obsData.maf,
                    },
                    notes: obsData.notes,
                },
            });
            await refetchActiveSession();
            toast.success(t('care_session.length_saved', `Saved ${obsData.canal_id} length: ${obsData.length_mm} mm`));
        } catch (err) {
            toast.error(err?.response?.data?.detail || 'Failed to record measurement');
        }
    }, [id, activeCareSession?.id, recordCareObservationMutation, refetchActiveSession, t]);

    const handleFinishSession = useCallback(async ({ notes, next_visit_request } = {}) => {
        if (!activeCareSession?.id) return;
        try {
            await finishCareSessionMutation.mutateAsync({
                patientId: id,
                sessionId: activeCareSession.id,
                data: { notes, next_visit_request },
            });
            await discardCareSessionDraft();
            await refetchActiveSession();
            await refetchResumableSession();
            refetchWorkspace();
            setIsRctWorkflowOpen(false);
            setIsFinishSheetOpen(false);
            toast.success(t('care_session.finished_success', 'Care session completed successfully'));
        } catch (err) {
            toast.error(err?.response?.data?.detail || 'Failed to finish care session');
        }
    }, [id, activeCareSession?.id, finishCareSessionMutation, discardCareSessionDraft, refetchActiveSession, refetchResumableSession, refetchWorkspace, t]);

    const adaptedChart = useMemo(() => {
        return adaptWorkspaceSnapshotToRenderer(effectiveSnapshot, {
            chartId: `patient-chart-${id}`,
            isPediatric,
            showRoots: true,
            showSurfaces: true,
            enableSurfaceSelection: true,
            selectedToothKeys: selectedTeeth,
            selectedSurfacesByTooth,
            planOverlay,
            labOrders,
            onToothClick: handleToothClick,
            onSurfaceClick: handleSurfaceClick,
        });
    }, [effectiveSnapshot, id, isPediatric, selectedTeeth, selectedSurfacesByTooth, planOverlay, labOrders, handleToothClick, handleSurfaceClick]);

    const adaptedModalChart = useMemo(() => {
        return adaptWorkspaceSnapshotToRenderer(effectiveSnapshot, {
            chartId: `patient-modal-chart-${id}`,
            isPediatric,
            showRoots: false,
            showSurfaces: false,
            onToothClick: (toothKey, notation) => {
                handleModalToothSelect(toothKey, notation);
                setIsToothSelectModalOpen(false);
            },
        });
    }, [effectiveSnapshot, id, isPediatric, handleModalToothSelect]);

    const [localTeethStatus] = useState(null);
    const effectiveTeethStatus = localTeethStatus ?? (workspaceSnapshot ? adaptedChart.teethStatus : teethStatus);
    effectiveTeethStatusRef.current = effectiveTeethStatus;

    const { data: history = [], refetch: refetchHistory } = usePatientTreatments(
        id,
        activeTab === 'chart' || activeTab === 'history' || activeTab === 'billing' || activeTab === 'timeline' || activeTab === 'labs'
    );
    const { data: payments = [] } = usePatientPayments(
        id,
        activeTab === 'chart' || activeTab === 'billing' || activeTab === 'timeline'
    );
    const {
        data: attachments = [],
        isLoading: attachmentsLoading,
        refetch: refetchAttachments,
        isPollingStalled: isAttachmentsPollingStalled,
    } = usePatientAttachments(id, activeTab === 'files');

    const { mutateAsync: createPaymentMutate } = useCreatePayment();
    const { mutateAsync: deletePaymentMutate } = useDeletePayment();

    const refetchAllTeeth = useCallback(() => {
        refetchTeeth();
        refetchWorkspace?.();
    }, [refetchTeeth, refetchWorkspace]);

    const { handleSaveTreatment, refetchClinicalData } = useTreatmentOperations({
        patientId: id,
        refetchHistory,
        refetchTeeth: refetchAllTeeth,
        refetchWorkspace,
        setIsTreatmentSheetOpen,
        setEditingTreatmentId,
        editingTreatmentId,
        selectedToothCondition,
    });

    const {
        handleFileUpload,
        handleDeleteAttachment,
        handleSavePatient,
        handleNewAppointment,
        handleSavePayment,
        openManualTreatment,
        handleEditTreatment,
        handleDeleteTreatment,
        handleRemoveWorkItemOrTreatment,
        handleDeletePayment,
        handlePrintInvoice,
        handlePrintRx,
    } = usePatientRecordActions({
        id,
        patient,
        navigate,
        t,
        refetchPatient,
        refetchAttachments,
        refetchHistory,
        refetchWorkspace,
        createPaymentMutate,
        deletePaymentMutate,
        setIsEditPatientOpen,
        setIsPaymentModalOpen,
        setIsTreatmentSheetOpen,
        setIsRxModalOpen,
        setEditingTreatmentId,
        setNewTreatment,
        getInitialTreatment,
    });

    const executeClinicalAction = useCallback(async (actionData) => {
        const { item, toothKeys, targetKind, surfaces } = actionData;
        const primaryTooth = toothKeys?.[0] || resolvedActiveTooth;
        if (!primaryTooth) return false;

        // Flow A: When clinical_vnext_native_writes is enabled, dispatch to G7 endpoints.
        // R01/PD02: Native writes require a canonical code. If item.code is null (custom clinic procedure),
        // fall back to Flow B (legacy modal) because native writes without a legacy Treatment are invisible to billing.
        if (isNativeWritesEnabled && (item.kind === 'finding' || Boolean(item.code))) {
            try {
                const isFinding = item.kind === 'finding';
                if (isFinding) {
                    if (toothKeys && toothKeys.length > 1) {
                        const items = toothKeys.map((tk) => ({
                            code: item.code,
                            targets: targetKind === 'surface' && surfaces && surfaces.length > 0
                                ? surfaces.map((s) => ({ tooth_key: tk, target_kind: 'surface', surface_code: s }))
                                : [{ tooth_key: tk, target_kind: 'tooth' }],
                        }));
                        await createPatientClinicalFindingsBulk(id, { items });
                    } else {
                        const targets = targetKind === 'surface' && surfaces && surfaces.length > 0
                            ? surfaces.map((s) => ({ tooth_key: primaryTooth, target_kind: 'surface', surface_code: s }))
                            : [{ tooth_key: primaryTooth, target_kind: 'tooth' }];
                        await createPatientClinicalFinding(id, { code: item.code, targets });
                    }
                } else {
                    // Procedure
                    if (toothKeys && toothKeys.length > 1) {
                        const items = toothKeys.map((tk) => ({
                            code: item.code,
                            targets: targetKind === 'surface' && surfaces && surfaces.length > 0
                                ? surfaces.map((s) => ({ tooth_key: tk, target_kind: 'surface', surface_code: s }))
                                : [{ tooth_key: tk, target_kind: 'tooth' }],
                        }));
                        await createPatientClinicalProceduresBulk(id, { items });
                    } else {
                        const targets = targetKind === 'surface' && surfaces && surfaces.length > 0
                            ? surfaces.map((s) => ({ tooth_key: primaryTooth, target_kind: 'surface', surface_code: s }))
                            : [{ tooth_key: primaryTooth, target_kind: 'tooth' }];
                        await createPatientClinicalProcedure(id, { code: item.code, targets });
                    }
                }
                await Promise.all([refetchWorkspace?.(), refetchTeeth?.(), refetchHistory?.()]);
                invalidatePatientClinicalQueries(queryClient, id);
                toast.success(t('patient_details.alerts.treatment_save_success', 'Action recorded successfully'));
                return true;
            } catch (err) {
                toast.error(err.response?.data?.detail || t('patient_details.alerts.treatment_save_fail'));
                return false;
            }
        }

        // Flow B: Safe legacy path when native writes are OFF (preserves 100% billing and inventory)
        if (item.kind === 'finding') {
            try {
                const fdiNum = Number.parseInt(primaryTooth, 10);
                const conditionMap = {
                    CARIES: 'Decayed',
                    PAIN: 'Decayed',
                    FRACTURE: 'Fractured',
                };
                const condition = conditionMap[item.code] || 'Decayed';
                await updateToothStatus({
                    patient_id: parseInt(id, 10),
                    tooth_number: fdiNum,
                    condition,
                });
                await Promise.all([refetchTeeth?.(), refetchWorkspace?.()]);
                invalidatePatientClinicalQueries(queryClient, id);
                toast.success(t('patient_details.alerts.treatment_save_success', 'Finding recorded successfully'));
                return true;
            } catch (err) {
                toast.error(t('patient_details.alerts.tooth_update_fail'));
                return false;
            }
        }

        // For procedures: open compact QuickTreatmentSheet pre-populated (U4D / D1)
        const prefill = buildTreatmentPrefill({
            baseTreatment: getInitialTreatment(),
            source: 'quick_launcher',
            toothKey: primaryTooth,
            selectedTeeth: toothKeys && toothKeys.length > 0 ? toothKeys : (primaryTooth ? [primaryTooth] : []),
            selectedSurfacesByTooth: actionData.selectedSurfacesByTooth || selectedSurfacesByTooth || {},
            surfaces,
            targetKind,
            procedureName: item.name,
            defaultPriceListId: patient?.default_price_list_id,
        });
        setNewTreatment(prefill);
        setIsTreatmentSheetOpen(true);
        return true;
    }, [id, resolvedActiveTooth, isNativeWritesEnabled, patient, getInitialTreatment, refetchWorkspace, refetchTeeth, refetchHistory, queryClient, t, selectedSurfacesByTooth]);

    const handlePerformPlanItem = useCallback(({ item, plan, toothKey, surfaces }) => {
        const workItemId = item.work_item?.id || item.work_item_id;
        const code = item.work_item?.code || item.work_item?.procedure_code;

        let matchedProcedureName = item.work_item?.display_name || '';
        if (procedures && procedures.length > 0) {
            const match = procedures.find(
                (p) => (code && p.canonical_code === code) || p.name === matchedProcedureName
            );
            if (match) {
                matchedProcedureName = match.name;
            }
        }

        const prefill = buildTreatmentPrefill({
            baseTreatment: getInitialTreatment(),
            source: 'plan_item',
            toothKey,
            surfaces,
            procedureName: matchedProcedureName,
            clinicalWorkItemId: workItemId,
            planTitle: plan?.title,
            planId: plan?.id,
            workItemCode: code,
            defaultPriceListId: patient?.default_price_list_id,
        });
        setNewTreatment(prefill);
        setIsTreatmentSheetOpen(true);
    }, [procedures, patient, getInitialTreatment]);

    executeClinicalActionRef.current = executeClinicalAction;
    const handleQuickLauncherAction = executeClinicalAction;

    useHotkeys('n', (event) => {
        event.preventDefault();
        handleNewAppointment();
    }, [handleNewAppointment]);

    useHotkeys('t', (event) => {
        event.preventDefault();
        setIsToothSelectModalOpen(true);
    });

    useHotkeys('e', (event) => {
        event.preventDefault();
        setIsEditPatientOpen(true);
    });

    useHotkeys('/', (event) => {
        if (activeTab === 'chart') {
            const target = event.target;
            if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
                return;
            }
            event.preventDefault();
            if (selectedTeeth.length === 0) {
                setSelectedTeeth(['16']);
                setActiveToothKey('16');
            }
            setTimeout(() => {
                const searchInput = document.querySelector('[data-testid="chart-quick-action-search"]');
                searchInput?.focus();
            }, 50);
        }
    }, [activeTab, selectedTeeth, setSelectedTeeth, setActiveToothKey]);

    useHotkeys('alt+k', (event) => {
        if (activeTab === 'chart') {
            event.preventDefault();
            if (selectedTeeth.length === 0) {
                setSelectedTeeth(['16']);
                setActiveToothKey('16');
            }
            setTimeout(() => {
                const searchInput = document.querySelector('[data-testid="chart-quick-action-search"]');
                searchInput?.focus();
            }, 50);
        }
    }, [activeTab, selectedTeeth, setSelectedTeeth, setActiveToothKey]);

    return (
        <div className="min-w-0 space-y-4 pb-8 sm:space-y-6 sm:pb-10">
            {!patientIsError && !patientLoading && patient && (
                <div className="min-w-0 overflow-hidden">
                    <Breadcrumb items={[
                        { label: t('sidebar.patients'), to: '/patients' },
                        { label: patient.name },
                    ]} />
                </div>
            )}

            {patientIsError ? (
                <section className="rounded-xl border border-red-200 bg-red-50 p-3 text-red-700 sm:p-4">
                    <h2 className="mb-1 font-bold text-red-700">{t('patient_details.loading_error')}</h2>
                    <p className="break-words text-sm text-red-700">
                        {patientError?.response?.data?.detail || patientError?.message || t('patient_details.unknown_error')}
                    </p>
                    <div className="mt-3 grid grid-cols-1 gap-2 min-[360px]:grid-cols-2 sm:flex">
                        <button
                            type="button"
                            onClick={() => refetchPatient()}
                            className="min-h-11 rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-bold text-red-700 transition-colors hover:bg-red-50"
                        >
                            {t('patient_details.retry')}
                        </button>
                        <button
                            type="button"
                            onClick={() => navigate('/')}
                            className="min-h-11 rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-red-700"
                        >
                            {t('patient_details.login')}
                        </button>
                    </div>
                </section>
            ) : patientLoading ? (
                <PatientInfoSkeleton />
            ) : patient ? (
                <PatientInfoCard
                    patient={patient}
                    onEdit={() => setIsEditPatientOpen(true)}
                    onPrescription={() => setIsRxModalOpen(true)}
                    onNewAppointment={handleNewAppointment}
                />
            ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                    {t('patient_details.no_data')}
                </div>
            )}

            <section className="min-h-[32rem] min-w-0 rounded-2xl border border-border bg-surface p-2 shadow-sm sm:p-4 lg:min-h-[600px] lg:p-6">
                <TabGroup
                    activeTab={activeTab}
                    onChange={handleTabChange}
                    tabs={[
                        { id: 'chart', label: t('patients.tabs.chart'), icon: '🦷' },
                        { id: 'timeline', label: t('patients.tabs.timeline', 'الجدول الزمني'), icon: '📅' },
                        { id: 'history', label: t('patients.tabs.history'), icon: '📝' },
                        { id: 'billing', label: t('patients.tabs.billing'), icon: '💰' },
                        { id: 'files', label: t('patients.tabs.files'), icon: '📁' },
                        { id: 'labs', label: t('patients.tabs.labs'), icon: '🔬' },
                    ]}
                />

                <div className="mt-4 min-w-0 sm:mt-6 lg:mt-8">
                    <Suspense fallback={<TabSkeleton />}>
                        {activeTab === 'chart' && (
                            <div className="min-w-0 space-y-4">
                                <div className="flex min-w-0 flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                    <div className="min-w-0">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <h3 className="break-words font-bold text-slate-800 dark:text-white">{t('patient_details.chart.title')}</h3>
                                            {!workspaceLoading && !workspaceIsError && isSuperAdmin && (
                                                <span
                                                    data-testid="clinical-workspace-read-mode"
                                                    data-read-mode={adaptedChart.readMode}
                                                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                                        adaptedChart.readMode === 'VNEXT_PRIMARY'
                                                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                                                            : adaptedChart.readMode === 'SHADOW'
                                                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                                                            : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                                                    }`}
                                                >
                                                    {t(`clinical.read_mode.${adaptedChart.readMode?.toLowerCase()}`, adaptedChart.readMode)}
                                                </span>
                                            )}
                                        </div>
                                        <p className="mt-1 break-words text-xs text-slate-500 dark:text-slate-400">{t('patient_details.chart.subtitle')}</p>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-2 md:w-auto">
                                        <button
                                            type="button"
                                            onClick={() => setIsPediatric(value => !value)}
                                            className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold transition-colors ${isPediatric ? 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300' : 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}
                                            title={t('patient_details.chart.pediatric_mode')}
                                        >
                                            <Baby size={16} className="shrink-0" aria-hidden="true" />
                                            <span>{isPediatric ? t('patient_details.chart.child') : t('patient_details.chart.adult')}</span>
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setIsMultiSelectMode(value => !value)}
                                            aria-pressed={isMultiSelectMode}
                                            data-testid="chart-multi-select-toggle"
                                            className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold transition-colors ${isMultiSelectMode ? 'border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300 ring-2 ring-blue-500' : 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}
                                        >
                                            <span>{t('patient_details.chart.multi_select', 'Multi-Select')}</span>
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setIsQuickLauncherOpen(value => !value)}
                                            aria-pressed={isQuickLauncherOpen || !!activeStickyTool}
                                            data-testid="chart-quick-tool-toggle"
                                            className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold transition-colors ${isQuickLauncherOpen || activeStickyTool ? 'border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300 ring-2 ring-blue-500' : 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}
                                            title={t('patient_details.chart.quick_tools', 'Quick Tools')}
                                        >
                                            <Sparkles size={16} className="shrink-0 text-amber-500" aria-hidden="true" />
                                            <span>{t('patient_details.chart.quick_tools', 'Quick Tools')}</span>
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setIsToothSelectModalOpen(true)}
                                            data-testid="header-advanced-entry-button"
                                            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                            title={t('patient_details.chart.advanced_entry_tooltip', 'Open classic treatment entry modal')}
                                        >
                                            <span>{t('patient_details.chart.advanced_entry', 'Advanced Entry')}</span>
                                            <span className="sr-only">{t('patient_details.chart.new_treatment')}</span>
                                        </button>
                                    </div>
                                </div>

                                {!workspaceLoading && !workspaceIsError && (
                                    <ClinicalWorkspaceStatusBanner adaptedChart={adaptedChart} t={t} />
                                )}

                                {workspaceLoading ? (
                                    <TabSkeleton />
                                ) : workspaceIsError ? (
                                    <section
                                        data-testid="clinical-workspace-error"
                                        className="rounded-xl border border-red-200 bg-red-50 p-3 text-red-700 sm:p-4"
                                    >
                                        <h4 className="font-bold">{t('patient_details.chart_error', 'Failed to load clinical workspace')}</h4>
                                        <p className="mt-1 text-sm">{workspaceError?.response?.data?.detail || workspaceError?.message || t('patient_details.unknown_error')}</p>
                                        <button
                                            type="button"
                                            onClick={() => refetchWorkspace()}
                                            className="mt-3 min-h-9 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-bold text-red-700 transition-colors hover:bg-red-50"
                                        >
                                            {t('patient_details.retry', 'Retry')}
                                        </button>
                                    </section>
                                ) : (
                                    <>
                                        {careSessionDisabledNotice && (
                                            <div
                                                data-testid="care-session-disabled-notice"
                                                className="mb-3 p-3.5 rounded-lg border border-amber-300 bg-amber-50 text-amber-900 flex items-center justify-between text-sm shadow-sm"
                                                role="alert"
                                            >
                                                <span className="font-medium">{careSessionDisabledNotice}</span>
                                                <button
                                                    type="button"
                                                    onClick={() => setCareSessionDisabledNotice(null)}
                                                    className="text-amber-700 hover:text-amber-900 text-sm font-bold px-2 py-0.5 rounded"
                                                    aria-label="Close"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        )}
                                        {activeCareSession ? (
                                            <div className="mb-3">
                                                <CareSessionActiveBanner
                                                    session={activeCareSession}
                                                    onOpenWorkflow={() => setIsRctWorkflowOpen(true)}
                                                    onOpenFinishSheet={() => setIsFinishSheetOpen(true)}
                                                    patientId={id}
                                                    autosaveIndicator={autosaveIndicator}
                                                    t={t}
                                                />
                                            </div>
                                        ) : resumableCareSession?.has_resumable ? (
                                            <div className="mb-3">
                                                <ContinueTreatmentCard
                                                    resumableContext={resumableCareSession}
                                                    onResumeTreatment={handleResumeTreatment}
                                                    isResuming={startCareSessionMutation.isPending || transitionCareSessionMutation.isPending}
                                                    t={t}
                                                />
                                            </div>
                                        ) : null}
                                        <div
                                            onTouchStart={handleTouchStart}
                                            onTouchMove={handleTouchMove}
                                            onTouchEnd={handleTouchEnd}
                                            onTouchCancel={handleTouchEnd}
                                            className="space-y-3"
                                        >
                                            {activeStickyTool && (
                                                <ChartStickyToolBanner
                                                    activeTool={activeStickyTool}
                                                    appliedCount={stickyAppliedCount}
                                                    onExit={() => {
                                                        setActiveStickyTool(null);
                                                        setStickyAppliedCount(0);
                                                    }}
                                                    onSurfaceToggle={(surf) => {
                                                        setActiveStickyTool((prev) => {
                                                            if (!prev) return null;
                                                            const exists = prev.surfaces?.includes(surf);
                                                            const nextSurfaces = exists
                                                                ? prev.surfaces.filter((s) => s !== surf)
                                                                : [...(prev.surfaces || []), surf];
                                                            return { ...prev, surfaces: nextSurfaces };
                                                        });
                                                    }}
                                                />
                                            )}
                                            <PlanOverlayActiveBanner
                                                planOverlay={planOverlay}
                                                onToggleOverlay={handleTogglePlanOverlay}
                                                t={t}
                                            />
                                            <OnboardingTooltip tipKey="chart_click_tip" content={t('onboarding.chart_click_tip')} side="top">
                                                <ClinicalChartRenderer input={adaptedChart.rendererInput} />
                                            </OnboardingTooltip>
                                        </div>

                                        {isQuickLauncherOpen && selectedTeeth.length === 0 && (
                                            <div className="mt-3">
                                                <ChartQuickActionLauncher
                                                    selectedTeeth={[]}
                                                    selectedSurfacesByTooth={{}}
                                                    onAction={handleQuickLauncherAction}
                                                    onActivateStickyTool={(tool) => {
                                                        setActiveStickyTool(tool);
                                                        setStickyAppliedCount(0);
                                                    }}
                                                    clinicProcedures={procedures}
                                                    isLoading={proceduresLoading}
                                                    onClose={() => setIsQuickLauncherOpen(false)}
                                                />
                                            </div>
                                        )}

                                        <ChairsideSelectionBar
                                            selectedTeeth={selectedTeeth}
                                            resolvedActiveTooth={resolvedActiveTooth}
                                            setActiveToothKey={setActiveToothKey}
                                            handleRemoveToothFromSelection={handleRemoveToothFromSelection}
                                            isMultiSelectMode={isMultiSelectMode}
                                            handleClearSelection={handleClearSelection}
                                            handleRecordTreatmentFromSelection={handleRecordTreatmentFromSelection}
                                            activeSurfaces={activeSurfaces}
                                            handleToggleSurface={handleToggleSurface}
                                            selectedSurfacesByTooth={selectedSurfacesByTooth}
                                            handleQuickLauncherAction={handleQuickLauncherAction}
                                            setActiveStickyTool={setActiveStickyTool}
                                            setStickyAppliedCount={setStickyAppliedCount}
                                            procedures={procedures}
                                            proceduresLoading={proceduresLoading}
                                            i18n={i18n}
                                            t={t}
                                            adaptedChart={adaptedChart}
                                            workspaceSnapshot={workspaceSnapshot}
                                            history={history}
                                            treatmentPlans={treatmentPlans}
                                            payments={payments}
                                            labOrders={labOrders}
                                            handleRemoveWorkItemOrTreatment={handleRemoveWorkItemOrTreatment}
                                            activeCareSession={activeCareSession}
                                            onStartRctSession={handleStartRctSession}
                                            onOpenRctWorkflow={() => setIsRctWorkflowOpen(true)}
                                            patientId={id}
                                            attachments={attachments}
                                        />
                                    </>
                                )}

                                {isTreatmentPlansEnabled && (
                                    <TreatmentPlansCard
                                        patientId={id}
                                        activeOverlayPlanId={activeOverlayPlanId}
                                        activeOverlayPhaseId={activeOverlayPhaseId}
                                        onToggleOverlay={handleTogglePlanOverlay}
                                        onPerformItem={handlePerformPlanItem}
                                        isNativeWritesEnabled={isNativeWritesEnabled}
                                    />
                                )}
                            </div>
                        )}

                        {activeTab === 'timeline' && <PatientTimeline history={history} payments={payments} t={t} />}

                        {activeTab === 'history' && (
                            <TreatmentHistory
                                history={history}
                                patientId={id}
                                onAdd={openManualTreatment}
                                onEdit={handleEditTreatment}
                                onDelete={handleDeleteTreatment}
                            />
                        )}

                        {activeTab === 'files' && (
                            <PatientFiles
                                attachments={attachments}
                                handleFileUpload={handleFileUpload}
                                handleDeleteAttachment={handleDeleteAttachment}
                                loading={attachmentsLoading}
                                reloadAttachments={refetchAttachments}
                                isPollingStalled={isAttachmentsPollingStalled}
                                patientId={id}
                                activeCareSession={activeCareSession}
                                workItems={workspaceSnapshot?.work_items || []}
                            />
                        )}

                        {activeTab === 'billing' && (
                            <PatientBilling
                                patientId={id}
                                history={history}
                                payments={payments}
                                onAddPayment={() => setIsPaymentModalOpen(true)}
                                onDeletePayment={handleDeletePayment}
                                onPrintInvoice={handlePrintInvoice}
                                tenantFeatures={tenantFeatures}
                            />
                        )}

                        {activeTab === 'labs' && <LabOrdersTab patientId={id} treatments={history} />}
                    </Suspense>
                </div>
            </section>

            <EditPatientModal
                isOpen={isEditPatientOpen}
                onClose={() => setIsEditPatientOpen(false)}
                onSave={handleSavePatient}
                initialData={patient}
            />

            <QuickTreatmentSheet
                isOpen={isTreatmentSheetOpen}
                onClose={() => {
                    setIsTreatmentSheetOpen(false);
                    setEditingTreatmentId(null);
                }}
                onSave={handleSaveTreatment}
                onRefetch={refetchClinicalData}
                initialData={newTreatment}
                isEditing={Boolean(editingTreatmentId)}
                isNativeWritesEnabled={isNativeWritesEnabled}
                procedures={procedures}
                patient={patient}
                selectedToothCondition={selectedToothCondition}
                setSelectedToothCondition={setSelectedToothCondition}
                selectedTeeth={selectedTeeth}
                selectedSurfacesByTooth={selectedSurfacesByTooth}
                onSelectionChange={setSelectedTeeth}
            />

            <PrescriptionModal
                isOpen={isRxModalOpen}
                onClose={() => setIsRxModalOpen(false)}
                onPrint={handlePrintRx}
            />

            <PaymentModal
                isOpen={isPaymentModalOpen}
                onClose={() => setIsPaymentModalOpen(false)}
                onAdd={handleSavePayment}
            />

            <Modal
                isOpen={isToothSelectModalOpen}
                onClose={() => setIsToothSelectModalOpen(false)}
                title={t('patientDetails.chart.select_tooth')}
                size="lg"
            >
                <div className="min-w-0 space-y-4">
                    <ClinicalChartRenderer input={adaptedModalChart.rendererInput} />
                    <div className="sticky bottom-0 z-10 -mx-3 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 sm:-mx-4 sm:px-4">
                        <button
                            type="button"
                            onClick={() => {
                                setNewTreatment({
                                    ...getInitialTreatment(),
                                    tooth_number: '',
                                    default_price_list_id: patient?.default_price_list_id,
                                });
                                setIsTreatmentSheetOpen(true);
                                setIsToothSelectModalOpen(false);
                            }}
                            className="min-h-11 w-full rounded-xl bg-slate-100 px-4 py-2.5 font-bold text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                        >
                            {t('patient_details.chart.continue_no_tooth')}
                        </button>
                    </div>
                </div>
            </Modal>

            {isRctWorkflowOpen && activeCareSession && (
                <GenericVisitWorkspace
                    session={activeCareSession}
                    patient={patient}
                    patientWorkItems={workspaceSnapshot?.work_items || []}
                    isOpen={isRctWorkflowOpen}
                    onClose={() => setIsRctWorkflowOpen(false)}
                    onUpdateStepStatus={handleUpdateStepStatus}
                    onSaveObservation={handleSaveObservation}
                    onOpenFinishSheet={() => {
                        setIsRctWorkflowOpen(false);
                        setIsFinishSheetOpen(true);
                    }}
                    draftData={careSessionDraftData}
                    onDraftChange={updateCareSessionDraft}
                    careSessionDraftStatus={careSessionDraftStatus}
                    resolveConflict={resolveCareSessionDraftConflict}
                    refetchSession={refetchActiveSession}
                    t={t}
                />
            )}

            {isFinishSheetOpen && activeCareSession && (
                <FinishCareSessionSheet
                    isOpen={isFinishSheetOpen}
                    onClose={() => setIsFinishSheetOpen(false)}
                    session={activeCareSession}
                    onFinishSession={handleFinishSession}
                    isFinishing={finishCareSessionMutation.isPending}
                    draftData={careSessionDraftData}
                    onDraftChange={updateCareSessionDraft}
                    t={t}
                />
            )}
        </div>
    );
}
