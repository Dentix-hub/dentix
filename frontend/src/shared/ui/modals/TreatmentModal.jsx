import { useState, useEffect, useRef, useMemo } from 'react';
import { Package, Plus, Trash2, Droplets, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getMaterials, getStockSummary, getActiveSessions } from '@/api/inventory';
import TrackSessionModal from '@/features/inventory/components/TrackSessionModal';
import { EnhancedMaterialConsumption } from '@/features/inventory/components/EnhancedMaterialConsumption';
import MaterialConsumptionPanel from '@/features/inventory/MaterialConsumptionPanel';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { addTreatmentSession } from '@/api';
import { MultiSessionPanel } from '../components/MultiSessionPanel';
import Modal from '@/shared/ui/Modal';
import logger from '@/utils/logger';
import { resolveProcedureSelection } from '@/features/patients/utils/resolveProcedureSelection';
import { buildTreatmentPayload } from '@/features/patients/utils/buildTreatmentPayload';
import { palmerToFdi, fdiToPalmer } from '@/utils/toothUtils';

const CLINICAL_SURFACES = [
    { code: 'M', label: 'M', description: 'Mesial (أنسي)' },
    { code: 'O', label: 'O', description: 'Occlusal (إطباقي)' },
    { code: 'D', label: 'D', description: 'Distal (وحشي)' },
    { code: 'B', label: 'B', description: 'Buccal (دهليزي)' },
    { code: 'L', label: 'L', description: 'Lingual (لساني)' },
    { code: 'I', label: 'I', description: 'Incisal (قاطع)' },
    { code: 'P', label: 'P', description: 'Palatal (حنكي)' },
];

const normalizeTreatmentData = (data) => {
    if (!data) return data;
    const rawSurfaces = Array.isArray(data.surfaces)
        ? data.surfaces
        : (data.surface ? String(data.surface).replace(/[^A-Za-z]/g, '').toUpperCase().split('') : []);
    return {
        ...data,
        surface: data.surface || rawSurfaces.join(''),
        surfaces: rawSurfaces,
        target_kind: data.target_kind || (rawSurfaces.length > 0 ? 'surface' : 'tooth'),
    };
};

const getClinicalLinkErrorMessage = (errorCode, t) => {
    switch (errorCode) {
        case 'CLINICAL_LINK_UNAVAILABLE':
            return t('clinical_plans.errors.link_unavailable', 'Clinical shadow mode is not active.');
        case 'CLINICAL_LINK_NOT_OPEN':
            return t('clinical_plans.errors.link_not_open', 'This planned item is already completed or closed.');
        case 'CLINICAL_LINK_CODE_MISMATCH':
            return t('clinical_plans.errors.link_code_mismatch', 'Selected procedure code does not match the planned item.');
        case 'CLINICAL_LINK_TARGET_MISMATCH':
            return t('clinical_plans.errors.link_target_mismatch', 'Selected tooth or surfaces do not match the planned item.');
        case 'CLINICAL_LINK_ALREADY_LINKED':
            return t('clinical_plans.errors.link_already_linked', 'This plan item has already been performed and linked.');
        case 'CLINICAL_LINK_CONFLICT':
            return t('clinical_plans.errors.link_conflict', 'A concurrent update occurred. Please refresh.');
        default:
            return errorCode;
    }
};

export default function TreatmentModal({
    isOpen,
    onClose,
    onSave,
    initialData,
    isEditing = false,
    procedures = [],
    selectedToothCondition,
    setSelectedToothCondition,
    selectedTeeth = [],
    selectedSurfacesByTooth = {},
    onSelectionChange,
}) {
    const { t } = useTranslation();
    const [treatment, setTreatment] = useState(() => normalizeTreatmentData(initialData) || initialData);
    const [isSaving, setIsSaving] = useState(false);
    const isSavingRef = useRef(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [isManualProcedure, setIsManualProcedure] = useState(false);
    const [linkError, setLinkError] = useState(null);
    const [explicitToothCondition, setExplicitToothCondition] = useState(null);
    const safeProcedures = useMemo(() => (Array.isArray(procedures) ? procedures : []), [procedures]);

    const displayProcedures = useMemo(() => {
        if (treatment?.prefill_source === 'plan_item' && treatment?.work_item_code) {
            const matching = safeProcedures.filter(
                (p) => p.canonical_code === treatment.work_item_code
            );
            if (matching.length > 0) return matching;
        }
        return safeProcedures;
    }, [safeProcedures, treatment?.prefill_source, treatment?.work_item_code]);
    // Modal Tabs
    const [toothModalTab, setToothModalTab] = useState('Status');
    const [selectedPathologies, setSelectedPathologies] = useState([]);
    const [selectedRestorations, setSelectedRestorations] = useState([]);
    // Inventory State
    const [availableMaterials, setAvailableMaterials] = useState([]);
    const [isMaterialsLoading, setIsMaterialsLoading] = useState(false);
    const [consumedMaterials, setConsumedMaterials] = useState([]); // [{ material_id, quantity }]
    const [, setShowInventory] = useState(false);
    const [isSmartConsumptionOpen, setIsSmartConsumptionOpen] = useState(false);
    const [smartConsumptionMode, setSmartConsumptionMode] = useState('smart');
    // Fetch Active Sessions to show status
    const { refetch: refetchSessions } = useQuery({
        queryKey: ['active-sessions'],
        queryFn: getActiveSessions,
        enabled: isOpen
    });
    // Session Tracking State
    const [isTrackSessionOpen, setIsTrackSessionOpen] = useState(false);
    const [trackSessionMode, setTrackSessionMode] = useState('OPEN');
    const [trackSessionMaterial, setTrackSessionMaterial] = useState(null);
    const [trackSessionStockItem, setTrackSessionStockItem] = useState(null);
    const [trackSessionData] = useState(null);
    // Fetch Materials on Mount
    useEffect(() => {
        if (isOpen) {
            logger.debug('[MATERIALS_DEBUG] TreatmentModal opened, fetching stock summary...');
            setIsMaterialsLoading(true);
            getStockSummary().then(res => {
                logger.debug('[MATERIALS_DEBUG] getStockSummary raw response:', JSON.stringify(res.data).substring(0, 500));
                const materialsList = res.data?.data || res.data || [];
                logger.debug('[MATERIALS_DEBUG] Parsed materialsList:', materialsList?.length, 'items', Array.isArray(materialsList));
                
                setAvailableMaterials(Array.isArray(materialsList) ? materialsList : []);
            }).catch(err => {
                logger.error("[MATERIALS_DEBUG] getStockSummary FAILED:", err?.response?.status, err?.response?.data || err.message);
                getMaterials().then(res => {
                    const list = res.data?.data || res.data || [];
                    setAvailableMaterials(Array.isArray(list) ? list : []);
                }).catch(err2 => {
                    logger.error("[MATERIALS_DEBUG] getMaterials ALSO FAILED:", err2?.response?.status);
                });
            }).finally(() => {
                setIsMaterialsLoading(false);
            });
        }
    }, [isOpen]);
    useEffect(() => {
        if (isOpen) {
            setLinkError(null);
            const normalized = normalizeTreatmentData(initialData);
            setTreatment(normalized);
            setIsManualProcedure(false);

            const prefillSource = normalized?.prefill_source;
            const preserveEscalatedEdits = Boolean(normalized?.escalated_from_quick_sheet);
            const escalationErr = normalized?.escalation_error;

            if (!preserveEscalatedEdits && (prefillSource === 'quick_launcher' || prefillSource === 'plan_item')) {
                const procName = normalized?.procedure;
                if (procName) {
                    resolveProcedureSelection({
                        procedureName: procName,
                        procedures: safeProcedures,
                        defaultPriceListId: normalized?.default_price_list_id,
                        currentPriceListId: normalized?.price_list_id,
                    }).then(({ found, cost, price_list_id, autoMaterials }) => {
                        if (!found) {
                            setIsManualProcedure(true);
                            setTreatment(prev => ({
                                ...prev,
                                procedure: procName,
                                cost: prev?.cost ?? '',
                                price_list_id: null,
                            }));
                        } else {
                            setTreatment(prev => ({
                                ...prev,
                                procedure: procName,
                                cost,
                                price_list_id,
                            }));
                            if (autoMaterials.length > 0) {
                                logger.debug("[MATERIALS_DEBUG] Auto-loaded materials (BOM):", autoMaterials);
                                setConsumedMaterials(autoMaterials);
                                setShowInventory(true);
                            }
                        }
                    });
                }
            }

            // FIX: Always reset consumed materials when opening modal to prevent stale data
            if ((isEditing || preserveEscalatedEdits) && initialData?.consumedMaterials && initialData.consumedMaterials.length > 0) {
                logger.debug("[TreatmentModal] Loading existing materials:", initialData.consumedMaterials);
                setConsumedMaterials(initialData.consumedMaterials);
                setShowInventory(true);
            } else if (!prefillSource || preserveEscalatedEdits) {
                // Reset for new entry or if no materials exist
                setConsumedMaterials([]);
                setShowInventory(false);
            }
            // Reset tabs logic when opening new (or editing if needed, but usually keep existing)
            if (!isEditing) {
                setToothModalTab('Status');
                setSelectedPathologies([]);
                setSelectedRestorations([]);
                setExplicitToothCondition(null);
            }

            if (escalationErr) {
                setTimeout(() => {
                    handleSaveError(escalationErr, false);
                }, 0);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, initialData, isEditing, safeProcedures]);
    const queryClient = useQueryClient();

    const addSessionMutation = useMutation({
        mutationFn: (data) => addTreatmentSession(treatment.id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['patient-details', treatment.patient_id] });
            // Also update local state to show the new session without a full refetch if possible
            setTreatment(prev => ({
                ...prev,
                treatment_sessions: [...(prev.treatment_sessions || []), { 
                    ...prev.last_added_session, // mock or wait for refresh
                    created_at: new Date().toISOString() 
                }]
            }));
        }
    });

    const handleAddSession = async (sessionData) => {
        try {
            await addSessionMutation.mutateAsync({
                ...sessionData,
                treatment_id: treatment.id,
                tenant_id: treatment.tenant_id
            });
            return true;
        } catch (error) {
            logger.error("Failed to add session:", error);
            return false;
        }
    };
    if (!isOpen) return null;

    const getConfirmOpenDetail = (error) => {
        const data = error.response?.data;
        const candidates = [
            data?.error?.details,
            typeof data?.detail === 'object' ? data.detail : null,
            data?.details,
            data?.data,
            data
        ];
        const structured = candidates.find(item => item?.code === 'CONFIRM_OPEN_REQUIRED');
        if (structured) return structured;

        const message = [
            typeof data?.detail === 'string' ? data.detail : '',
            data?.error?.message,
            data?.message
        ].find(value => typeof value === 'string' && value.includes('CONFIRM_OPEN_REQUIRED'));

        if (!message) return null;

        const [, rest = ''] = message.split('CONFIRM_OPEN_REQUIRED:');
        const [stockId, ...nameParts] = rest.split(':');
        return {
            code: 'CONFIRM_OPEN_REQUIRED',
            stock_item_id: parseInt(stockId, 10),
            material_info: nameParts.join(':') || 'Material'
        };
    };

    const openTrackSessionForConflict = (detail) => {
        const stockItemId = Number(detail.stock_item_id || detail.stockItemId || detail.stock_item?.id);
        const materialName = detail.material_info || detail.material_name || detail.message || 'Material';

        setTrackSessionMode('OPEN');
        setTrackSessionMaterial({
            id: detail.material_id,
            name: materialName,
            material_name: materialName
        });
        setTrackSessionStockItem(stockItemId ? {
            id: stockItemId,
            name: materialName,
            material_name: materialName
        } : null);
        setIsTrackSessionOpen(true);
    };

    const toggleSurface = (code) => {
        const currentSurfaces = Array.isArray(treatment?.surfaces) ? [...treatment.surfaces] : [];
        const exists = currentSurfaces.includes(code);
        const updated = exists ? currentSurfaces.filter(s => s !== code) : [...currentSurfaces, code];
        const order = ['M', 'O', 'I', 'D', 'B', 'L', 'P'];
        updated.sort((a, b) => order.indexOf(a) - order.indexOf(b));
        const surfaceStr = updated.join('');
        setTreatment(prev => ({
            ...prev,
            surfaces: updated,
            surface: surfaceStr,
            target_kind: updated.length > 0 ? 'surface' : 'tooth',
        }));
    };

    const handleSurfaceInputChange = (value) => {
        const clean = value.replace(/[^A-Za-z]/g, '').toUpperCase();
        const letters = clean.split('').filter((c, i, arr) => arr.indexOf(c) === i);
        setTreatment(prev => ({
            ...prev,
            surface: clean,
            surfaces: letters,
            target_kind: letters.length > 0 ? 'surface' : 'tooth',
        }));
    };

    function handleSaveError(error, forceSkipStock = false) {
        logger.error('[TREATMENT] Save Error Details:', {
            status: error.response?.status,
            data: error.response?.data,
            message: error.message
        });

        const confirmOpenDetail = getConfirmOpenDetail(error);
        if (confirmOpenDetail) {
            openTrackSessionForConflict(confirmOpenDetail);
            return;
        }

        const responseData = error.response?.data;
        const errDetail = responseData?.detail;

        // Case: Clinical plan item linking error (U2.3)
        const clinicalLinkCode = (
            (typeof errDetail === 'string' && errDetail.startsWith('CLINICAL_LINK_') ? errDetail : null) ||
            (typeof errDetail?.code === 'string' && errDetail.code.startsWith('CLINICAL_LINK_') ? errDetail.code : null) ||
            (typeof responseData?.code === 'string' && responseData.code.startsWith('CLINICAL_LINK_') ? responseData.code : null) ||
            (typeof responseData?.message === 'string' && responseData.message.startsWith('CLINICAL_LINK_') ? responseData.message : null) ||
            (typeof error?.message === 'string' && error.message.includes('CLINICAL_LINK_') ? error.message : null)
        );

        if (clinicalLinkCode) {
            const linkErrorMsg = getClinicalLinkErrorMessage(clinicalLinkCode, t);
            setLinkError(linkErrorMsg);
            toast.error(linkErrorMsg);
            return;
        }

        // Case: Stock validation failure (400 with stock-related message)
        const isStockError = error.response?.status === 400 && (
            (typeof errDetail === 'string' && (errDetail.includes('مخزون') || errDetail.includes('stock') || errDetail.includes('Insufficient'))) ||
            (typeof responseData?.message === 'string' && responseData.message.includes('مخزون'))
        );

        if (isStockError && !forceSkipStock) {
            // Show rich toast with retry option
            toast((t) => (
                <div className="flex flex-col gap-2 max-w-xs" dir="rtl">
                    <div className="flex items-center gap-2 text-red-700 font-bold text-sm">
                        <span>⚠️</span>
                        <span>نقص في المخزون</span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                        {typeof errDetail === 'string' ? errDetail : 'بعض المواد غير متوفرة في المخزن حالياً.'}
                    </p>
                    <div className="flex gap-2 pt-1 border-t border-slate-100">
                        <button
                            onClick={() => {
                                toast.dismiss(t.id);
                                handleSave(null, true);
                            }}
                            className="flex-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-bold transition-colors"
                        >
                            حفظ بدون خصم مخزون
                        </button>
                        <button
                            onClick={() => toast.dismiss(t.id)}
                            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-bold transition-colors"
                        >
                            إلغاء
                        </button>
                    </div>
                </div>
            ), { duration: 15000 });
            return;
        }

        // Case: Generic Error (other 400 or 500)
        const errorEnvelope = responseData?.error;
        const friendlyMsg = typeof errDetail === 'string' ? errDetail : 
                           (errDetail?.message || errorEnvelope?.message || error.message || 'فشل حفظ العلاج');
        
        if (!error.alreadyNotified) {
            toast.error(friendlyMsg);
        }
    }

    const handleSave = async (e, forceSkipStock = false) => {
        if (e) e.preventDefault();
        if (isSavingRef.current) return;

        // Cap at 32 teeth (full adult dentition)
        const rawTeeth = (Array.isArray(selectedTeeth) && selectedTeeth.length > 0)
            ? selectedTeeth
            : (Array.isArray(treatment?.selectedTeeth) && treatment.selectedTeeth.length > 0)
                ? treatment.selectedTeeth
                : (Array.isArray(initialData?.selectedTeeth) && initialData.selectedTeeth.length > 0)
                    ? initialData.selectedTeeth
                    : (treatment?.tooth_number ? [treatment.tooth_number] : []);

        const effectiveTeeth = rawTeeth.slice(0, 32);
        const isMulti = !isEditing && effectiveTeeth.length > 1;

        if (isMulti) {
            const procedureRequiresSurfaces = treatment?.target_kind === 'surface';
            if (procedureRequiresSurfaces) {
                const invalidTeeth = effectiveTeeth.filter((t) => {
                    const strKey = String(t);
                    const fdi = palmerToFdi(t) || t;
                    const strFdi = fdi != null ? String(fdi) : null;
                    const surfs = (selectedSurfacesByTooth && (selectedSurfacesByTooth[strKey] || (strFdi && selectedSurfacesByTooth[strFdi]))) ||
                                  (treatment?.selectedSurfacesByTooth && (treatment.selectedSurfacesByTooth[strKey] || (strFdi && treatment.selectedSurfacesByTooth[strFdi]))) ||
                                  [];
                    return surfs.length === 0;
                });
                if (invalidTeeth.length > 0) {
                    const displayTeeth = invalidTeeth.map((t) => palmerToFdi(t) || t).join(', ');
                    toast.error(
                        t(
                            'quick_treatment_sheet.errors.surfaces_required_for_teeth',
                            'يرجى تحديد أسطح للأسنان التالية: {{teeth}}',
                            { teeth: displayTeeth }
                        )
                    );
                    return;
                }
            }

            isSavingRef.current = true;
            setIsSaving(true);

            let failedIndex = -1;
            let lastError = null;

            for (let i = 0; i < effectiveTeeth.length; i++) {
                const toothKey = effectiveTeeth[i];
                const strKey = String(toothKey);
                const toothFdi = palmerToFdi(toothKey) || toothKey;
                const strFdi = toothFdi != null ? String(toothFdi) : null;
                const toothSurfaces = (selectedSurfacesByTooth && (selectedSurfacesByTooth[strKey] || (strFdi && selectedSurfacesByTooth[strFdi]))) ||
                                      (treatment?.selectedSurfacesByTooth && (treatment.selectedSurfacesByTooth[strKey] || (strFdi && treatment.selectedSurfacesByTooth[strFdi]))) ||
                                      [];
                const toothPalmer = fdiToPalmer(toothFdi) || String(toothKey);
                const targetKind = toothSurfaces.length > 0 ? 'surface' : (treatment?.target_kind || 'tooth');

                const singleTreatment = {
                    ...(treatment || {}),
                    tooth_number: toothPalmer,
                    surfaces: toothSurfaces,
                    surface: toothSurfaces.join(''),
                    target_kind: targetKind,
                };
                delete singleTreatment.escalated_from_quick_sheet;
                delete singleTreatment.escalation_error;

                const singlePayload = buildTreatmentPayload(singleTreatment, {
                    consumedMaterials,
                    procedures: safeProcedures,
                    isEditing: false,
                    forceSkipStock,
                });

                try {
                    await onSave(singlePayload);
                } catch (error) {
                    failedIndex = i;
                    lastError = error;
                    break;
                }
            }

            try {
                if (failedIndex !== -1) {
                    const remainingTeeth = effectiveTeeth.slice(failedIndex);
                    onSelectionChange?.(remainingTeeth);
                    handleSaveError(lastError, forceSkipStock);
                } else {
                    onSelectionChange?.([]);
                    onClose?.();
                }
            } finally {
                isSavingRef.current = false;
                setIsSaving(false);
            }
            return;
        }

        isSavingRef.current = true;
        setIsSaving(true);
        
        const cleanTreatment = { ...(treatment || {}) };
        delete cleanTreatment.escalated_from_quick_sheet;
        delete cleanTreatment.escalation_error;
        if (explicitToothCondition) {
            cleanTreatment.explicit_tooth_condition = explicitToothCondition;
        }

        const payload = buildTreatmentPayload(cleanTreatment, {
            consumedMaterials,
            procedures: safeProcedures,
            isEditing,
            forceSkipStock,
        });

        logger.debug('[TREATMENT] Saving with payload:', payload);

        try {
            setLinkError(null);
            await onSave(payload);
        } catch (error) {
            handleSaveError(error, forceSkipStock);
        } finally {
            isSavingRef.current = false;
            setIsSaving(false);
        }
    };

    const dialogTitle = isEditing
        ? 'تعديل بيانات العلاج'
        : (treatment.tooth_number ? `تفاصيل السن رقم #${treatment.tooth_number}` : 'تسجيل علاج جديد');

    return (
        <>
            <Modal
                isOpen={isOpen}
                onClose={onClose}
                size="3xl"
                title={dialogTitle}
                closeLabel="إغلاق نافذة العلاج"
            >
                <div className="space-y-4">
                    {/* Clinical link error banner */}
                    {linkError && (
                        <div
                            data-testid="clinical-link-error-banner"
                            className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
                        >
                            <AlertCircle size={16} className="shrink-0 text-red-600 dark:text-red-400" />
                            <span>{linkError}</span>
                        </div>
                    )}

                    {/* Plan Item Chip when linking from treatment plan */}
                    {Boolean(treatment.clinical_work_item_id) && (
                        <div
                            data-testid="clinical-link-item-chip"
                            className="flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50/70 p-2.5 text-xs text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/40 dark:text-blue-300"
                        >
                            <div className="flex items-center gap-2">
                                <span className="rounded-md bg-blue-600 px-2 py-0.5 text-[10px] font-bold text-white uppercase">
                                    {t('clinical_plans.linked_plan_item', 'Plan Item')}
                                </span>
                                <span className="font-semibold">
                                    {treatment.plan_title ? `${treatment.plan_title} — ` : ''}
                                    {treatment.procedure || treatment.work_item_code || `#${treatment.clinical_work_item_id}`}
                                </span>
                                {treatment.tooth_number && (
                                    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[11px] font-medium text-blue-700 dark:bg-blue-900/60 dark:text-blue-200">
                                        #{treatment.tooth_number} {treatment.surface ? `(${treatment.surface})` : ''}
                                    </span>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Modal Context Header for chart-driven opens (U3.3) */}
                    {Boolean(treatment.prefill_source && !treatment.clinical_work_item_id) && (
                        <div
                            data-testid="treatment-modal-context-banner"
                            className="flex items-center justify-between rounded-xl border border-slate-200/80 bg-slate-50/80 p-2.5 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-300"
                        >
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="rounded-md bg-slate-200 px-2 py-0.5 text-[10px] font-bold text-slate-700 uppercase dark:bg-slate-800 dark:text-slate-200">
                                    {t(`treatment_modal.prefill_source.${treatment.prefill_source}`, treatment.prefill_source)}
                                </span>
                                {treatment.procedure && (
                                    <span className="font-semibold text-text-primary">
                                        {treatment.procedure}
                                    </span>
                                )}
                                {treatment.tooth_number && (
                                    <span className="rounded bg-slate-200/70 px-1.5 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                                        #{treatment.tooth_number} {treatment.surface ? `(${treatment.surface})` : ''}
                                    </span>
                                )}
                            </div>
                        </div>
                    )}

                    {treatment.tooth_number && (
                        <div className="bg-surface rounded-2xl border border-border p-4 shadow-low mb-4">
                            {/* Segmented Control */}
                            <div className="flex p-1 bg-surface-subtle rounded-xl mb-6 relative">
                                {['Status', 'Pathology', 'Restorations'].map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setToothModalTab(tab)}
                                        className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all duration-300 relative z-10 ${toothModalTab === tab ? 'bg-surface text-text-primary shadow-low scale-100' : 'text-text-muted hover:text-text-secondary'}`}
                                    >
                                        {tab === 'Status' && 'العامة'}
                                        {tab === 'Pathology' && 'الأمراض'}
                                        {tab === 'Restorations' && 'التركيبات'}
                                    </button>
                                ))}
                            </div>
                            {/* Tab Content */}
                            <div className="min-h-[100px]">
                                {/* Tab 1: Status (Single Select) */}
                                {toothModalTab === 'Status' && (
                                    <div className="animate-in fade-in zoom-in-95 duration-200">
                                        <div className="flex flex-wrap gap-2">
                                            {['Healthy', 'Missing', 'Impacted', 'Unerupted', 'Retained Root'].map(status => (
                                                <button
                                                    key={status}
                                                    onClick={() => {
                                                        setExplicitToothCondition(status);
                                                        setSelectedToothCondition(status);
                                                        // Auto-fill logic
                                                        const foundProc = safeProcedures.find(p => p.name.toLowerCase() === status.toLowerCase());
                                                        setTreatment(prev => ({
                                                            ...prev,
                                                            diagnosis: status,
                                                            procedure: foundProc ? foundProc.name : prev.procedure,
                                                            cost: foundProc ? foundProc.price : prev.cost
                                                        }));
                                                    }}
                                                    className={`px-4 py-2 rounded-full text-sm font-bold transition-all border ${selectedToothCondition === status
                                                        ? 'bg-slate-800 text-white border-slate-800 shadow-md transform scale-105'
                                                        : 'bg-surface text-text-secondary border-border hover:bg-surface-subtle'
                                                        }`}
                                                >
                                                    {status}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {/* Tab 2: Pathology (Multi Select) */}
                                {toothModalTab === 'Pathology' && (
                                    <div className="animate-in fade-in zoom-in-95 duration-200">
                                        <div className="flex flex-wrap gap-2">
                                            {['Decayed', 'Fractured', 'Abscess', 'Mobility', 'Pain'].map(item => {
                                                const isSelected = selectedPathologies.includes(item);
                                                return (
                                                    <button
                                                        key={item}
                                                        onClick={() => {
                                                            const newSel = isSelected
                                                                ? selectedPathologies.filter(i => i !== item)
                                                                : [...selectedPathologies, item];
                                                            setSelectedPathologies(newSel);
                                                            // Update diagnosis with all selected
                                                            const diagnosis = [...newSel, ...selectedRestorations].join(', ');
                                                            setTreatment(prev => ({ ...prev, diagnosis: diagnosis || prev.diagnosis }));
                                                            // If Decayed is selected, update chart color
                                                            if (!isSelected && item === 'Decayed') setSelectedToothCondition('Decayed');
                                                        }}
                                                        className={`px-4 py-2 rounded-full text-sm font-bold transition-all border ${isSelected
                                                            ? 'bg-red-50 text-red-600 border-red-200 shadow-sm ring-1 ring-red-100'
                                                            : 'bg-surface text-text-secondary border-border hover:border-red-200 hover:text-red-500'
                                                            }`}
                                                    >
                                                        {item}
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )}
                                {/* Tab 3: Restorations (Multi Select) */}
                                {toothModalTab === 'Restorations' && (
                                    <div className="animate-in fade-in zoom-in-95 duration-200">
                                        <div className="flex flex-wrap gap-2">
                                            {['Filled', 'Root Canal', 'Crown', 'Bridge', 'Implant'].map(item => {
                                                const isSelected = selectedRestorations.includes(item);
                                                return (
                                                    <button
                                                        key={item}
                                                        onClick={() => {
                                                            const newSel = isSelected
                                                                ? selectedRestorations.filter(i => i !== item)
                                                                : [...selectedRestorations, item];
                                                            setSelectedRestorations(newSel);
                                                            const diagnosis = [...selectedPathologies, ...newSel].join(', ');
                                                            setTreatment(prev => ({ ...prev, diagnosis: diagnosis || prev.diagnosis }));
                                                            const chartMap = { 'Filled': 'Filled', 'Root Canal': 'RootCanal', 'Crown': 'Crown', 'Bridge': 'Crown', 'Implant': 'Crown' };
                                                            if (!isSelected && chartMap[item]) {
                                                                setSelectedToothCondition(chartMap[item]);
                                                            }
                                                        }}
                                                        className={`px-4 py-2 rounded-full text-sm font-bold transition-all border ${isSelected
                                                            ? 'bg-blue-50 text-blue-600 border-blue-200 shadow-sm ring-1 ring-blue-100'
                                                            : 'bg-surface text-text-secondary border-border hover:border-blue-200 hover:text-blue-500'
                                                            }`}
                                                    >
                                                        {item}
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    <div>
                        <label htmlFor="treatment-diagnosis" className="mb-1 block text-xs font-bold text-text-muted">التشخيص</label>
                        <input
                            id="treatment-diagnosis"
                            value={treatment.diagnosis}
                            onChange={e => setTreatment({ ...treatment, diagnosis: e.target.value })}
                            placeholder="التشخيص"
                            className="w-full rounded-control border border-border bg-surface-subtle p-3 text-text-primary outline-none focus-visible:ring-focus"
                        />
                    </div>

                    {/* Procedure Selection & Price Calculation */}
                    <div className="bg-surface-subtle p-4 rounded-xl space-y-4">
                        {/* Price List Selection (Optional Override) */}
                        <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                            <span>قائمة الأسعار:</span>
                            {/* In a real app, this could be a dropdown. For now, we just show the active one or allow toggle if needed */}
                        </div>
                        {isManualProcedure ? (
                            <div className="flex gap-2 animate-in fade-in zoom-in-95 duration-200">
                                <input
                                    value={treatment.procedure}
                                    onChange={e => setTreatment({ ...treatment, procedure: e.target.value })}
                                    placeholder="أدخل اسم الإجراء يدوياً..."
                                    aria-label="اسم الإجراء العلاجي"
                                    className="flex-1 p-3 bg-blue-50/50 border border-blue-100 rounded-xl outline-none text-blue-900 placeholder-blue-300 font-bold"
                                    autoFocus
                                />
                                <button
                                    onClick={() => {
                                        setIsManualProcedure(false);
                                        setTreatment({ ...treatment, procedure: '' });
                                    }}
                                    className="px-4 bg-surface-subtle hover:bg-surface-muted text-text-secondary rounded-xl font-medium transition-colors"
                                >
                                    قائمة
                                </button>
                            </div>
                        ) : (
                            <div className="relative">
                                <label htmlFor="treatment-procedure" className="sr-only">الإجراء العلاجي</label>
                                <select
                                    id="treatment-procedure"
                                    value={treatment.procedure}
                                    onChange={async e => {
                                        const val = e.target.value;
                                        if (val === 'MANUAL_ENTRY_OPTION') {
                                            setIsManualProcedure(true);
                                            setTreatment({ ...treatment, procedure: '', cost: '', price_list_id: null });
                                            return;
                                        }
                                        const { cost, price_list_id, autoMaterials } = await resolveProcedureSelection({
                                            procedureName: val,
                                            procedures: safeProcedures,
                                            defaultPriceListId: initialData?.default_price_list_id,
                                            currentPriceListId: treatment.price_list_id,
                                        });
                                        if (autoMaterials.length > 0) {
                                            logger.debug("[MATERIALS_DEBUG] Auto-loaded materials (BOM):", autoMaterials);
                                            setConsumedMaterials(autoMaterials);
                                            setShowInventory(true);
                                        }
                                        setTreatment({
                                            ...treatment,
                                            procedure: val,
                                            cost,
                                            price_list_id,
                                        });
                                    }}
                                    className="w-full p-3 bg-surface border border-border rounded-xl outline-none appearance-none cursor-pointer font-bold text-text-primary focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
                                >
                                    <option value="">اختر الإجراء العلاجي...</option>
                                    <option value="MANUAL_ENTRY_OPTION" className="font-bold text-primary bg-blue-50">✍️ كتابة إجراء يدوي (غير مضاف)</option>
                                    {displayProcedures.map(p => (
                                        <option key={p.id} value={p.name}>{p.name}</option>
                                    ))}
                                </select>
                                <div className="absolute start-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                                    <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>
                            </div>
                        )}
                        {/* Price Display / Override */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="treatment-cost" className="text-xs font-bold text-text-muted block mb-1">التكلفة</label>
                                <input
                                    id="treatment-cost"
                                    value={treatment.cost}
                                    onChange={e => setTreatment({ ...treatment, cost: e.target.value })}
                                    placeholder="0.00"
                                    type="number"
                                    className="w-full p-3 bg-surface border border-border rounded-xl outline-none font-bold text-text-primary focus-visible:ring-focus"
                                />
                            </div>
                            <div>
                                <label htmlFor="treatment-discount" className="text-xs font-bold text-text-muted block mb-1">الخصم</label>
                                <input
                                    id="treatment-discount"
                                    value={treatment.discount}
                                    onChange={e => setTreatment({ ...treatment, discount: e.target.value })}
                                    placeholder="0.00"
                                    type="number"
                                    className="w-full p-3 bg-surface border border-border border-dashed rounded-xl outline-none text-text-primary focus-visible:ring-focus"
                                />
                            </div>
                        </div>
                        {/* Status Selection */}
                        <div className="pt-2 border-t border-border mt-2">
                            <label className="text-xs font-bold text-text-muted block mb-2">حالة الإجراء</label>
                            <div className="flex p-1 bg-surface border border-border rounded-xl gap-1">
                                {[
                                    { id: 'Pending', label: 'قيد التنفيذ', color: 'text-amber-600 bg-amber-50 border-amber-200' },
                                    { id: 'Done', label: 'تم الانتهاء', color: 'text-green-600 bg-green-50 border-green-200' }
                                ].map((s) => (
                                    <button
                                        key={s.id}
                                        type="button"
                                        onClick={() => setTreatment({ ...treatment, status: s.id })}
                                        className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all ${
                                            (treatment.status || 'Done') === s.id 
                                            ? s.color + ' border shadow-sm scale-[1.02]' 
                                            : 'text-text-muted hover:text-text-secondary'
                                        }`}
                                    >
                                        {s.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="treatment-tooth-number" className="mb-1 block text-xs font-bold text-text-muted">رقم السن</label>
                                <input
                                    id="treatment-tooth-number"
                                    value={treatment.tooth_number || ''}
                                    onChange={e => setTreatment({ ...treatment, tooth_number: e.target.value })}
                                    placeholder="رقم السن"
                                    className="w-full rounded-control border border-border bg-surface-subtle p-3 text-text-primary outline-none focus-visible:ring-focus"
                                />
                            </div>
                            <div>
                                <label htmlFor="treatment-surface" className="mb-1 block text-xs font-bold text-text-muted">سطح السن (Surface)</label>
                                <input
                                    id="treatment-surface"
                                    value={treatment.surface || ''}
                                    onChange={e => handleSurfaceInputChange(e.target.value)}
                                    placeholder="مثال: MOD أو O أو M"
                                    className="w-full rounded-control border border-border bg-surface-subtle p-3 text-text-primary outline-none focus-visible:ring-focus font-mono uppercase"
                                />
                            </div>
                        </div>

                        {/* Interactive Surface Selector Pills */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            <span className="text-xs font-bold text-text-muted me-1">الأسطح:</span>
                            {CLINICAL_SURFACES.map(({ code, label, description }) => {
                                const isSelected = Array.isArray(treatment?.surfaces) && treatment.surfaces.includes(code);
                                return (
                                    <button
                                        key={code}
                                        type="button"
                                        onClick={() => toggleSurface(code)}
                                        title={description}
                                        aria-pressed={isSelected}
                                        aria-label={`تحديد السطح ${code} - ${description}`}
                                        className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-all ${
                                            isSelected
                                                ? 'bg-primary text-white border-primary shadow-sm scale-105'
                                                : 'bg-surface text-text-secondary border-border hover:bg-surface-subtle hover:border-primary/40'
                                        }`}
                                    >
                                        {label}
                                    </button>
                                );
                            })}
                            {(Array.isArray(treatment?.surfaces) && treatment.surfaces.length > 0) && (
                                <button
                                    type="button"
                                    onClick={() => setTreatment(prev => ({ ...prev, surfaces: [], surface: '', target_kind: 'tooth' }))}
                                    className="text-xs text-text-muted hover:text-red-500 ms-2 underline"
                                >
                                    مسح الأسطح
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Advanced Toggle */}
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="w-full py-2 text-sm text-primary font-bold border border-primary/20 rounded-xl hover:bg-primary/5 transition-colors"
                    >
                        {showAdvanced ? '- إخفاء التفاصيل' : '+ إضافة تفاصيل (عصب، قنوات)'}
                    </button>
                    {showAdvanced && (
                        <div className="space-y-4 p-4 bg-primary/5 rounded-2xl border border-primary/10 animate-in slide-in-from-top-2 duration-200">
                            {/* Simplified Advanced Fields for Brevity - Keeping core functionality */}
                            <div>
                                <label className="block text-xs font-bold text-text-muted mb-1">عدد القنوات</label>
                                <input type="number" value={treatment.canal_count} onChange={e => setTreatment({ ...treatment, canal_count: e.target.value })} className="w-full p-3 bg-surface rounded-xl border border-border text-text-primary" placeholder="e.g 3" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-text-muted mb-1">تفاصيل القنوات</label>
                                {(() => {
                                    const normalizedCanals = Array.isArray(treatment.canals) ? treatment.canals : [];
                                    return (
                                        <>
                                            {normalizedCanals.map((canal, idx) => (
                                                <div key={idx} className="flex gap-2 mb-2">
                                                    <input value={canal.name} onChange={e => {
                                                        const newCanals = normalizedCanals.map((c, i) => i === idx ? { ...c, name: e.target.value } : c);
                                                        setTreatment({ ...treatment, canals: newCanals });
                                                    }} placeholder="الاسم" aria-label={`اسم القناة ${idx + 1}`} className="flex-1 p-2 bg-surface rounded-lg border border-border text-text-primary" />
                                                    <input value={canal.length} onChange={e => {
                                                        const newCanals = normalizedCanals.map((c, i) => i === idx ? { ...c, length: e.target.value } : c);
                                                        setTreatment({ ...treatment, canals: newCanals });
                                                    }} placeholder="مم" aria-label={`طول القناة ${idx + 1}`} className="w-20 p-2 bg-surface rounded-lg border border-border text-text-primary" />
                                                </div>
                                            ))}
                                            <button onClick={() => setTreatment({ ...treatment, canals: [...normalizedCanals, { name: '', length: '' }] })} className="text-xs text-primary">+ إضافة قناة</button>
                                        </>
                                    );
                                })()}
                            </div>
                            <textarea value={treatment.sessions} onChange={e => setTreatment({ ...treatment, sessions: e.target.value })} placeholder="جلسات" aria-label="جلسات العلاج" className="w-full p-3 bg-surface rounded-xl border border-border h-20 text-text-primary" />
                            <textarea value={treatment.complications} onChange={e => setTreatment({ ...treatment, complications: e.target.value })} placeholder="المضاعفات" aria-label="مضاعفات العلاج" className="w-full p-3 bg-surface rounded-xl border border-red-200 text-red-600 h-20" />
                        </div>
                    )}
                    {/* Inventory Consumption Section */}
                    <div className="border border-border rounded-xl overflow-hidden">
                        <div className="p-3 bg-surface-subtle flex items-center justify-between">
                            <h4 className="font-bold text-text-primary flex items-center gap-2">
                                <Package size={18} aria-hidden="true" />
                                المواد المستهلكة
                            </h4>
                            <button
                                onClick={() => {
                                    setSmartConsumptionMode('manual');
                                    setIsSmartConsumptionOpen(true);
                                }}
                                className="text-xs font-bold bg-primary text-white px-3 py-1.5 rounded-lg hover:bg-primary-600 transition-colors flex items-center gap-1 shadow-sm shadow-primary/20"
                            >
                                <Plus size={14} aria-hidden="true" /> إضافة
                            </button>
                        </div>

                        {/* Selected Materials List (Always at top if items exist) */}
                        {consumedMaterials.length > 0 && (
                            <div className="p-3 bg-surface border-b border-border space-y-2">
                                <div className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2">المواد المختارة</div>
                                {consumedMaterials.map((item, idx) => {
                                    const mId = item.material_id || item.id;
                                    const matInfo = availableMaterials.find(m => 
                                        (m.material_id?.toString() === mId?.toString()) || 
                                        (m.id?.toString() === mId?.toString())
                                    );
                                    const matName = item.name || item.material_name || matInfo?.material_name || matInfo?.name || 'Unknown Material';
                                    const isDivisible = ['g', 'ml', 'cm'].includes(item.unit?.toLowerCase()) ||
                                        matInfo?.type === 'DIVISIBLE' ||
                                        matInfo?.material_type === 'DIVISIBLE';
                                    const isReusable = matInfo?.type === 'REUSABLE' || matInfo?.material_type === 'REUSABLE';
                                    return (
                                        <div key={idx} className="p-2.5 rounded-xl border border-primary/20 bg-primary/5 shadow-sm transition-all flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                {(isDivisible || isReusable) ? <Droplets size={16} className="text-primary" aria-hidden="true" /> : <Package size={16} className="text-primary" aria-hidden="true" />}
                                                <span className="font-bold text-text-primary text-sm">{matName}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm font-bold bg-surface px-2 py-0.5 rounded border border-border shadow-sm text-text-primary">
                                                    {item.quantity} {isDivisible ? (item.unit || 'وزن نسبي') : (item.unit || 'وحدة')}
                                                </span>
                                                <button
                                                    onClick={() => {
                                                        const newMats = [...consumedMaterials];
                                                        newMats.splice(idx, 1);
                                                        setConsumedMaterials(newMats);
                                                    }}
                                                    aria-label={`حذف ${matName} من المواد المستهلكة`}
                                                    className="p-1 rounded text-red-400 hover:bg-surface hover:text-red-600 transition-colors shadow-sm border border-transparent hover:border-red-100"
                                                >
                                                    <Trash2 size={14} aria-hidden="true" />
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* Material Consumption Panel - shows suggested materials */}
                        {treatment.procedure && (
                            <div className="p-3 bg-surface">
                                <div className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2">اقتراحات حسب الإجراء</div>
                                <MaterialConsumptionPanel
                                    key={`mat-panel-${treatment.id || 'new'}-${treatment.procedure || 'none'}`}
                                    procedureId={safeProcedures.find(p => p.name === treatment.procedure)?.id}
                                    doctorId={treatment.doctor_id}
                                    initialMaterials={consumedMaterials}
                                    onMaterialsChange={(materials) => {
                                        const formatted = materials.map(m => ({
                                            material_id: m.material_id,
                                            quantity: m.material_type === 'NON_DIVISIBLE' ? m.quantity : m.weight,
                                            unit: m.base_unit,
                                            material_type: m.material_type,
                                            weight_score: m.weight,
                                            is_manual_override: m.is_manual_override,
                                            session_id: m.session_id,
                                            name: m.material_name,
                                            category_id: m.category_id
                                        }));
                                        
                                        setConsumedMaterials(prev => {
                                            const incomingCategories = new Set(formatted.map(m => m.category_id));
                                            const manualMaterials = prev.filter(p => !p.category_id || !incomingCategories.has(p.category_id));
                                            return [...manualMaterials, ...formatted];
                                        });
                                    }}
                                />
                            </div>
                        )}

                        {consumedMaterials.length === 0 && (
                            <div className="p-4 text-center text-xs text-text-muted bg-surface-subtle">
                                لم يتم تسجيل أي مواد لهذا الإجراء
                            </div>
                        )}
                    </div>

                    <div>
                        <label htmlFor="treatment-notes" className="mb-1 block text-xs font-bold text-text-muted">ملاحظات عامة</label>
                        <textarea
                            id="treatment-notes"
                            value={treatment.notes}
                            onChange={e => setTreatment({ ...treatment, notes: e.target.value })}
                            placeholder="ملاحظات عامة"
                            className="w-full rounded-control border border-border bg-surface-subtle p-3 text-text-primary outline-none focus-visible:ring-focus"
                        />
                    </div>
                    
                    {/* Multi-Session Tracking (Only if editing existing treatment) */}
                    {isEditing && treatment.id && (
                        <div className="pt-4 border-t border-border">
                            <MultiSessionPanel 
                                sessions={treatment.treatment_sessions || []}
                                onAddSession={handleAddSession}
                                isLoading={addSessionMutation.isPending}
                            />
                        </div>
                    )}

                    <div className="flex justify-end gap-3 text-lg font-bold pt-4 border-t border-border">
                        <button onClick={onClose} disabled={isSaving} className="px-4 py-2 hover:bg-surface-subtle rounded-control disabled:opacity-50">إلغاء</button>
                        <button onClick={handleSave} disabled={isSaving} className="px-6 py-2 bg-primary text-white rounded-control disabled:opacity-50 disabled:cursor-not-allowed">
                            {isSaving ? 'جاري الحفظ...' : 'حفظ'}
                        </button>
                    </div>
                </div>
            </Modal>

            {/* Smart Inventory Modal */}
            <EnhancedMaterialConsumption
                isOpen={isSmartConsumptionOpen}
                onClose={() => setIsSmartConsumptionOpen(false)}
                procedure={safeProcedures.find(p => p.name === treatment.procedure)}
                patientAge={null} 
                patientId={treatment.patient_id}
                availableMaterials={availableMaterials}
                isLoading={isMaterialsLoading}
                initialMaterials={consumedMaterials}
                mode={smartConsumptionMode} // Pass mode
                onSave={(newMaterials) => {
                    const mapped = newMaterials.map(m => ({
                        material_id: m.material_id || m.id,
                        quantity: m.quantity,
                        unit: m.unit,
                        name: m.name || m.material_name, // Ensure name is passed for fallback rendering
                        is_manual_override: true
                    }));
                    
                    // MERGE: Keep existing materials that were selected via the suggestions panel
                    // but update/replace if the same material was picked
                    setConsumedMaterials(prev => {
                        const existingIds = new Set(mapped.map(m => m.material_id.toString()));
                        const filteredPrev = prev.filter(p => !existingIds.has((p.material_id || p.id).toString()));
                        return [...filteredPrev, ...mapped];
                    });
                    
                    setIsSmartConsumptionOpen(false);
                }}
            />
            {/* Session Tracking Modal */}
            <TrackSessionModal
                isOpen={isTrackSessionOpen}
                onClose={() => {
                    setIsTrackSessionOpen(false);
                    setTrackSessionStockItem(null);
                    refetchSessions(); // Refresh status after close
                }}
                mode={trackSessionMode}
                material={trackSessionMaterial}
                stockItem={trackSessionStockItem}
                session={trackSessionData}
                onSuccess={() => {
                    // Auto-retry save after opening session
                    if (trackSessionMode === 'OPEN') {
                        setTimeout(() => handleSave(), 100);
                    }
                }}
            />
        </>
    );
}
