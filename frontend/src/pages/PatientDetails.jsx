import { lazy, memo, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import ClinicalChartRenderer from '@/features/clinical-chart/components/ClinicalChartRenderer';
import ClinicalChartInspector from '@/features/clinical-chart/components/ClinicalChartInspector';
import ChartQuickActionLauncher from '@/features/clinical-chart/components/ChartQuickActionLauncher';
import ChartStickyToolBanner from '@/features/clinical-chart/components/ChartStickyToolBanner';
import { getSmartTargetKindAndSurfaces } from '@/features/clinical-chart/domain/catalogDefinitions';
import { CLINICAL_CHART_COPY } from '@/features/clinical-chart/components/clinicalChartWorkspaceCopy';
import { adaptWorkspaceSnapshotToRenderer } from '@/features/clinical-chart/adapters/workspaceSnapshotAdapter';
import PatientInfoCard from '@/features/patients/PatientInfoCard';
import { useProcedures } from '@/shared/context/ProceduresContext';
import TreatmentModal from '@/shared/ui/modals/TreatmentModal';
import PrescriptionModal from '@/shared/ui/modals/PrescriptionModal';
import PaymentModal from '@/shared/ui/modals/PaymentModal';
import EditPatientModal from '@/features/patients/modals/EditPatientModal.jsx';
import { Breadcrumb, Modal, SkeletonBox, TabGroup, toast } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import { useHotkeys } from 'react-hotkeys-hook';
import {
    usePatient,
    usePatientTeeth,
    usePatientClinicalWorkspace,
    usePatientTreatments,
    usePatientPayments,
    usePatientAttachments,
    useCreatePayment,
    useDeletePayment,
    useTenantFeatures,
    usePatientClinicalPlans,
} from '@/hooks/usePatientDetails';
import TreatmentPlansCard from '@/features/clinical-plans/TreatmentPlansCard';
import { useTreatmentOperations } from '@/features/patients/hooks/useTreatmentOperations';
import { Baby, Sparkles } from 'lucide-react';

import { toothToNumber, fdiToPalmer, getTodayStr, universalToPalmer } from '../utils/toothUtils';
import {
    updatePatient,
    deleteTreatment,
    uploadAttachment,
    deleteAttachment,
    createPrescription,
    createPatientClinicalFinding,
    createPatientClinicalFindingsBulk,
    createPatientClinicalProcedure,
    createPatientClinicalProceduresBulk,
    updatePatientClinicalWorkItem,
    updateToothStatus,
} from '../api';

const TreatmentHistory = lazy(() => import('@/features/patients/PatientTabs/TreatmentHistory'));
const PatientFiles = lazy(() => import('@/features/patients/PatientTabs/PatientFiles'));
const PatientBilling = lazy(() => import('@/features/patients/PatientTabs/PatientBilling'));
const LabOrdersTab = lazy(() => import('@/features/lab/LabOrdersTab'));
const PatientTimeline = lazy(() => import('@/features/patients/PatientTabs/PatientTimeline'));

const TabSkeleton = memo(() => (
    <div className="space-y-3 p-2 sm:space-y-4 sm:p-4">
        <SkeletonBox height="4rem" className="rounded-xl" />
        <SkeletonBox height="4rem" className="rounded-xl" />
        <SkeletonBox height="4rem" className="rounded-xl" />
    </div>
));
TabSkeleton.displayName = 'TabSkeleton';

const PatientInfoSkeleton = memo(() => (
    <div className="flex min-w-0 items-center gap-3 rounded-2xl border border-border bg-surface p-3 animate-pulse sm:gap-4 sm:rounded-3xl sm:p-6">
        <div className="h-12 w-12 shrink-0 rounded-xl bg-slate-200 dark:bg-slate-700 sm:h-16 sm:w-16 sm:rounded-2xl" />
        <div className="min-w-0 flex-1 space-y-2">
            <div className="h-6 w-2/3 max-w-48 rounded bg-slate-200 dark:bg-slate-700" />
            <div className="h-4 w-1/2 max-w-32 rounded bg-slate-200 dark:bg-slate-700" />
        </div>
    </div>
));
PatientInfoSkeleton.displayName = 'PatientInfoSkeleton';

export default function PatientDetails() {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const { id } = useParams();
    const [searchParams, setSearchParams] = useSearchParams();
    const initialTab = searchParams.get('tab') || 'chart';
    const [activeTab, setActiveTab] = useState(initialTab);

    const handleTabChange = (tabId) => {
        setActiveTab(tabId);
        setSearchParams({ tab: tabId }, { replace: true });
    };

    const { procedures } = useProcedures();
    const [isPediatric, setIsPediatric] = useState(false);
    const [isToothSelectModalOpen, setIsToothSelectModalOpen] = useState(false);

    const [selectedTeeth, setSelectedTeeth] = useState([]);
    const [selectedSurfacesByTooth, setSelectedSurfacesByTooth] = useState({});
    const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
    const [activeToothKey, setActiveToothKey] = useState(null);
    const [isModifierKeyDown, setIsModifierKeyDown] = useState(false);

    // Sticky tool mode states
    const [activeStickyTool, setActiveStickyTool] = useState(null);
    const [stickyAppliedCount, setStickyAppliedCount] = useState(0);
    const [isQuickLauncherOpen, setIsQuickLauncherOpen] = useState(false);
    const executeClinicalActionRef = useRef(null);

    // Mobile touch scroll safety guard
    const touchStartPosRef = useRef({ x: 0, y: 0, time: 0 });
    const isTouchScrollingRef = useRef(false);

    const handleTouchStart = useCallback((e) => {
        if (e.touches && e.touches.length > 0) {
            touchStartPosRef.current = {
                x: e.touches[0].clientX,
                y: e.touches[0].clientY,
                time: Date.now(),
            };
            isTouchScrollingRef.current = false;
        }
    }, []);

    const handleTouchMove = useCallback((e) => {
        if (e.touches && e.touches.length > 0) {
            const dx = e.touches[0].clientX - touchStartPosRef.current.x;
            const dy = e.touches[0].clientY - touchStartPosRef.current.y;
            if (Math.hypot(dx, dy) > 8) {
                isTouchScrollingRef.current = true;
            }
        }
    }, []);

    const handleTouchEnd = useCallback(() => {
        if (isTouchScrollingRef.current) {
            setTimeout(() => {
                isTouchScrollingRef.current = false;
            }, 250);
        }
    }, []);

    useEffect(() => {
        if (!activeStickyTool) return;
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                setActiveStickyTool(null);
                setStickyAppliedCount(0);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [activeStickyTool]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.shiftKey || e.ctrlKey || e.metaKey || e.key === 'Shift' || e.key === 'Control' || e.key === 'Meta') {
                setIsModifierKeyDown(true);
            }
        };
        const handleKeyUp = (e) => {
            if (!e.shiftKey && !e.ctrlKey && !e.metaKey) {
                setIsModifierKeyDown(false);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, []);

    const resolvedActiveTooth = activeToothKey || selectedTeeth[selectedTeeth.length - 1] || null;
    const activeSurfaces = (resolvedActiveTooth && selectedSurfacesByTooth[resolvedActiveTooth]) || [];

    const {
        data: patient,
        isLoading: patientLoading,
        isError: patientIsError,
        error: patientError,
        refetch: refetchPatient
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

    const handleModalToothSelect = useCallback((number, notation = 'universal') => {
        const isFdiKey = notation === 'fdi';
        const fdi = isFdiKey ? Number.parseInt(number, 10) : toothToNumber(number);
        const current = effectiveTeethStatusRef.current[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);
        const palmerPrefix = isFdiKey
            ? fdiToPalmer(fdi)
            : universalToPalmer(number, isPediatric);
        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: palmerPrefix,
            surface: '',
            surfaces: [],
            target_kind: 'tooth',
            default_price_list_id: patient?.default_price_list_id,
        });
        setIsTreatmentModalOpen(true);
    }, [isPediatric, patient]);

    const handleToothClick = useCallback((number, notation = 'universal') => {
        if (isTouchScrollingRef.current) {
            return;
        }

        const isFdiKey = notation === 'fdi';
        const fdi = isFdiKey ? Number.parseInt(number, 10) : toothToNumber(number);
        const toothKey = String(fdi);
        const current = effectiveTeethStatusRef.current[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);

        // Sticky Tool Mode handling
        if (activeStickyTool && activeStickyTool.item) {
            const { item, targetKind, surfaces } = activeStickyTool;
            let effectiveTargetKind = targetKind;
            let effectiveSurfaces = surfaces || [];

            if (effectiveTargetKind === 'surface' && effectiveSurfaces.length === 0) {
                const smart = getSmartTargetKindAndSurfaces(item, toothKey, []);
                effectiveSurfaces = smart.surfaces.length > 0 ? smart.surfaces : [smart.defaultSurface || 'O'];
            }

            executeClinicalActionRef.current?.({
                item,
                toothKeys: [toothKey],
                targetKind: effectiveTargetKind,
                surfaces: effectiveSurfaces,
                defaultPrice: item.defaultPrice || 0,
            })?.then((success) => {
                if (success) {
                    setStickyAppliedCount((prev) => prev + 1);
                }
            });

            setActiveToothKey(toothKey);
            return;
        }

        const isMulti = isMultiSelectMode || isModifierKeyDown;

        if (isMulti) {
            setSelectedTeeth(prev => {
                if (prev.includes(toothKey)) {
                    return prev.filter(k => k !== toothKey);
                }
                return [...prev, toothKey];
            });
            setActiveToothKey(toothKey);
        } else {
            setSelectedTeeth([toothKey]);
            setActiveToothKey(toothKey);
        }
    }, [isMultiSelectMode, isModifierKeyDown, activeStickyTool]);

    const handleSurfaceClick = useCallback((target) => {
        if (isTouchScrollingRef.current) {
            return;
        }
        if (!target) return;
        const toothKey = String(target.toothKey || target.tooth_key || '');
        const surfaceCode = String(target.surfaceCode || target.surface_code || '').toUpperCase();
        if (!toothKey) return;

        const fdi = Number.parseInt(toothKey, 10);
        const current = effectiveTeethStatusRef.current[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);

        // Sticky Tool Mode handling on surface
        if (activeStickyTool && activeStickyTool.item) {
            const { item } = activeStickyTool;
            executeClinicalActionRef.current?.({
                item,
                toothKeys: [toothKey],
                targetKind: 'surface',
                surfaces: [surfaceCode],
                defaultPrice: item.defaultPrice || 0,
            })?.then((success) => {
                if (success) {
                    setStickyAppliedCount((prev) => prev + 1);
                }
            });

            setActiveToothKey(toothKey);
            return;
        }

        setSelectedTeeth(prev => {
            if (prev.includes(toothKey)) return prev;
            return isMultiSelectMode ? [...prev, toothKey] : [toothKey];
        });
        setActiveToothKey(toothKey);

        if (surfaceCode) {
            setSelectedSurfacesByTooth(prev => {
                const currentSurfaces = prev[toothKey] || [];
                const nextSurfaces = currentSurfaces.includes(surfaceCode)
                    ? currentSurfaces.filter(s => s !== surfaceCode)
                    : [...currentSurfaces, surfaceCode];
                return {
                    ...prev,
                    [toothKey]: nextSurfaces,
                };
            });
        }
    }, [isMultiSelectMode, activeStickyTool]);

    const handleToggleSurface = useCallback((surfaceCode) => {
        if (!resolvedActiveTooth) return;
        const surfaceUpper = String(surfaceCode).toUpperCase();
        setSelectedSurfacesByTooth(prev => {
            const currentSurfaces = prev[resolvedActiveTooth] || [];
            const nextSurfaces = currentSurfaces.includes(surfaceUpper)
                ? currentSurfaces.filter(s => s !== surfaceUpper)
                : [...currentSurfaces, surfaceUpper];
            return {
                ...prev,
                [resolvedActiveTooth]: nextSurfaces,
            };
        });
    }, [resolvedActiveTooth]);

    const handleRecordTreatmentFromSelection = useCallback(() => {
        const toothKey = resolvedActiveTooth || selectedTeeth[0];
        if (!toothKey) return;
        const fdi = Number.parseInt(toothKey, 10);
        const palmerPrefix = fdiToPalmer(fdi);
        const surfaces = selectedSurfacesByTooth[toothKey] || [];
        const surfaceUpper = surfaces.join('');

        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: palmerPrefix,
            surface: surfaceUpper,
            surfaces: [...surfaces],
            target_kind: surfaces.length > 0 ? 'surface' : 'tooth',
            default_price_list_id: patient?.default_price_list_id,
        });
        setIsTreatmentModalOpen(true);
    }, [resolvedActiveTooth, selectedTeeth, selectedSurfacesByTooth, patient]);

    const handleClearSelection = useCallback(() => {
        setSelectedTeeth([]);
        setSelectedSurfacesByTooth({});
        setActiveToothKey(null);
    }, []);

    const handleRemoveToothFromSelection = useCallback((toothKey) => {
        setSelectedTeeth(prev => prev.filter(k => k !== toothKey));
        setSelectedSurfacesByTooth(prev => {
            const copy = { ...prev };
            delete copy[toothKey];
            return copy;
        });
        setActiveToothKey(prev => (prev === toothKey ? null : prev));
    }, []);

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

    const [activeOverlayPlanId, setActiveOverlayPlanId] = useState(null);
    const [activeOverlayPhaseId, setActiveOverlayPhaseId] = useState(null);

    const { data: treatmentPlans = [] } = usePatientClinicalPlans(id, {
        enabled: isTreatmentPlansEnabled && !!id,
    });

    const handleTogglePlanOverlay = useCallback((planId, phaseId = null) => {
        setActiveOverlayPlanId((prevPlanId) => {
            if (prevPlanId === planId && (phaseId === null || activeOverlayPhaseId === phaseId)) {
                setActiveOverlayPhaseId(null);
                return null;
            }
            setActiveOverlayPhaseId(phaseId);
            return planId;
        });
    }, [activeOverlayPhaseId]);

    const planOverlay = useMemo(() => {
        if (!activeOverlayPlanId || !treatmentPlans || treatmentPlans.length === 0) return null;
        const plan = treatmentPlans.find((p) => p.id === activeOverlayPlanId);
        if (!plan) return null;

        const PHASE_COLORS = [
            { border: '#3b82f6', bg: '#eff6ff', text: '#1d4ed8', badgeBg: '#2563eb', label: 'Phase 1' },
            { border: '#10b981', bg: '#ecfdf5', text: '#047857', badgeBg: '#059669', label: 'Phase 2' },
            { border: '#f59e0b', bg: '#fffbeb', text: '#b45309', badgeBg: '#d97706', label: 'Phase 3' },
            { border: '#8b5cf6', bg: '#f5f3ff', text: '#6d28d9', badgeBg: '#7c3aed', label: 'Phase 4' },
            { border: '#ec4899', bg: '#fdf2f8', text: '#be185d', badgeBg: '#db2777', label: 'Phase 5' },
        ];

        const teethMap = {};
        (plan.phases || []).forEach((ph, pIdx) => {
            if (activeOverlayPhaseId && ph.id !== activeOverlayPhaseId) return;
            const colorConfig = PHASE_COLORS[pIdx % PHASE_COLORS.length];
            (ph.items || []).forEach((item) => {
                const targets = item.work_item?.targets || [];
                targets.forEach((target) => {
                    if (target.tooth_key) {
                        const tk = String(target.tooth_key);
                        if (!teethMap[tk]) {
                            teethMap[tk] = {
                                phaseId: ph.id,
                                phaseOrder: ph.phase_order,
                                phaseName: ph.name,
                                phaseIndex: pIdx,
                                color: colorConfig.badgeBg,
                                borderColor: colorConfig.border,
                                bgColor: colorConfig.bg,
                                badge: `P${pIdx + 1}`,
                                procedureCodes: [item.work_item?.code].filter(Boolean),
                            };
                        } else {
                            if (item.work_item?.code && !teethMap[tk].procedureCodes.includes(item.work_item.code)) {
                                teethMap[tk].procedureCodes.push(item.work_item.code);
                            }
                        }
                    }
                });
            });
        });

        return {
            planId: plan.id,
            planTitle: plan.title,
            phaseId: activeOverlayPhaseId,
            teeth: teethMap,
            phases: (plan.phases || []).map((ph, idx) => ({
                id: ph.id,
                name: ph.name,
                colorConfig: PHASE_COLORS[idx % PHASE_COLORS.length],
            })),
        };
    }, [activeOverlayPlanId, activeOverlayPhaseId, treatmentPlans]);

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
            onToothClick: handleToothClick,
            onSurfaceClick: handleSurfaceClick,
        });
    }, [effectiveSnapshot, id, isPediatric, selectedTeeth, selectedSurfacesByTooth, planOverlay, handleToothClick, handleSurfaceClick]);

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
        activeTab === 'chart' || activeTab === 'history' || activeTab === 'billing' || activeTab === 'timeline'
    );
    const { data: payments = [] } = usePatientPayments(
        id,
        activeTab === 'chart' || activeTab === 'billing' || activeTab === 'timeline'
    );
    const {
        data: attachments = [],
        isLoading: attachmentsLoading,
        refetch: refetchAttachments
    } = usePatientAttachments(id, activeTab === 'files');

    const [isEditPatientOpen, setIsEditPatientOpen] = useState(false);
    const [isRxModalOpen, setIsRxModalOpen] = useState(false);
    const [isTreatmentModalOpen, setIsTreatmentModalOpen] = useState(false);
    const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);

    const getInitialTreatment = () => ({
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
        notes: ''
    });

    const [newTreatment, setNewTreatment] = useState(getInitialTreatment());
    const [editingTreatmentId, setEditingTreatmentId] = useState(null);
    const [selectedToothCondition, setSelectedToothCondition] = useState('Healthy');

    const { mutateAsync: createPaymentMutate } = useCreatePayment();
    const { mutateAsync: deletePaymentMutate } = useDeletePayment();

    const refetchAllTeeth = useCallback(() => {
        refetchTeeth();
        refetchWorkspace?.();
    }, [refetchTeeth, refetchWorkspace]);

    const { handleSaveTreatment } = useTreatmentOperations({
        patientId: id,
        refetchHistory,
        refetchTeeth: refetchAllTeeth,
        refetchWorkspace,
        setIsTreatmentModalOpen,
        setEditingTreatmentId,
        editingTreatmentId,
        selectedToothCondition
    });

    const handleFileUpload = useCallback(async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        try {
            await uploadAttachment(id, file);
            refetchAttachments();
        } catch {
            toast.error(t('patient_details.alerts.upload_fail'));
        }
    }, [id, refetchAttachments, t]);

    const handleDeleteAttachment = useCallback(async (attachmentId) => {
        if (!window.confirm('Delete this file?')) return;
        try {
            await deleteAttachment(attachmentId);
            refetchAttachments();
        } catch {
            // Preserve existing silent attachment-delete failure behavior.
        }
    }, [refetchAttachments]);

    const handleSavePatient = useCallback(async (updatedData) => {
        try {
            await updatePatient(id, updatedData);
            setIsEditPatientOpen(false);
            refetchPatient();
            toast.success(t('patients.update_success'));
        } catch (error) {
            const detail = error.response?.data?.detail;
            const message = typeof detail === 'string'
                ? detail
                : (Array.isArray(detail)
                    ? detail.map((item) => item.msg || item).join(', ')
                    : (error.message || t('common.error')));
            toast.error(`${t('common.error')}: ${message}`);
        }
    }, [id, refetchPatient, t]);

    const handleNewAppointment = useCallback(() => {
        navigate(`/appointments?patient_id=${id}`);
    }, [navigate, id]);

    const handleSavePayment = useCallback(async (data) => {
        try {
            await createPaymentMutate({ ...data, patient_id: parseInt(id, 10) });
            setIsPaymentModalOpen(false);
            toast.success(t('finance.pay_success', 'تم الدفع بنجاح'));
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.payment_save_fail'));
        }
    }, [id, createPaymentMutate, t]);

    const openManualTreatment = useCallback(() => {
        setEditingTreatmentId(null);
        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: '',
            surface: '',
            surfaces: [],
            target_kind: 'tooth',
            default_price_list_id: patient?.default_price_list_id
        });
        setIsTreatmentModalOpen(true);
    }, [patient]);

    const handleEditTreatment = useCallback((item) => {
        setEditingTreatmentId(item.id);
        let canals = [{ name: '', length: '' }];
        try {
            const parsed = item.canal_lengths ? JSON.parse(item.canal_lengths) : null;
            if (Array.isArray(parsed) && parsed.length) canals = parsed;
        } catch {
            // Preserve empty-canal fallback for malformed historical data.
        }

        const initialSurfaces = Array.isArray(item.surfaces)
            ? item.surfaces
            : (item.surface ? item.surface.split('').filter(Boolean) : []);

        setNewTreatment({
            id: item.id,
            patient_id: item.patient_id,
            doctor_id: item.doctor_id,
            date: item.date ? new Date(item.date).toLocaleDateString('en-CA') : getTodayStr(),
            diagnosis: item.diagnosis || '',
            procedure: item.procedure || '',
            cost: item.cost ?? '',
            discount: item.discount ?? '',
            tooth_number: item.tooth_number ? fdiToPalmer(item.tooth_number) : '',
            surface: item.surface || initialSurfaces.join(''),
            surfaces: initialSurfaces,
            target_kind: item.target_kind || (initialSurfaces.length ? 'surface' : 'tooth'),
            canal_count: item.canal_count ?? '',
            canals,
            sessions: item.sessions || '',
            complications: item.complications || '',
            notes: item.notes || '',
            status: item.status || 'Done',
            consumedMaterials: item.consumedMaterials || [],
            default_price_list_id: patient?.default_price_list_id
        });
        setIsTreatmentModalOpen(true);
    }, [patient]);

    const handleDeleteTreatment = useCallback(async (treatmentId) => {
        if (!window.confirm(t('patient_details.alerts.delete_treatment_confirm'))) return;
        try {
            await deleteTreatment(treatmentId);
            await Promise.all([refetchHistory(), refetchWorkspace()]);
            toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.delete_treatment_fail'));
        }
    }, [refetchHistory, refetchWorkspace, t]);

    const handleRemoveWorkItemOrTreatment = useCallback(async (item) => {
        try {
            if (item.sourceType === 'treatment' || (!item.sourceType && item.treatment_id)) {
                await deleteTreatment(item.id);
                await Promise.all([refetchHistory(), refetchWorkspace()]);
                toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
            } else {
                const workItemId = item.id;
                if (workItemId && !String(workItemId).startsWith('ve-')) {
                    await updatePatientClinicalWorkItem(id, workItemId, { status: 'cancelled' });
                }
                await refetchWorkspace();
                toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
            }
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.delete_treatment_fail', 'Failed to remove item'));
        }
    }, [id, refetchHistory, refetchWorkspace, t]);

    const executeClinicalAction = useCallback(async (actionData) => {
        const { item, toothKeys, targetKind, surfaces, defaultPrice } = actionData;
        const primaryTooth = toothKeys?.[0] || resolvedActiveTooth;
        if (!primaryTooth) return false;

        // Flow A: When clinical_vnext_native_writes is enabled, dispatch to G7 endpoints
        if (isNativeWritesEnabled) {
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
                    FRACTURE: 'Fractured',
                    PAIN: 'Decayed',
                };
                const condition = conditionMap[item.code] || 'Decayed';
                await updateToothStatus({
                    patient_id: parseInt(id, 10),
                    tooth_number: fdiNum,
                    condition,
                });
                await Promise.all([refetchTeeth?.(), refetchWorkspace?.()]);
                toast.success(t('patient_details.alerts.treatment_save_success', 'Finding recorded successfully'));
                return true;
            } catch (err) {
                toast.error(t('patient_details.alerts.tooth_update_fail'));
                return false;
            }
        }

        // For procedures: open TreatmentModal pre-populated
        const fdi = Number.parseInt(primaryTooth, 10);
        const palmerPrefix = fdiToPalmer(fdi);
        const surfaceStr = Array.isArray(surfaces) ? surfaces.join('') : (surfaces || '');

        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: palmerPrefix,
            procedure_name: item.name,
            cost: defaultPrice || 0,
            surface: surfaceStr,
            surfaces: Array.isArray(surfaces) ? [...surfaces] : [],
            target_kind: targetKind || (surfaceStr ? 'surface' : 'tooth'),
            default_price_list_id: patient?.default_price_list_id,
        });
        setIsTreatmentModalOpen(true);
        return true;
    }, [id, resolvedActiveTooth, isNativeWritesEnabled, patient, refetchWorkspace, refetchTeeth, refetchHistory, t]);

    executeClinicalActionRef.current = executeClinicalAction;
    const handleQuickLauncherAction = executeClinicalAction;

    const handleDeletePayment = useCallback(async (paymentId) => {
        if (!window.confirm(t('patient_details.alerts.delete_payment_confirm'))) return;
        try {
            await deletePaymentMutate({ paymentId, patientId: parseInt(id, 10) });
            toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.delete_payment_fail'));
        }
    }, [id, deletePaymentMutate, t]);

    const handlePrintInvoice = useCallback(() => {
        navigate(`/print/invoice/${id}`);
    }, [navigate, id]);

    const handlePrintRx = useCallback(async ({ drugs, notes }) => {
        try {
            const payload = {
                patient_id: parseInt(id, 10),
                medications: JSON.stringify(drugs || []),
                notes: notes || ''
            };
            const res = await createPrescription(payload);
            // Print route carries the real prescription id; no PHI in sessionStorage.
            setIsRxModalOpen(false);
            window.open(`/print/rx/${res.data?.id}`, '_blank');
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.rx_fail'));
        }
    }, [id, t]);

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
    }, [activeTab, selectedTeeth]);

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
    }, [activeTab, selectedTeeth]);

    return (
        <div className="min-w-0 space-y-4 pb-8 sm:space-y-6 sm:pb-10">
            {!patientIsError && !patientLoading && patient && (
                <div className="min-w-0 overflow-hidden">
                    <Breadcrumb items={[
                        { label: t('sidebar.patients'), to: '/patients' },
                        { label: patient.name }
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
                                            {!workspaceLoading && !workspaceIsError && (
                                                <span
                                                    data-testid="clinical-workspace-read-mode"
                                                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                                        adaptedChart.readMode === 'VNEXT_PRIMARY'
                                                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                                                            : adaptedChart.readMode === 'SHADOW'
                                                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                                                            : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300'
                                                    }`}
                                                >
                                                    {adaptedChart.readMode}
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
                                    <div className="space-y-2" data-testid="clinical-workspace-status">
                                        <div
                                            data-testid="clinical-workspace-coverage"
                                            className="flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-400"
                                        >
                                            <span className="font-semibold">{t('clinical.coverage', 'Coverage')}:</span>
                                            {Object.entries(adaptedChart.coverage).map(([domain, status]) => (
                                                <span
                                                    key={domain}
                                                    className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${
                                                        status === 'COMPLETE'
                                                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                                                            : status === 'PARTIAL'
                                                            ? 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
                                                            : 'bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
                                                    }`}
                                                >
                                                    <span>{domain}:</span>
                                                    <span className="font-bold">{status}</span>
                                                </span>
                                            ))}
                                        </div>

                                        {adaptedChart.isFallback && (
                                            <div
                                                data-testid="clinical-workspace-fallback-banner"
                                                className="rounded-lg border border-blue-200 bg-blue-50/70 p-2.5 text-xs text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300"
                                            >
                                                <span className="font-semibold">{t('clinical.fallback_notice', 'Notice')}: </span>
                                                {t('clinical.fallback_desc', 'Displaying clinical records with legacy fallback contribution.')}
                                            </div>
                                        )}

                                        {adaptedChart.warnings && adaptedChart.warnings.length > 0 && (
                                            <div
                                                data-testid="clinical-workspace-warnings"
                                                className="rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300"
                                            >
                                                <span className="font-semibold">{t('clinical.warnings', 'Warnings')}: </span>
                                                <ul className="mt-1 list-inside list-disc space-y-0.5">
                                                    {adaptedChart.warnings.map((w, idx) => (
                                                        <li key={idx}>
                                                            <span className="font-medium">[{w.code}]</span> {w.message}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {adaptedChart.isEmpty && (
                                            <div
                                                data-testid="clinical-workspace-empty"
                                                className="rounded-lg border border-slate-200 bg-slate-50/50 p-2 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400"
                                            >
                                                {t('clinical.empty_workspace', 'No clinical events or work items recorded for this patient yet.')}
                                            </div>
                                        )}
                                    </div>
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
                                            {planOverlay && (
                                                <div
                                                    data-testid="plan-overlay-active-banner"
                                                    className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-blue-200 bg-blue-50/80 p-3 shadow-sm dark:border-blue-900/60 dark:bg-blue-950/40"
                                                >
                                                    <div className="flex flex-wrap items-center gap-3">
                                                        <div className="flex items-center gap-2">
                                                            <span className="flex h-2.5 w-2.5 rounded-full bg-blue-600 animate-pulse" />
                                                            <span className="text-xs font-bold text-blue-900 dark:text-blue-200">
                                                                {t('clinical_plans.overlay.active_banner', 'Plan Overlay Active')}:
                                                            </span>
                                                            <span className="text-xs font-extrabold text-blue-700 dark:text-blue-300">
                                                                {planOverlay.planTitle}
                                                                {planOverlay.phaseId && ` (${planOverlay.phases.find((p) => p.id === planOverlay.phaseId)?.name || ''})`}
                                                            </span>
                                                        </div>
                                                        <div className="flex flex-wrap items-center gap-2 border-s border-blue-200 ps-3 dark:border-blue-800">
                                                            {planOverlay.phases.map((ph, idx) => (
                                                                <span
                                                                    key={ph.id}
                                                                    className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold"
                                                                    style={{
                                                                        backgroundColor: ph.colorConfig.bg,
                                                                        color: ph.colorConfig.text,
                                                                        border: `1px solid ${ph.colorConfig.border}`,
                                                                    }}
                                                                >
                                                                    <span
                                                                        className="inline-block h-1.5 w-1.5 rounded-full"
                                                                        style={{ backgroundColor: ph.colorConfig.badgeBg }}
                                                                    />
                                                                    {ph.name} (P{idx + 1})
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        onClick={() => handleTogglePlanOverlay(planOverlay.planId, planOverlay.phaseId)}
                                                        className="inline-flex min-h-11 items-center justify-center rounded-xl border border-blue-300 bg-white px-3 py-1.5 text-xs font-bold text-blue-700 hover:bg-blue-50 dark:border-blue-800 dark:bg-slate-900 dark:text-blue-300 dark:hover:bg-slate-800"
                                                        data-testid="clear-plan-overlay-button"
                                                    >
                                                        {t('clinical_plans.overlay.clear_overlay', 'Clear Overlay')}
                                                    </button>
                                                </div>
                                            )}
                                            <ClinicalChartRenderer input={adaptedChart.rendererInput} />
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
                                                    onClose={() => setIsQuickLauncherOpen(false)}
                                                />
                                            </div>
                                        )}
                                        {selectedTeeth.length > 0 && (
                                            <div
                                                data-testid="chairside-selection-bar"
                                                className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                                            >
                                                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        <span className="text-sm font-bold text-slate-700 dark:text-slate-300">
                                                            {t('patient_details.chart.selected_teeth', 'Selected Teeth')}:
                                                        </span>
                                                        <div className="flex flex-wrap items-center gap-1.5" data-testid="selected-teeth-badges">
                                                            {selectedTeeth.map((toothKey) => {
                                                                const fdi = Number.parseInt(toothKey, 10);
                                                                const palmer = fdiToPalmer(fdi);
                                                                const isActive = toothKey === resolvedActiveTooth;
                                                                return (
                                                                    <button
                                                                        key={toothKey}
                                                                        type="button"
                                                                        onClick={() => setActiveToothKey(toothKey)}
                                                                        className={`inline-flex min-h-11 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                                                                            isActive
                                                                                ? 'bg-blue-600 text-white shadow-sm ring-2 ring-blue-500 ring-offset-1'
                                                                                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                                                                        }`}
                                                                        data-testid={`selected-tooth-badge-${toothKey}`}
                                                                    >
                                                                        <span>{toothKey} ({palmer})</span>
                                                                        {isMultiSelectMode && (
                                                                            <span
                                                                                role="button"
                                                                                tabIndex={0}
                                                                                onClick={(e) => {
                                                                                    e.stopPropagation();
                                                                                    handleRemoveToothFromSelection(toothKey);
                                                                                }}
                                                                                onKeyDown={(e) => {
                                                                                    if (e.key === 'Enter' || e.key === ' ') {
                                                                                        e.stopPropagation();
                                                                                        handleRemoveToothFromSelection(toothKey);
                                                                                    }
                                                                                }}
                                                                                aria-label={`Remove tooth ${toothKey}`}
                                                                                className="inline-flex h-4 w-4 items-center justify-center rounded-full text-xs hover:bg-black/20"
                                                                            >
                                                                                ×
                                                                            </span>
                                                                        )}
                                                                    </button>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            type="button"
                                                            onClick={handleClearSelection}
                                                            className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                                                            data-testid="clear-selection-button"
                                                        >
                                                            {t('patient_details.chart.clear_selection', 'Clear Selection')}
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={handleRecordTreatmentFromSelection}
                                                            className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                                            data-testid="record-treatment-button"
                                                            title={t('patient_details.chart.advanced_entry_tooltip', 'Open classic treatment entry modal')}
                                                        >
                                                            {t('patient_details.chart.advanced_entry', 'Advanced Entry')}
                                                        </button>
                                                    </div>
                                                </div>

                                                {resolvedActiveTooth && (
                                                    <div className="flex flex-wrap items-center gap-2 pt-1" data-testid="surface-pill-bar">
                                                        <span className="me-1 text-xs font-bold text-slate-500 dark:text-slate-400">
                                                            {t('patient_details.chart.surfaces', 'Surfaces')} ({resolvedActiveTooth}):
                                                        </span>
                                                        {['M', 'D', 'O', 'I', 'B', 'L', 'P'].map((code) => {
                                                            const isSelected = activeSurfaces.includes(code);
                                                            return (
                                                                <button
                                                                    key={code}
                                                                    type="button"
                                                                    onClick={() => handleToggleSurface(code)}
                                                                    aria-pressed={isSelected}
                                                                    data-testid={`surface-pill-${code}`}
                                                                    className={`min-h-11 rounded-xl border px-3 py-1.5 text-xs font-bold transition-all ${
                                                                        isSelected
                                                                            ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                                                                            : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                                                                    }`}
                                                                >
                                                                    {code}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                )}

                                                <ChartQuickActionLauncher
                                                    selectedTeeth={selectedTeeth}
                                                    selectedSurfacesByTooth={selectedSurfacesByTooth}
                                                    onAction={handleQuickLauncherAction}
                                                    onActivateStickyTool={(tool) => {
                                                        setActiveStickyTool(tool);
                                                        setStickyAppliedCount(0);
                                                    }}
                                                    clinicProcedures={procedures}
                                                    onClose={handleClearSelection}
                                                />

                                                <ClinicalChartInspector
                                                    copy={CLINICAL_CHART_COPY[i18n?.language?.startsWith('ar') ? 'ar' : 'en'] || CLINICAL_CHART_COPY.en}
                                                    title={t('patient_details.chart.title')}
                                                    selection={{
                                                        toothKey: resolvedActiveTooth,
                                                        surfaceCode: activeSurfaces[0] || null,
                                                        surfaceCodes: activeSurfaces,
                                                    }}
                                                    toothState={adaptedChart.projection?.teeth?.[resolvedActiveTooth]}
                                                    workItems={workspaceSnapshot?.work_items || []}
                                                    treatments={history || []}
                                                    treatmentPlans={treatmentPlans || []}
                                                    payments={payments || []}
                                                    onRemoveItem={handleRemoveWorkItemOrTreatment}
                                                />
                                            </div>
                                        )}
                                    </>
                                )}

                                {isTreatmentPlansEnabled && (
                                    <TreatmentPlansCard
                                        patientId={id}
                                        activeOverlayPlanId={activeOverlayPlanId}
                                        activeOverlayPhaseId={activeOverlayPhaseId}
                                        onToggleOverlay={handleTogglePlanOverlay}
                                    />
                                )}
                            </div>
                        )}


                        {activeTab === 'timeline' && <PatientTimeline history={history} payments={payments} t={t} />}

                        {activeTab === 'history' && (
                            <TreatmentHistory
                                history={history}
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
                            />
                        )}

                        {activeTab === 'labs' && <LabOrdersTab patientId={id} />}
                    </Suspense>
                </div>
            </section>

            <EditPatientModal
                isOpen={isEditPatientOpen}
                onClose={() => setIsEditPatientOpen(false)}
                onSave={handleSavePatient}
                initialData={patient}
            />

            <TreatmentModal
                isOpen={isTreatmentModalOpen}
                onClose={() => setIsTreatmentModalOpen(false)}
                onSave={handleSaveTreatment}
                initialData={newTreatment}
                isEditing={!!editingTreatmentId}
                procedures={procedures}
                selectedToothCondition={selectedToothCondition}
                setSelectedToothCondition={setSelectedToothCondition}
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
                                    default_price_list_id: patient?.default_price_list_id
                                });
                                setIsTreatmentModalOpen(true);
                                setIsToothSelectModalOpen(false);
                            }}
                            className="min-h-11 w-full rounded-xl bg-slate-100 px-4 py-2.5 font-bold text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                        >
                            {t('patient_details.chart.continue_no_tooth')}
                        </button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
