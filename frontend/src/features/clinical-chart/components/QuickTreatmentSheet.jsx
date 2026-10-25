import { useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { QueryClientContext } from '@tanstack/react-query';
import {
    Check,
    Package,
    SlidersHorizontal,
    AlertCircle,
    Plus,
    Trash2,
    Droplets,
    Clock,
    Calendar,
    CheckCircle2,
    FlaskConical,
} from 'lucide-react';
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';

import DentixBottomSheet from '@/shared/ui/DentixBottomSheet';
import { toast } from '@/shared/ui';
import logger from '@/utils/logger';
import { getMaterials, getStockSummary } from '@/api/inventory';
import { addTreatmentSession, getLaboratories, getPatientLabOrders, createLabPayment } from '@/api';
import TrackSessionModal from '@/features/inventory/components/TrackSessionModal';
import { EnhancedMaterialConsumption } from '@/features/inventory/components/EnhancedMaterialConsumption';
import MaterialConsumptionPanel from '@/features/inventory/MaterialConsumptionPanel';
import { resolveProcedureSelection } from '@/features/patients/utils/resolveProcedureSelection';
import { buildTreatmentPayload } from '@/features/patients/utils/buildTreatmentPayload';
import { resolveEffectiveProcedureChartBehavior } from '@/features/clinical-chart/domain/procedureChartAppearance';
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

const TOOTH_CONDITIONS = [
    { key: 'Healthy', labelKey: 'dental_chart.status_healthy', defaultAr: 'سليم' },
    { key: 'Missing', labelKey: 'dental_chart.status_missing', defaultAr: 'مفقود' },
    { key: 'Impacted', labelKey: 'dental_chart.status_impacted', defaultAr: 'منطمر' },
    { key: 'Unerupted', labelKey: 'dental_chart.status_unerupted', defaultAr: 'غير بازغ' },
    { key: 'Retained Root', labelKey: 'dental_chart.status_retained_root', defaultAr: 'جذر متبقي' },
];

const normalizeSheetData = (data) => {
    if (!data) return null;
    const rawSurfaces = Array.isArray(data.surfaces)
        ? data.surfaces
        : (data.surface ? String(data.surface).replace(/[^A-Za-z]/g, '').toUpperCase().split('') : []);
    return {
        ...data,
        status: data.status || 'Done',
        surface: data.surface || rawSurfaces.join(''),
        surfaces: rawSurfaces,
        target_kind: data.target_kind || (rawSurfaces.length > 0 ? 'surface' : 'tooth'),
        canals: Array.isArray(data.canals) ? data.canals : [{ name: '', length: '' }],
        canal_count: data.canal_count ?? '',
        sessions: data.sessions || '',
        complications: data.complications || '',
        notes: data.notes || '',
        diagnosis: data.diagnosis || '',
        discount: data.discount ?? '',
        treatment_sessions: Array.isArray(data.treatment_sessions) ? data.treatment_sessions : [],
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

const suggestConditionForProcedure = (procName) => {
    if (!procName) return null;
    const lower = procName.toLowerCase();
    if (lower.includes('خلع') || lower.includes('extract')) return 'Missing';
    if (lower.includes('طربوش') || lower.includes('تاج') || lower.includes('crown') || lower.includes('bridge')) return 'Crown';
    if (lower.includes('عصب') || lower.includes('endo') || lower.includes('root canal')) return 'Endo';
    if (lower.includes('حشو') || lower.includes('fill') || lower.includes('composite')) return 'Filled';
    return null;
};

/**
 * Unified Treatment Entry & Edit Sheet.
 * Built on `DentixBottomSheet`. Replaces the legacy treatment modal completely.
 * Features: Procedure data, localized tooth status chips, condition confirmation,
 * interactive surface selector pills, inventory consumption, legacy sessions tracking,
 * and lab order integration without duplicate procedures.
 */
export default function QuickTreatmentSheet({
    isOpen,
    onClose,
    onSave,
    onOpenDetails,
    initialData,
    isEditing = false,
    procedures = [],
    patient = null,
    selectedToothCondition = 'Healthy',
    setSelectedToothCondition = null,
    selectedTeeth = [],
    selectedSurfacesByTooth = {},
    onSelectionChange,
    onRefetch,
}) {
    const { t } = useTranslation();
    const queryClient = useContext(QueryClientContext);

    const [treatment, setTreatment] = useState(() => normalizeSheetData(initialData));
    const [consumedMaterials, setConsumedMaterials] = useState([]);
    const [isSaving, setIsSaving] = useState(false);
    const isSavingRef = useRef(false);
    const [highlightedInvalidTeeth, setHighlightedInvalidTeeth] = useState([]);

    // UI expansion & specialized states
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [isManualProcedure, setIsManualProcedure] = useState(false);
    const [linkError, setLinkError] = useState(null);
    const [explicitToothCondition, setExplicitToothCondition] = useState(null);
    const [suggestedCondition, setSuggestedCondition] = useState(null);

    // Inventory consumption modals
    const [availableMaterials, setAvailableMaterials] = useState([]);
    const [isMaterialsLoading, setIsMaterialsLoading] = useState(false);
    const [isSmartConsumptionOpen, setIsSmartConsumptionOpen] = useState(false);
    const [smartConsumptionMode, setSmartConsumptionMode] = useState('smart');

    // Conflict / TrackSession state
    const [isTrackSessionOpen, setIsTrackSessionOpen] = useState(false);
    const [trackSessionMode, setTrackSessionMode] = useState('OPEN');
    const [trackSessionMaterial, setTrackSessionMaterial] = useState(null);
    const [trackSessionStockItem, setTrackSessionStockItem] = useState(null);

    // Lab section state
    const [laboratories, setLaboratories] = useState([]);
    const [patientLabOrdersList, setPatientLabOrdersList] = useState([]);
    const [labData, setLabData] = useState({
        laboratory_id: '',
        shade: '',
        material: '',
        delivery_date: '',
        notes: '',
        cost: '',
        paid_now: '',
    });
    const [isRecordingPayment, setIsRecordingPayment] = useState(false);
    const [paymentAmount, setPaymentAmount] = useState('');
    const [paymentNotes, setPaymentNotes] = useState('');
    const [isSubmittingPayment, setIsSubmittingPayment] = useState(false);
    const [paymentError, setPaymentError] = useState('');

    // Sessions section state (legacy path D4)
    const [isAddingSession, setIsAddingSession] = useState(false);
    const [isAddingSessionLoading, setIsAddingSessionLoading] = useState(false);
    const [newSessionData, setNewSessionData] = useState({
        notes: '',
        next_session_date: '',
        status: 'completed',
    });

    const handleSaveErrorRef = useRef(null);

    const safeProcedures = useMemo(
        () => (Array.isArray(procedures) ? procedures : []),
        [procedures],
    );

    const matchedProcedure = useMemo(() => {
        if (!treatment?.procedure) return null;
        return safeProcedures.find((p) => p.name === treatment.procedure) || null;
    }, [safeProcedures, treatment?.procedure]);

    const chartBehavior = useMemo(() => {
        if (!matchedProcedure) return null;
        return resolveEffectiveProcedureChartBehavior(matchedProcedure);
    }, [matchedProcedure]);

    const paletteSwatch = useMemo(() => {
        return chartBehavior?.paletteSwatch || null;
    }, [chartBehavior]);

    // Check if prosthetic / lab required
    const isProsthetic = useMemo(() => {
        if (!treatment?.procedure) return false;
        if (chartBehavior?.requires_lab) return true;
        if (chartBehavior?.category === 'prosthodontic' || chartBehavior?.category === 'prosthetics') return true;
        if (matchedProcedure?.category === 'prosthodontic' || matchedProcedure?.category === 'prosthetics') return true;
        if (matchedProcedure?.canonical_code?.startsWith('PROS_')) return true;
        return /crown|bridge|veneer|inlay|onlay|denture|طربوش|تاج|جسر|تركيب/i.test(treatment.procedure);
    }, [chartBehavior, matchedProcedure, treatment?.procedure]);

    // Cap at 32 teeth (full adult dentition).
    const effectiveTeeth = useMemo(() => {
        const raw = (Array.isArray(selectedTeeth) && selectedTeeth.length > 0)
            ? selectedTeeth
            : (Array.isArray(treatment?.selectedTeeth) && treatment.selectedTeeth.length > 0)
                ? treatment.selectedTeeth
                : (Array.isArray(initialData?.selectedTeeth) && initialData.selectedTeeth.length > 0)
                    ? initialData.selectedTeeth
                    : (Array.isArray(treatment?.toothKeys) && treatment.toothKeys.length > 0)
                        ? treatment.toothKeys
                        : (treatment?.tooth_number ? [treatment.tooth_number] : []);
        return raw.slice(0, 32);
    }, [selectedTeeth, treatment?.selectedTeeth, treatment?.toothKeys, treatment?.tooth_number, initialData?.selectedTeeth]);

    const isMultiTooth = !isEditing && effectiveTeeth.length > 1;

    const effectiveSurfacesByTooth = useMemo(() => {
        if (selectedSurfacesByTooth && Object.keys(selectedSurfacesByTooth).length > 0) {
            return selectedSurfacesByTooth;
        }
        return treatment?.selectedSurfacesByTooth || initialData?.selectedSurfacesByTooth || {};
    }, [selectedSurfacesByTooth, treatment?.selectedSurfacesByTooth, initialData?.selectedSurfacesByTooth]);

    const getSurfacesForTooth = useCallback((toothKey) => {
        if (!toothKey) return [];
        const fdi = palmerToFdi(toothKey) || toothKey;
        const strKey = String(toothKey);
        const strFdi = fdi != null ? String(fdi) : null;

        if (effectiveSurfacesByTooth) {
            if (Array.isArray(effectiveSurfacesByTooth[strKey]) && effectiveSurfacesByTooth[strKey].length > 0) {
                return effectiveSurfacesByTooth[strKey];
            }
            if (strFdi && Array.isArray(effectiveSurfacesByTooth[strFdi]) && effectiveSurfacesByTooth[strFdi].length > 0) {
                return effectiveSurfacesByTooth[strFdi];
            }
        }

        const treatFdi = palmerToFdi(treatment?.tooth_number) || treatment?.tooth_number;
        if (String(treatFdi) === strKey || (strFdi && String(treatFdi) === strFdi) || String(treatment?.tooth_number) === strKey) {
            if (Array.isArray(treatment?.surfaces) && treatment.surfaces.length > 0) {
                return treatment.surfaces;
            }
        }
        return [];
    }, [effectiveSurfacesByTooth, treatment?.tooth_number, treatment?.surfaces]);

    const procedureRequiresSurfaces = useMemo(() => {
        if (treatment?.target_kind === 'surface') return true;
        if (matchedProcedure?.allowed_target_kinds?.length === 1 && matchedProcedure.allowed_target_kinds[0] === 'surface') {
            return true;
        }
        return false;
    }, [treatment?.target_kind, matchedProcedure]);

    // Load inventory stock summary and laboratories when open
    useEffect(() => {
        if (!isOpen) return;

        setIsMaterialsLoading(true);
        getStockSummary().then((res) => {
            const list = res?.data?.data || res?.data || [];
            setAvailableMaterials(Array.isArray(list) ? list : []);
        }).catch(() => {
            getMaterials().then((res) => {
                const list = res?.data?.data || res?.data || [];
                setAvailableMaterials(Array.isArray(list) ? list : []);
            }).catch(() => {});
        }).finally(() => {
            setIsMaterialsLoading(false);
        });

        getLaboratories().then((res) => {
            setLaboratories(Array.isArray(res?.data) ? res.data : []);
        }).catch(() => {});

        const patientId = patient?.id || initialData?.patient_id;
        if (patientId) {
            getPatientLabOrders(patientId).then((res) => {
                setPatientLabOrdersList(Array.isArray(res?.data) ? res.data : []);
            }).catch(() => {});
        }
    }, [isOpen, patient?.id, initialData?.patient_id]);

    // Reset and initialize data on open
    useEffect(() => {
        if (!isOpen) return;
        const normalized = normalizeSheetData(initialData);
        setTreatment(normalized);
        setHighlightedInvalidTeeth([]);
        setLinkError(null);
        setIsManualProcedure(false);
        setShowAdvanced(false);
        setIsAddingSession(false);
        setNewSessionData({ notes: '', next_session_date: '', status: 'completed' });
        setLabData({
            laboratory_id: '',
            shade: '',
            material: '',
            delivery_date: '',
            notes: '',
            cost: '',
            paid_now: '',
        });
        setIsRecordingPayment(false);
        setPaymentAmount('');
        setPaymentNotes('');
        setPaymentError('');

        const initialCondition = initialData?.explicit_tooth_condition || initialData?.diagnosis || selectedToothCondition || 'Healthy';
        setExplicitToothCondition(initialCondition);

        const procName = normalized?.procedure;
        if (procName) {
            const suggestion = suggestConditionForProcedure(procName);
            setSuggestedCondition(suggestion);

            resolveProcedureSelection({
                procedureName: procName,
                procedures: safeProcedures,
                defaultPriceListId: normalized?.default_price_list_id,
                currentPriceListId: normalized?.price_list_id,
            }).then(({ found, cost, price_list_id, autoMaterials }) => {
                if (!found) {
                    setIsManualProcedure(true);
                    setTreatment((prev) => (prev ? {
                        ...prev,
                        procedure: procName,
                        cost: prev.cost ?? '',
                        price_list_id: null,
                    } : prev));
                    setConsumedMaterials(initialData?.consumedMaterials || []);
                } else {
                    const resolvedCost = (initialData?.cost !== undefined && initialData?.cost !== '')
                        ? initialData.cost
                        : cost;
                    setTreatment((prev) => (prev ? {
                        ...prev,
                        procedure: procName,
                        cost: resolvedCost,
                        price_list_id,
                    } : prev));
                    setConsumedMaterials(initialData?.consumedMaterials?.length ? initialData.consumedMaterials : (autoMaterials || []));
                }
            });
        } else {
            setConsumedMaterials(initialData?.consumedMaterials || []);
        }

        // Escalation error recovery
        if (normalized?.escalation_error) {
            setTimeout(() => {
                handleSaveErrorRef.current?.(normalized.escalation_error, false);
            }, 0);
        }
    }, [isOpen, initialData, safeProcedures, selectedToothCondition]);

    // Find linked lab order for this treatment if editing
    const linkedLabOrder = useMemo(() => {
        if (!treatment?.id) return null;
        return patientLabOrdersList.find((o) => o.treatment_id === treatment.id && o.status !== 'cancelled') || null;
    }, [treatment?.id, patientLabOrdersList]);

    if (!isOpen || !treatment) return null;

    const fdiTooth = palmerToFdi(treatment.tooth_number) || treatment.tooth_number || '';
    const surfaceList = Array.isArray(treatment.surfaces) ? treatment.surfaces : [];
    const numericCost = parseFloat(treatment.cost) || 0;
    const isUnpriced = numericCost === 0;
    const currentStatus = treatment.status || 'Done';
    const totalCost = isMultiTooth ? (numericCost * effectiveTeeth.length) : numericCost;
    const totalCostFormatted = totalCost.toFixed(2);

    const selectedCondition = explicitToothCondition || treatment.diagnosis || selectedToothCondition || 'Healthy';

    const getConditionLabel = (condKey) => {
        const found = TOOTH_CONDITIONS.find((c) => c.key.toLowerCase() === (condKey || '').toLowerCase());
        if (found) return t(found.labelKey, found.defaultAr);
        return condKey;
    };

    const handleConfirmCondition = (condKey) => {
        setExplicitToothCondition(condKey);
        setSelectedToothCondition?.(condKey);
        setTreatment((prev) => ({
            ...prev,
            diagnosis: condKey,
        }));
    };

    // Surface manipulation
    const toggleSurface = (code) => {
        const current = Array.isArray(treatment?.surfaces) ? [...treatment.surfaces] : [];
        const exists = current.includes(code);
        const updated = exists ? current.filter((s) => s !== code) : [...current, code];
        const order = ['M', 'O', 'I', 'D', 'B', 'L', 'P'];
        updated.sort((a, b) => order.indexOf(a) - order.indexOf(b));
        const surfaceStr = updated.join('');
        setTreatment((prev) => ({
            ...prev,
            surfaces: updated,
            surface: surfaceStr,
            target_kind: updated.length > 0 ? 'surface' : 'tooth',
        }));
    };

    const handleSurfaceInputChange = (value) => {
        const clean = value.replace(/[^A-Za-z]/g, '').toUpperCase();
        const letters = clean.split('').filter((c, i, arr) => arr.indexOf(c) === i);
        setTreatment((prev) => ({
            ...prev,
            surface: clean,
            surfaces: letters,
            target_kind: letters.length > 0 ? 'surface' : 'tooth',
        }));
    };

    const handleProcedureChange = async (e) => {
        const val = e.target.value;
        if (val === 'MANUAL_ENTRY_OPTION') {
            setIsManualProcedure(true);
            setTreatment((prev) => ({ ...prev, procedure: '', cost: '', price_list_id: null }));
            return;
        }

        const suggestion = suggestConditionForProcedure(val);
        setSuggestedCondition(suggestion);

        const { cost, price_list_id, autoMaterials } = await resolveProcedureSelection({
            procedureName: val,
            procedures: safeProcedures,
            defaultPriceListId: treatment.default_price_list_id,
            currentPriceListId: treatment.price_list_id,
        });

        if (autoMaterials && autoMaterials.length > 0) {
            setConsumedMaterials(autoMaterials);
        }

        setTreatment((prev) => ({
            ...prev,
            procedure: val,
            cost,
            price_list_id,
        }));
    };

    // Conflict recovery helpers (F4)
    const getConfirmOpenDetail = (error) => {
        const data = error?.response?.data;
        const candidates = [
            data?.error?.details,
            typeof data?.detail === 'object' ? data.detail : null,
            data?.details,
            data?.data,
            data,
        ];
        const structured = candidates.find((item) => item?.code === 'CONFIRM_OPEN_REQUIRED');
        if (structured) return structured;

        const message = [
            typeof data?.detail === 'string' ? data.detail : '',
            data?.error?.message,
            data?.message,
        ].find((value) => typeof value === 'string' && value.includes('CONFIRM_OPEN_REQUIRED'));

        if (!message) return null;

        const [, rest = ''] = message.split('CONFIRM_OPEN_REQUIRED:');
        const [stockId, ...nameParts] = rest.split(':');
        return {
            code: 'CONFIRM_OPEN_REQUIRED',
            stock_item_id: parseInt(stockId, 10),
            material_info: nameParts.join(':') || 'Material',
        };
    };

    const openTrackSessionForConflict = (detail) => {
        const stockItemId = Number(detail.stock_item_id || detail.stockItemId || detail.stock_item?.id);
        const materialName = detail.material_info || detail.material_name || detail.message || 'Material';

        setTrackSessionMode('OPEN');
        setTrackSessionMaterial({
            id: detail.material_id,
            name: materialName,
            material_name: materialName,
        });
        setTrackSessionStockItem(stockItemId ? {
            id: stockItemId,
            name: materialName,
            material_name: materialName,
        } : null);
        setIsTrackSessionOpen(true);
    };

    const handleSaveError = (error, forceSkipStock = false) => {
        logger.error('[QUICK_SHEET] Save Error Details:', error);

        const confirmOpenDetail = getConfirmOpenDetail(error);
        if (confirmOpenDetail) {
            openTrackSessionForConflict(confirmOpenDetail);
            return;
        }

        const responseData = error.response?.data;
        const errDetail = responseData?.detail;

        // Case 1: Clinical plan item link error
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

        // Case 2: Stock validation failure (400)
        const isStockError = error.response?.status === 400 && (
            (typeof errDetail === 'string' && (errDetail.includes('مخزون') || errDetail.includes('stock') || errDetail.includes('Insufficient'))) ||
            (typeof responseData?.message === 'string' && responseData.message.includes('مخزون'))
        );

        if (isStockError && !forceSkipStock) {
            toast((toastObj) => (
                <div className="flex flex-col gap-2 max-w-xs" dir="rtl">
                    <div className="flex items-center gap-2 text-red-700 font-bold text-sm">
                        <span>⚠️</span>
                        <span>{t('quick_treatment_sheet.stock_insufficient', 'نقص في المخزون')}</span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                        {typeof errDetail === 'string' ? errDetail : 'بعض المواد غير متوفرة في المخزن حالياً.'}
                    </p>
                    <div className="flex gap-2 pt-1 border-t border-slate-100">
                        <button
                            type="button"
                            onClick={() => {
                                toast.dismiss(toastObj.id);
                                handleSave(null, true);
                            }}
                            className="flex-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-bold transition-colors"
                        >
                            {t('quick_treatment_sheet.save_without_stock', 'حفظ بدون خصم مخزون')}
                        </button>
                        <button
                            type="button"
                            onClick={() => toast.dismiss(toastObj.id)}
                            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-bold transition-colors"
                        >
                            {t('quick_treatment_sheet.cancel_button', 'إلغاء')}
                        </button>
                    </div>
                </div>
            ), { duration: 15000 });
            return;
        }

        const errorEnvelope = responseData?.error;
        const friendlyMsg = typeof errDetail === 'string' ? errDetail :
            (errDetail?.message || errorEnvelope?.message || error.message || t('quick_treatment_sheet.errors.save_failed', 'فشل حفظ العلاج'));

        if (!error.alreadyNotified) {
            toast.error(friendlyMsg);
        }
    };
    handleSaveErrorRef.current = handleSaveError;

    // Sessions handler (legacy D4)
    const handleSaveSession = async () => {
        if (!newSessionData.notes || !treatment.id) return;
        setIsAddingSessionLoading(true);
        try {
            const res = await addTreatmentSession(treatment.id, {
                ...newSessionData,
                treatment_id: treatment.id,
                tenant_id: treatment.tenant_id,
            });
            const createdSession = res?.data || {
                ...newSessionData,
                id: Date.now(),
                created_at: new Date().toISOString(),
            };
            setTreatment((prev) => ({
                ...prev,
                treatment_sessions: [...(prev.treatment_sessions || []), createdSession],
            }));
            queryClient?.invalidateQueries({ queryKey: ['patient-details', treatment.patient_id] });
            setIsAddingSession(false);
            setNewSessionData({ notes: '', next_session_date: '', status: 'completed' });
            toast.success(t('quick_treatment_sheet.session_saved', 'تم حفظ الجلسة بنجاح'));
        } catch (err) {
            logger.error('Failed to add session', err);
            toast.error(err?.response?.data?.detail || 'فشل حفظ الجلسة');
        } finally {
            setIsAddingSessionLoading(false);
        }
    };

    const handleRecordLabPayment = async (e) => {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        setPaymentError('');
        if (!linkedLabOrder) return;
        const remaining = linkedLabOrder.remaining_amount != null
            ? Number(linkedLabOrder.remaining_amount)
            : Math.max(0, (Number(linkedLabOrder.cost) || 0) - (Number(linkedLabOrder.paid_amount) || 0));
        const amt = parseFloat(paymentAmount);
        if (isNaN(amt) || amt <= 0) {
            const msg = t('labs.details.payments.messages.invalid_amount', 'يرجى إدخال مبلغ صحيح أكبر من الصفر');
            setPaymentError(msg);
            toast.error(msg);
            return;
        }
        if (amt > remaining) {
            const msg = t('labs.details.payments.messages.overpay', 'المبلغ المدفوع يتجاوز المتبقي للطلب');
            setPaymentError(msg);
            toast.error(msg);
            return;
        }
        setIsSubmittingPayment(true);
        try {
            await createLabPayment(linkedLabOrder.laboratory_id, {
                lab_order_id: linkedLabOrder.id,
                amount: amt,
                notes: paymentNotes || undefined,
            });
            toast.success(t('quick_treatment_sheet.payment_success', 'تم تسجيل الدفعة بنجاح'));
            setIsRecordingPayment(false);
            setPaymentAmount('');
            setPaymentNotes('');
            const patientId = patient?.id || initialData?.patient_id;
            if (patientId) {
                const res = await getPatientLabOrders(patientId);
                setPatientLabOrdersList(Array.isArray(res?.data) ? res.data : []);
            }
        } catch (err) {
            const detail = err.response?.data?.detail;
            const msg = typeof detail === 'string' ? detail : t('labs.details.payments.messages.add_fail', 'فشل تسجيل الدفعة');
            setPaymentError(msg);
            toast.error(msg);
        } finally {
            setIsSubmittingPayment(false);
        }
    };

    const handleSave = async (e, forceSkipStock = false) => {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        if (isSavingRef.current) return;

        // Surface validation: if procedure requires surfaces, ensure every tooth has surfaces specified
        if (procedureRequiresSurfaces) {
            const invalidTeeth = effectiveTeeth.filter((t) => getSurfacesForTooth(t).length === 0);
            if (invalidTeeth.length > 0) {
                setHighlightedInvalidTeeth(invalidTeeth);
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

        if (isProsthetic && labData.laboratory_id) {
            const numCost = parseFloat(labData.cost) || 0;
            const numPaid = parseFloat(labData.paid_now) || 0;
            if (numPaid > numCost) {
                toast.error(t('quick_treatment_sheet.paid_now_exceeds_cost', 'المبلغ المدفوع الآن لا يمكن أن يتجاوز تكلفة الطلب'));
                return;
            }
        }

        isSavingRef.current = true;
        setIsSaving(true);

        const cleanTreatment = { ...treatment };
        delete cleanTreatment.escalated_from_quick_sheet;
        delete cleanTreatment.escalation_error;
        if (explicitToothCondition) {
            cleanTreatment.explicit_tooth_condition = explicitToothCondition;
        }
        if (isProsthetic && labData.laboratory_id) {
            cleanTreatment.lab_order = labData;
        }

        if (!isMultiTooth) {
            const payload = buildTreatmentPayload(
                {
                    ...cleanTreatment,
                    status: currentStatus,
                },
                {
                    consumedMaterials,
                    procedures: safeProcedures,
                    isEditing,
                    forceSkipStock,
                },
            );

            try {
                setLinkError(null);
                await onSave(payload);
                onClose?.();
            } catch (error) {
                if (typeof onOpenDetails === 'function') {
                    onOpenDetails({
                        ...cleanTreatment,
                        cost: treatment.cost,
                        status: currentStatus,
                        consumedMaterials,
                        selectedTeeth: effectiveTeeth,
                        selectedSurfacesByTooth: effectiveSurfacesByTooth,
                        escalated_from_quick_sheet: true,
                        escalation_error: error,
                    });
                    onClose?.();
                } else {
                    handleSaveError(error, forceSkipStock);
                }
            } finally {
                isSavingRef.current = false;
                setIsSaving(false);
            }
            return;
        }

        // Multi-tooth sequential save
        let failedIndex = -1;
        let lastError = null;
        let successCount = 0;

        for (let i = 0; i < effectiveTeeth.length; i++) {
            const toothKey = effectiveTeeth[i];
            const toothSurfaces = getSurfacesForTooth(toothKey);
            const toothFdi = palmerToFdi(toothKey) || toothKey;
            const toothPalmer = fdiToPalmer(toothFdi) || String(toothKey);
            const singleTargetKind = toothSurfaces.length > 0 ? 'surface' : (cleanTreatment.target_kind || 'tooth');

            const singleTreatment = {
                ...cleanTreatment,
                tooth_number: toothPalmer,
                surfaces: toothSurfaces,
                surface: toothSurfaces.join(''),
                target_kind: singleTargetKind,
                status: currentStatus,
            };

            const singlePayload = buildTreatmentPayload(
                singleTreatment,
                {
                    consumedMaterials,
                    procedures: safeProcedures,
                    isEditing: false,
                    forceSkipStock,
                },
            );

            try {
                await onSave(singlePayload, { skipToast: true, skipRefetch: true });
                successCount++;
            } catch (error) {
                failedIndex = i;
                lastError = error;
                break;
            }
        }

        try {
            if (successCount > 0 && typeof onRefetch === 'function') {
                await onRefetch();
            }

            if (failedIndex !== -1) {
                const remainingTeeth = effectiveTeeth.slice(failedIndex);
                onSelectionChange?.(remainingTeeth);
                handleSaveError(lastError, forceSkipStock);
            } else {
                toast.success(
                    t('quick_treatment_sheet.multi_save_success', 'تم حفظ الإجراءات لـ {{count}} أسنان بنجاح', {
                        count: effectiveTeeth.length,
                        defaultValue: t('patient_details.alerts.treatment_save_success', 'تم حفظ الإجراء بنجاح'),
                    })
                );
                onSelectionChange?.([]);
                onClose?.();
            }
        } finally {
            isSavingRef.current = false;
            setIsSaving(false);
        }
    };

    const dialogTitle = isEditing
        ? t('quick_treatment_sheet.edit_title', 'تعديل بيانات العلاج')
        : (treatment.tooth_number ? `تفاصيل السن رقم #${treatment.tooth_number}` : t('quick_treatment_sheet.create_title', 'تسجيل علاج جديد'));

    const headerTitle = (
        <span className="inline-flex items-center gap-2" data-testid="quick-treatment-sheet-header">
            {paletteSwatch && (
                <span
                    data-testid="quick-treatment-sheet-swatch"
                    data-color-key={paletteSwatch.key}
                    style={{
                        backgroundColor: paletteSwatch.fill,
                        borderColor: paletteSwatch.stroke,
                    }}
                    className="inline-block h-3.5 w-3.5 shrink-0 rounded-full border"
                    title={`${paletteSwatch.labelAr} / ${paletteSwatch.labelEn}`}
                />
            )}
            <span data-testid="quick-treatment-sheet-procedure-name">
                {treatment.procedure || dialogTitle}
            </span>
            {treatment.tooth_number && (
                <span className="text-xs text-text-muted font-normal">
                    (#{treatment.tooth_number})
                </span>
            )}
            <span className="sr-only">{dialogTitle}</span>
        </span>
    );

    const sessions = treatment.treatment_sessions || [];

    return (
        <>
            <DentixBottomSheet
                open={isOpen}
                onOpenChange={(nextOpen) => {
                    if (!nextOpen) onClose?.();
                }}
                title={headerTitle}
                closeLabel={t('quick_treatment_sheet.close_button_label', 'إغلاق نافذة العلاج')}
            >
                <form
                    onSubmit={handleSave}
                    data-testid="quick-treatment-sheet"
                    className="space-y-4"
                >
                    {/* Hidden helper testids for tests expecting legacy treatment sheet semantics */}
                    <div data-testid="treatment-modal" className="sr-only">
                        <span data-testid="treatment-modal-tooth">{treatment.tooth_number}</span>
                        <span data-testid="treatment-modal-procedure">{treatment.procedure}</span>
                        <span data-testid="treatment-modal-surface">{treatment.surface}</span>
                        <span data-testid="treatment-modal-surfaces">{(treatment.surfaces || []).join(',')}</span>
                        <span data-testid="treatment-modal-target-kind">{treatment.target_kind}</span>
                    </div>

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

                    {/* Modal Context Header for chart-driven opens */}
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

                    {/* Tooth & Surface Target Chips */}
                    <div className="flex flex-wrap items-center gap-2" data-testid="quick-treatment-sheet-targets">
                        {isMultiTooth ? (
                            <>
                                <span
                                    data-testid="quick-treatment-multi-tooth-count"
                                    className="inline-flex items-center rounded-lg bg-blue-100 px-2.5 py-1 text-xs font-bold text-blue-800 dark:bg-blue-900/60 dark:text-blue-200"
                                >
                                    {t('quick_treatment_sheet.multi_teeth_count', '{{count}} أسنان', { count: effectiveTeeth.length })}
                                </span>
                                <div className="flex flex-wrap items-center gap-1.5" data-testid="quick-treatment-multi-tooth-chips">
                                    {effectiveTeeth.map((toothKey) => {
                                        const fdi = palmerToFdi(toothKey) || toothKey;
                                        const palmer = fdiToPalmer(fdi);
                                        const surfs = getSurfacesForTooth(toothKey);
                                        const isInvalid = highlightedInvalidTeeth.includes(toothKey);

                                        return (
                                            <span
                                                key={toothKey}
                                                data-testid={`quick-treatment-tooth-chip-${fdi}`}
                                                data-invalid={isInvalid ? 'true' : undefined}
                                                className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-xs font-bold transition-all ${
                                                    isInvalid
                                                        ? 'border-red-400 bg-red-50 text-red-700 ring-2 ring-red-400 dark:border-red-700 dark:bg-red-950/50 dark:text-red-300'
                                                        : 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-200'
                                                }`}
                                            >
                                                <span className="font-mono">{fdi}</span>
                                                {palmer && String(palmer) !== String(fdi) && (
                                                    <span className="text-blue-600/70 font-mono text-[10px] dark:text-blue-300/70">
                                                        ({palmer})
                                                    </span>
                                                )}
                                                {surfs.length > 0 ? (
                                                    <span className="rounded bg-indigo-100 px-1 py-0.2 font-mono text-[10px] text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">
                                                        {surfs.join('')}
                                                    </span>
                                                ) : (
                                                    <span className="text-[10px] text-slate-400">
                                                        ({t('quick_treatment_sheet.whole_tooth_short', 'كامل')})
                                                    </span>
                                                )}
                                            </span>
                                        );
                                    })}
                                </div>
                            </>
                        ) : (
                            <>
                                {treatment.tooth_number && (
                                    <span
                                        data-testid="quick-treatment-tooth-chip"
                                        data-palmer-tooth={treatment.tooth_number}
                                        data-fdi-tooth={fdiTooth}
                                        className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold text-blue-800 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-200"
                                    >
                                        <span>{t('quick_treatment_sheet.tooth_label', 'السن:')}</span>
                                        <span className="font-mono">{fdiTooth}</span>
                                        {String(fdiTooth) !== String(treatment.tooth_number) && (
                                            <span className="text-blue-600/80 font-mono dark:text-blue-300/80">
                                                ({treatment.tooth_number})
                                            </span>
                                        )}
                                    </span>
                                )}

                                {surfaceList.length > 0 ? (
                                    <div className="flex flex-wrap items-center gap-1" data-testid="quick-treatment-surface-chips">
                                        <span className="text-xs font-bold text-slate-500 dark:text-slate-400">{t('quick_treatment_sheet.surfaces_label', 'الأسطح:')}</span>
                                        {surfaceList.map((surf) => (
                                            <span
                                                key={surf}
                                                data-testid={`quick-treatment-surface-chip-${surf}`}
                                                className="inline-flex items-center rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 font-mono text-xs font-bold text-indigo-800 dark:border-indigo-800 dark:bg-indigo-950/50 dark:text-indigo-200"
                                            >
                                                {surf}
                                            </span>
                                        ))}
                                    </div>
                                ) : (
                                    <span
                                        data-testid="quick-treatment-whole-tooth-chip"
                                        className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                    >
                                        {t('quick_treatment_sheet.whole_tooth', 'كامل السن (Whole tooth)')}
                                    </span>
                                )}
                            </>
                        )}
                    </div>

                    {/* Tooth Status Chips & Suggestion Banner */}
                    {treatment.tooth_number && (
                        <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/30">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-slate-600 dark:text-slate-300">
                                    {t('quick_treatment_sheet.tooth_condition_label', 'حالة السن')}
                                </span>
                                {selectedCondition && (
                                    <span className="rounded bg-slate-200 px-2 py-0.5 font-mono text-[10px] font-bold text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                                        {getConditionLabel(selectedCondition)}
                                    </span>
                                )}
                            </div>

                            {suggestedCondition && suggestedCondition !== selectedCondition && (
                                <div
                                    data-testid="condition-suggestion-banner"
                                    className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs dark:border-amber-900/40 dark:bg-amber-950/40"
                                >
                                    <span className="text-amber-800 dark:text-amber-200">
                                        {t('dental_chart.condition_suggested', 'الحالة المقترحة:')}{' '}
                                        <strong>{getConditionLabel(suggestedCondition)}</strong>
                                    </span>
                                    <button
                                        type="button"
                                        onClick={() => handleConfirmCondition(suggestedCondition)}
                                        className="rounded-md bg-amber-600 px-2.5 py-1 text-xs font-bold text-white shadow-xs hover:bg-amber-700"
                                    >
                                        {t('dental_chart.confirm_condition', 'تأكيد الحالة')}
                                    </button>
                                </div>
                            )}

                            <div className="flex flex-wrap gap-1.5">
                                {TOOTH_CONDITIONS.map((cond) => {
                                    const isActive = (selectedCondition || 'Healthy').toLowerCase() === cond.key.toLowerCase();
                                    const localizedLabel = t(cond.labelKey, cond.defaultAr);
                                    return (
                                        <button
                                            key={cond.key}
                                            type="button"
                                            onClick={() => handleConfirmCondition(cond.key)}
                                            className={`rounded-full px-3 py-1 text-xs font-bold transition-all border ${
                                                isActive
                                                    ? 'bg-slate-800 text-white border-slate-800 shadow-xs dark:bg-slate-100 dark:text-slate-900'
                                                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
                                            }`}
                                        >
                                            {localizedLabel}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Tooth Number & Interactive Surface Pills */}
                    <div className="space-y-1.5">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                                <label htmlFor="treatment-tooth-number" className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                    {t('quick_treatment_sheet.tooth_label', 'رقم السن')}
                                </label>
                                <input
                                    id="treatment-tooth-number"
                                    aria-label="رقم السن"
                                    type="text"
                                    value={treatment.tooth_number || ''}
                                    onChange={(e) => setTreatment((prev) => ({ ...prev, tooth_number: e.target.value }))}
                                    placeholder="رقم السن (e.g. 11 or UR1)"
                                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                />
                            </div>
                            <div>
                                <label htmlFor="treatment-surface" className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                    {t('quick_treatment_sheet.surfaces_label', 'سطح السن (Surface)')}
                                </label>
                                <input
                                    id="treatment-surface"
                                    aria-label="سطح السن (Surface)"
                                    type="text"
                                    value={treatment.surface || ''}
                                    onChange={(e) => handleSurfaceInputChange(e.target.value)}
                                    placeholder="مثال: MOD أو O أو M"
                                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 font-mono text-xs uppercase text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                />
                            </div>
                        </div>

                        {/* Interactive Surface Selector Pills */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 me-1">
                                {t('quick_treatment_sheet.surfaces_label', 'الأسطح:')}
                            </span>
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
                                        className={`rounded-lg px-2.5 py-1 text-xs font-bold border transition-all ${
                                            isSelected
                                                ? 'bg-blue-600 text-white border-blue-600 shadow-xs scale-105'
                                                : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
                                        }`}
                                    >
                                        {label}
                                    </button>
                                );
                            })}
                            {Array.isArray(treatment?.surfaces) && treatment.surfaces.length > 0 && (
                                <button
                                    type="button"
                                    onClick={() => setTreatment((prev) => ({ ...prev, surfaces: [], surface: '', target_kind: 'tooth' }))}
                                    className="text-xs text-slate-500 hover:text-red-500 ms-2 underline dark:text-slate-400"
                                >
                                    {t('quick_treatment_sheet.clear_surfaces', 'مسح الأسطح')}
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Procedure & Price Section */}
                    <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/30">
                        <div>
                            <label htmlFor="treatment-diagnosis" className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                {t('quick_treatment_sheet.diagnosis_label', 'التشخيص')}
                            </label>
                            <input
                                id="treatment-diagnosis"
                                aria-label="التشخيص"
                                type="text"
                                value={treatment.diagnosis || ''}
                                onChange={(e) => setTreatment((prev) => ({ ...prev, diagnosis: e.target.value }))}
                                placeholder="التشخيص (e.g. Dental caries, Pulpitis)"
                                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                            />
                        </div>

                        <div>
                            <label htmlFor="treatment-procedure" className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                {t('quick_treatment_sheet.procedure_label', 'الإجراء')}
                            </label>
                            {isManualProcedure ? (
                                <div className="flex gap-2">
                                    <input
                                        value={treatment.procedure || ''}
                                        onChange={(e) => setTreatment((prev) => ({ ...prev, procedure: e.target.value }))}
                                        placeholder="أدخل اسم الإجراء يدوياً..."
                                        aria-label="اسم الإجراء العلاجي"
                                        className="flex-1 rounded-xl border border-blue-200 bg-blue-50/50 p-2.5 text-xs font-bold text-blue-900 outline-none focus:border-blue-500 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-100"
                                        autoFocus
                                    />
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setIsManualProcedure(false);
                                            setTreatment((prev) => ({ ...prev, procedure: '' }));
                                        }}
                                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                    >
                                        قائمة
                                    </button>
                                </div>
                            ) : (
                                <select
                                    id="treatment-procedure"
                                    aria-label="الإجراء العلاجي"
                                    value={treatment.procedure || ''}
                                    onChange={handleProcedureChange}
                                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                >
                                    <option value="">اختر الإجراء العلاجي...</option>
                                    <option value="MANUAL_ENTRY_OPTION" className="font-bold text-blue-600 bg-blue-50">✍️ كتابة إجراء يدوي (غير مضاف)</option>
                                    {safeProcedures.map((p) => (
                                        <option key={p.id} value={p.name}>{p.name}</option>
                                    ))}
                                </select>
                            )}
                        </div>

                        {/* Cost & Discount */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                                <div className="mb-1 flex items-center justify-between">
                                    <label
                                        htmlFor="quick-treatment-cost"
                                        className="text-xs font-bold text-slate-600 dark:text-slate-300"
                                    >
                                        {isMultiTooth
                                            ? t('quick_treatment_sheet.unit_cost_label', 'سعر السن الواحد')
                                            : t('quick_treatment_sheet.cost_label', 'التكلفة')}
                                    </label>
                                    {isUnpriced && (
                                        <span
                                            data-testid="quick-treatment-unpriced-hint"
                                            className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                                        >
                                            {t('quick_treatment_sheet.unpriced_hint', 'غير مسعّر')}
                                        </span>
                                    )}
                                </div>
                                <input
                                    id="quick-treatment-cost"
                                    data-testid="quick-treatment-cost-input"
                                    aria-label="التكلفة"
                                    type="number"
                                    value={treatment.cost ?? ''}
                                    onChange={(e) => setTreatment((prev) => ({ ...prev, cost: e.target.value }))}
                                    placeholder="0.00"
                                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 font-bold text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                />
                                {isMultiTooth && (
                                    <div
                                        data-testid="quick-treatment-total-cost-summary"
                                        className="mt-1.5 flex items-center justify-between rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-semibold text-slate-700 dark:bg-slate-800/80 dark:text-slate-300"
                                    >
                                        <span>{t('quick_treatment_sheet.total_cost_label', 'الإجمالي ({{count}} أسنان):', { count: effectiveTeeth.length })}</span>
                                        <span className="font-mono font-bold text-blue-600 dark:text-blue-400">
                                            {totalCostFormatted} ({effectiveTeeth.length} × {numericCost.toFixed(2)})
                                        </span>
                                    </div>
                                )}
                            </div>

                            <div>
                                <label
                                    htmlFor="treatment-discount"
                                    className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300"
                                >
                                    {t('quick_treatment_sheet.discount_label', 'الخصم')}
                                </label>
                                <input
                                    id="treatment-discount"
                                    aria-label="الخصم"
                                    type="number"
                                    value={treatment.discount ?? ''}
                                    onChange={(e) => setTreatment((prev) => ({ ...prev, discount: e.target.value }))}
                                    placeholder="0.00"
                                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 font-bold text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                />
                            </div>
                        </div>

                        {/* Status Segmented Control */}
                        <div>
                            <span className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                {t('quick_treatment_sheet.status_label', 'حالة الإجراء')}
                            </span>
                            <div
                                data-testid="quick-treatment-status-control"
                                className="flex gap-1 rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-900"
                            >
                                {[
                                    { id: 'Done', label: t('quick_treatment_sheet.status_done', 'تم الانتهاء'), activeClass: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' },
                                    { id: 'Pending', label: t('quick_treatment_sheet.status_pending', 'قيد التنفيذ'), activeClass: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-300' },
                                ].map((opt) => {
                                    const isActive = currentStatus === opt.id;
                                    return (
                                        <button
                                            key={opt.id}
                                            type="button"
                                            data-testid={`quick-treatment-status-${opt.id}`}
                                            aria-pressed={isActive}
                                            onClick={() => setTreatment((prev) => ({ ...prev, status: opt.id }))}
                                            className={`flex-1 rounded-lg py-2 text-xs font-bold transition-all ${
                                                isActive
                                                    ? `${opt.activeClass} border shadow-xs`
                                                    : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'
                                            }`}
                                        >
                                            {opt.label}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    {/* Advanced Collapsible (Canals, Complications, Sessions Notes) */}
                    <div>
                        <button
                            type="button"
                            data-testid="quick-treatment-more-details-button"
                            onClick={() => {
                                if (typeof onOpenDetails === 'function') {
                                    onClose?.();
                                    onOpenDetails({
                                        ...treatment,
                                        status: currentStatus,
                                        consumedMaterials,
                                        selectedTeeth: effectiveTeeth,
                                        selectedSurfacesByTooth: effectiveSurfacesByTooth,
                                        escalated_from_quick_sheet: true,
                                    });
                                } else {
                                    setShowAdvanced(!showAdvanced);
                                }
                            }}
                            className="w-full py-2 text-xs text-blue-600 font-bold border border-blue-200 dark:border-blue-800 rounded-xl hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-colors flex items-center justify-center gap-1.5"
                        >
                            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
                            <span>{showAdvanced ? t('quick_treatment_sheet.hide_details', '- إخفاء التفاصيل') : t('quick_treatment_sheet.more_details_button', 'تفاصيل إضافية (More details)')}</span>
                        </button>

                        {showAdvanced && (
                            <div className="mt-3 space-y-3 rounded-2xl border border-blue-100 bg-blue-50/30 p-3 dark:border-blue-900/40 dark:bg-blue-950/20">
                                <div>
                                    <label htmlFor="treatment-canal-count" className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                        عدد القنوات
                                    </label>
                                    <input
                                        id="treatment-canal-count"
                                        type="number"
                                        value={treatment.canal_count ?? ''}
                                        onChange={(e) => setTreatment((prev) => ({ ...prev, canal_count: e.target.value }))}
                                        placeholder="e.g. 3"
                                        className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                    />
                                </div>

                                <div>
                                    <span className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                        تفاصيل القنوات
                                    </span>
                                    {(treatment.canals || []).map((canal, idx) => (
                                        <div key={idx} className="flex gap-2 mb-2">
                                            <input
                                                value={canal.name}
                                                onChange={(e) => {
                                                    const updated = [...treatment.canals];
                                                    updated[idx] = { ...updated[idx], name: e.target.value };
                                                    setTreatment((prev) => ({ ...prev, canals: updated }));
                                                }}
                                                placeholder="الاسم"
                                                aria-label={`اسم القناة ${idx + 1}`}
                                                className="flex-1 rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            />
                                            <input
                                                value={canal.length}
                                                onChange={(e) => {
                                                    const updated = [...treatment.canals];
                                                    updated[idx] = { ...updated[idx], length: e.target.value };
                                                    setTreatment((prev) => ({ ...prev, canals: updated }));
                                                }}
                                                placeholder="مم"
                                                aria-label={`طول القناة ${idx + 1}`}
                                                className="w-20 rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            />
                                        </div>
                                    ))}
                                    <button
                                        type="button"
                                        onClick={() => setTreatment((prev) => ({
                                            ...prev,
                                            canals: [...(prev.canals || []), { name: '', length: '' }],
                                        }))}
                                        className="text-xs font-bold text-blue-600 hover:underline dark:text-blue-400"
                                    >
                                        + إضافة قناة
                                    </button>
                                </div>

                                <div>
                                    <label htmlFor="treatment-sessions-text" className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                                        جلسات العلاج
                                    </label>
                                    <textarea
                                        id="treatment-sessions-text"
                                        aria-label="جلسات العلاج"
                                        value={treatment.sessions || ''}
                                        onChange={(e) => setTreatment((prev) => ({ ...prev, sessions: e.target.value }))}
                                        placeholder="جلسات العلاج..."
                                        className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white h-16"
                                    />
                                </div>

                                <div>
                                    <label htmlFor="treatment-complications" className="mb-1 block text-xs font-bold text-red-600 dark:text-red-400">
                                        مضاعفات العلاج
                                    </label>
                                    <textarea
                                        id="treatment-complications"
                                        aria-label="مضاعفات العلاج"
                                        value={treatment.complications || ''}
                                        onChange={(e) => setTreatment((prev) => ({ ...prev, complications: e.target.value }))}
                                        placeholder="المضاعفات..."
                                        className="w-full rounded-xl border border-red-200 bg-white p-2.5 text-xs text-red-700 outline-none focus:border-red-500 dark:border-red-900/60 dark:bg-slate-900 dark:text-red-300 h-16"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Inventory BOM & Consumed Materials */}
                    <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-900/30">
                        <div className="flex items-center justify-between">
                            <h4 className="flex items-center gap-1.5 text-xs font-bold text-slate-700 dark:text-slate-300">
                                <Package size={15} />
                                <span>{t('quick_treatment_sheet.materials_title', 'المواد المستهلكة')}</span>
                            </h4>
                            <button
                                type="button"
                                onClick={() => {
                                    setSmartConsumptionMode('manual');
                                    setIsSmartConsumptionOpen(true);
                                }}
                                className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-bold text-white shadow-xs hover:bg-blue-700"
                            >
                                <Plus size={12} />
                                <span>{t('quick_treatment_sheet.add_material', 'إضافة مادة')}</span>
                            </button>
                        </div>

                        {consumedMaterials.length > 0 && (
                            <div
                                data-testid="quick-treatment-bom-summary"
                                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-200/80 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-900 dark:border-indigo-900/50 dark:bg-indigo-950/30 dark:text-indigo-200"
                            >
                                <span className="inline-flex items-center gap-1.5 font-semibold">
                                    <Package className="h-4 w-4 text-indigo-600 dark:text-indigo-400" aria-hidden="true" />
                                    <span>
                                        سيتم خصم {consumedMaterials.length} مواد ({consumedMaterials.length} materials will be deducted)
                                    </span>
                                </span>
                                <button
                                    type="button"
                                    data-testid="quick-treatment-bom-details-link"
                                    onClick={() => {
                                        setSmartConsumptionMode('manual');
                                        setIsSmartConsumptionOpen(true);
                                    }}
                                    className="font-bold text-indigo-700 underline hover:text-indigo-900 dark:text-indigo-300"
                                >
                                    تعديل المواد / Details
                                </button>
                            </div>
                        )}

                        {consumedMaterials.length > 0 && (
                            <div className="space-y-1.5 pt-1" data-testid="quick-treatment-materials-list">
                                {consumedMaterials.map((item, idx) => {
                                    const mId = item.material_id || item.id;
                                    const matInfo = availableMaterials.find((m) =>
                                        String(m.material_id || m.id) === String(mId)
                                    );
                                    const matName = item.name || item.material_name || matInfo?.material_name || matInfo?.name || 'Material';

                                    return (
                                        <div
                                            key={idx}
                                            className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-2 text-xs dark:border-slate-700 dark:bg-slate-800"
                                        >
                                            <div className="flex items-center gap-2">
                                                <Droplets size={14} className="text-blue-500" />
                                                <span className="font-semibold text-slate-800 dark:text-slate-200">{matName}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] font-bold text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                                                    {item.quantity} {item.unit || 'وحدة'}
                                                </span>
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        const updated = [...consumedMaterials];
                                                        updated.splice(idx, 1);
                                                        setConsumedMaterials(updated);
                                                    }}
                                                    aria-label={`حذف ${matName} من المواد المستهلكة`}
                                                    className="p-1 text-slate-400 hover:text-red-500"
                                                >
                                                    <Trash2 size={13} />
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {Boolean(queryClient && treatment.procedure) && (
                            <div className="pt-1">
                                <MaterialConsumptionPanel
                                    key={`mat-panel-${treatment.id || 'new'}-${treatment.procedure || 'none'}`}
                                    procedureId={safeProcedures.find((p) => p.name === treatment.procedure)?.id}
                                    doctorId={treatment.doctor_id}
                                    initialMaterials={consumedMaterials}
                                    onMaterialsChange={(materials) => {
                                        const formatted = materials.map((m) => ({
                                            material_id: m.material_id,
                                            quantity: m.material_type === 'NON_DIVISIBLE' ? m.quantity : m.weight,
                                            unit: m.base_unit,
                                            material_type: m.material_type,
                                            weight_score: m.weight,
                                            is_manual_override: m.is_manual_override,
                                            session_id: m.session_id,
                                            name: m.material_name,
                                            category_id: m.category_id,
                                        }));

                                        setConsumedMaterials((prev) => {
                                            const incomingCategories = new Set(formatted.map((m) => m.category_id));
                                            const manualMaterials = prev.filter((p) => !p.category_id || !incomingCategories.has(p.category_id));
                                            return [...manualMaterials, ...formatted];
                                        });
                                    }}
                                />
                            </div>
                        )}
                    </div>

                    {/* Lab Section (D2, D3) */}
                    {isProsthetic && (
                        <div className="space-y-3 rounded-2xl border border-teal-200 bg-teal-50/50 p-4 dark:border-teal-900/50 dark:bg-teal-950/30">
                            <div className="flex items-center justify-between">
                                <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-teal-800 dark:text-teal-300">
                                    <FlaskConical size={16} />
                                    <span>{t('quick_treatment_sheet.lab_section_title', 'بيانات المعمل')}</span>
                                </h4>
                                {linkedLabOrder && (
                                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${
                                        linkedLabOrder.status === 'cancelled'
                                            ? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                                            : linkedLabOrder.payment_status === 'paid' || (linkedLabOrder.remaining_amount != null && Number(linkedLabOrder.remaining_amount) <= 0)
                                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200'
                                                : linkedLabOrder.payment_status === 'partial' || Number(linkedLabOrder.paid_amount) > 0
                                                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200'
                                                    : 'bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-200'
                                    }`}>
                                        {linkedLabOrder.status === 'cancelled'
                                            ? t('labs.details.orders.status_cancelled', 'ملغي')
                                            : linkedLabOrder.payment_status === 'paid' || (linkedLabOrder.remaining_amount != null && Number(linkedLabOrder.remaining_amount) <= 0)
                                                ? t('labs.details.orders.status_paid', 'مدفوع')
                                                : linkedLabOrder.payment_status === 'partial' || Number(linkedLabOrder.paid_amount) > 0
                                                    ? t('labs.details.orders.status_partial', 'جزئي')
                                                    : t('labs.details.orders.status_unpaid', 'غير مدفوع')}
                                    </span>
                                )}
                            </div>

                            {linkedLabOrder ? (
                                <div className="space-y-3 rounded-xl bg-white p-3 border border-teal-100 text-xs dark:bg-slate-900 dark:border-teal-900/40">
                                    <div className="flex items-center justify-between">
                                        <span className="font-bold text-slate-700 dark:text-slate-200">
                                            {linkedLabOrder.laboratory_name || laboratories.find((l) => l.id === linkedLabOrder.laboratory_id)?.name || t('quick_treatment_sheet.lab_order_linked', 'طلب معمل مرتبط')}
                                        </span>
                                        <span className="font-mono text-slate-500">#{linkedLabOrder.id}</span>
                                    </div>
                                    <div className="flex flex-wrap gap-2 text-[11px] text-slate-600 dark:text-slate-400">
                                        {linkedLabOrder.work_type && <span className="rounded bg-slate-100 px-2 py-0.5 dark:bg-slate-800">{linkedLabOrder.work_type}</span>}
                                        {linkedLabOrder.material && <span className="rounded bg-slate-100 px-2 py-0.5 dark:bg-slate-800">{linkedLabOrder.material}</span>}
                                        {linkedLabOrder.shade && <span className="rounded bg-slate-100 px-2 py-0.5 dark:bg-slate-800">Shade: {linkedLabOrder.shade}</span>}
                                        {linkedLabOrder.delivery_date && <span className="rounded bg-slate-100 px-2 py-0.5 dark:bg-slate-800">Delivery: {linkedLabOrder.delivery_date}</span>}
                                    </div>
                                    {linkedLabOrder.notes && (
                                        <p className="text-[11px] text-slate-500 dark:text-slate-400 italic">{linkedLabOrder.notes}</p>
                                    )}

                                    {/* Read-only financial summary: cost / paid / remaining */}
                                    <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-center">
                                        <div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/50">
                                            <div className="text-[10px] text-slate-500">{t('quick_treatment_sheet.lab_cost_label', 'تكلفة المعمل')}</div>
                                            <div className="font-mono font-bold text-slate-800 dark:text-slate-200">{Number(linkedLabOrder.cost || 0)}</div>
                                        </div>
                                        <div className="rounded-lg bg-emerald-50/50 p-2 dark:bg-emerald-950/30">
                                            <div className="text-[10px] text-emerald-700 dark:text-emerald-400">{t('quick_treatment_sheet.lab_paid_amount', 'المسدد')}</div>
                                            <div className="font-mono font-bold text-emerald-600 dark:text-emerald-300">{Number(linkedLabOrder.paid_amount || 0)}</div>
                                        </div>
                                        <div className="rounded-lg bg-amber-50/50 p-2 dark:bg-amber-950/30">
                                            <div className="text-[10px] text-amber-700 dark:text-amber-400">{t('quick_treatment_sheet.lab_remaining_amount', 'المتبقي')}</div>
                                            <div className="font-mono font-bold text-amber-600 dark:text-amber-300">
                                                {linkedLabOrder.remaining_amount != null
                                                    ? Number(linkedLabOrder.remaining_amount)
                                                    : Math.max(0, (Number(linkedLabOrder.cost) || 0) - (Number(linkedLabOrder.paid_amount) || 0))}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Small Record Payment form instead of paid_now */}
                                    {linkedLabOrder.status !== 'cancelled' && (
                                        linkedLabOrder.remaining_amount == null || Number(linkedLabOrder.remaining_amount) > 0 || (Number(linkedLabOrder.cost || 0) > Number(linkedLabOrder.paid_amount || 0))
                                    ) && (
                                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                                            {!isRecordingPayment ? (
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        const rem = linkedLabOrder.remaining_amount != null
                                                            ? Number(linkedLabOrder.remaining_amount)
                                                            : Math.max(0, (Number(linkedLabOrder.cost) || 0) - (Number(linkedLabOrder.paid_amount) || 0));
                                                        setPaymentAmount(rem > 0 ? String(rem) : '');
                                                        setPaymentNotes('');
                                                        setPaymentError('');
                                                        setIsRecordingPayment(true);
                                                    }}
                                                    className="w-full rounded-xl bg-teal-600 px-3 py-2 text-xs font-bold text-white transition-colors hover:bg-teal-700 shadow-sm"
                                                >
                                                    {t('quick_treatment_sheet.record_payment', 'تسجيل دفعة')}
                                                </button>
                                            ) : (
                                                <div className="space-y-2 rounded-xl bg-teal-50/80 p-3 border border-teal-200 dark:bg-teal-950/40 dark:border-teal-900/60">
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-bold text-teal-800 dark:text-teal-300 text-xs">
                                                            {t('quick_treatment_sheet.record_payment', 'تسجيل دفعة')}
                                                        </span>
                                                        <button
                                                            type="button"
                                                            onClick={() => setIsRecordingPayment(false)}
                                                            className="text-slate-400 hover:text-slate-600 text-xs font-bold"
                                                        >
                                                            {t('common.cancel', 'إلغاء')}
                                                        </button>
                                                    </div>
                                                    {paymentError && (
                                                        <div className="text-[11px] text-red-600 dark:text-red-400 font-semibold">{paymentError}</div>
                                                    )}
                                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                        <div>
                                                            <label htmlFor="quick-sheet-payment-amount" className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                                                {t('labs.details.payments.form.amount', 'المبلغ')}
                                                            </label>
                                                            <input
                                                                id="quick-sheet-payment-amount"
                                                                type="number"
                                                                step="0.01"
                                                                min="0.01"
                                                                value={paymentAmount}
                                                                onChange={(e) => setPaymentAmount(e.target.value)}
                                                                placeholder="0.00"
                                                                className="w-full rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                                            />
                                                        </div>
                                                        <div>
                                                            <label htmlFor="quick-sheet-payment-notes" className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                                                {t('labs.details.payments.form.notes', 'ملاحظات')}
                                                            </label>
                                                            <input
                                                                id="quick-sheet-payment-notes"
                                                                type="text"
                                                                value={paymentNotes}
                                                                onChange={(e) => setPaymentNotes(e.target.value)}
                                                                placeholder="ملاحظات الدفعة..."
                                                                className="w-full rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                                            />
                                                        </div>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        disabled={isSubmittingPayment}
                                                        onClick={handleRecordLabPayment}
                                                        className="w-full rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-teal-700 disabled:opacity-50"
                                                    >
                                                        {isSubmittingPayment ? t('common.saving', 'جاري الحفظ...') : t('quick_treatment_sheet.record_payment', 'تسجيل الدفعة')}
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    <div>
                                        <label htmlFor="quick-treatment-lab-select" className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                                            {t('quick_treatment_sheet.lab_select', 'اختر المعمل')}
                                        </label>
                                        <select
                                            id="quick-treatment-lab-select"
                                            aria-label={t('quick_treatment_sheet.lab_select', 'اختر المعمل')}
                                            value={labData.laboratory_id}
                                            onChange={(e) => setLabData((prev) => ({ ...prev, laboratory_id: e.target.value }))}
                                            className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs font-bold text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                        >
                                            <option value="">{t('quick_treatment_sheet.lab_select', 'اختر المعمل...')}</option>
                                            {laboratories.map((lab) => (
                                                <option key={lab.id} value={lab.id}>{lab.name}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div>
                                            <label htmlFor="quick-treatment-lab-cost" className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                                                {t('quick_treatment_sheet.lab_cost_label', 'تكلفة المعمل')}
                                            </label>
                                            <input
                                                id="quick-treatment-lab-cost"
                                                type="number"
                                                min="0"
                                                step="0.01"
                                                value={labData.cost}
                                                onChange={(e) => setLabData((prev) => ({ ...prev, cost: e.target.value }))}
                                                placeholder="0.00"
                                                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            />
                                        </div>
                                        {parseFloat(labData.cost) > 0 && (
                                            <div>
                                                <label htmlFor="quick-treatment-lab-paid-now" className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                                                    {t('quick_treatment_sheet.paid_now_label', 'دفعت الآن')}
                                                </label>
                                                <input
                                                    id="quick-treatment-lab-paid-now"
                                                    type="number"
                                                    min="0"
                                                    max={labData.cost}
                                                    step="0.01"
                                                    value={labData.paid_now}
                                                    onChange={(e) => setLabData((prev) => ({ ...prev, paid_now: e.target.value }))}
                                                    placeholder="0.00"
                                                    className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                                />
                                            </div>
                                        )}
                                    </div>

                                    {parseFloat(labData.cost) > 0 && parseFloat(labData.paid_now) > parseFloat(labData.cost) && (
                                        <p className="text-[11px] text-red-600 dark:text-red-400 font-semibold">
                                            {t('quick_treatment_sheet.paid_now_exceeds_cost', 'المبلغ المدفوع الآن لا يمكن أن يتجاوز تكلفة الطلب')}
                                        </p>
                                    )}

                                    <p className="text-[11px] text-teal-700 dark:text-teal-300 font-medium">
                                        {t('quick_treatment_sheet.lab_accounting_hint', 'التكلفة بتتسجل مديونية على المعمل، والمبلغ المدفوع بيتسجل كمصروف')}
                                    </p>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div>
                                            <label htmlFor="quick-treatment-lab-shade" className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                                                {t('quick_treatment_sheet.shade_label', 'درجة اللون (Shade)')}
                                            </label>
                                            <input
                                                id="quick-treatment-lab-shade"
                                                type="text"
                                                value={labData.shade}
                                                onChange={(e) => setLabData((prev) => ({ ...prev, shade: e.target.value }))}
                                                placeholder="e.g. A2, 3M"
                                                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            />
                                        </div>
                                        <div>
                                            <label htmlFor="quick-treatment-lab-material" className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                                                {t('quick_treatment_sheet.material_label', 'المادة (Material)')}
                                            </label>
                                            <select
                                                id="quick-treatment-lab-material"
                                                value={labData.material}
                                                onChange={(e) => setLabData((prev) => ({ ...prev, material: e.target.value }))}
                                                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            >
                                                <option value="">اختر المادة...</option>
                                                <option value="Zirconia">Zirconia</option>
                                                <option value="E-max">E-max</option>
                                                <option value="PFM">PFM</option>
                                                <option value="Full Metal">Full Metal</option>
                                                <option value="Acrylic">Acrylic</option>
                                                <option value="Composite">Composite</option>
                                                <option value="Other">Other</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div>
                                            <label htmlFor="quick-treatment-lab-delivery-date" className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                                                {t('quick_treatment_sheet.delivery_date_label', 'موعد الاستلام المتوقع')}
                                            </label>
                                            <input
                                                id="quick-treatment-lab-delivery-date"
                                                type="date"
                                                value={labData.delivery_date}
                                                onChange={(e) => setLabData((prev) => ({ ...prev, delivery_date: e.target.value }))}
                                                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            />
                                        </div>
                                        <div>
                                            <label htmlFor="quick-treatment-lab-notes" className="mb-1 block text-xs font-bold text-slate-700 dark:text-slate-300">
                                                {t('quick_treatment_sheet.lab_notes_label', 'ملاحظات المعمل')}
                                            </label>
                                            <input
                                                id="quick-treatment-lab-notes"
                                                type="text"
                                                value={labData.notes}
                                                onChange={(e) => setLabData((prev) => ({ ...prev, notes: e.target.value }))}
                                                placeholder="تعليمات خاصة للمعمل..."
                                                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-teal-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Sessions Section (D4, legacy path) */}
                    {Boolean(isEditing && treatment.id) && (
                        <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-900/40">
                            <div className="flex items-center justify-between">
                                <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                                    <Clock size={16} className="text-blue-500" />
                                    <span>{t('quick_treatment_sheet.sessions_section_title', 'سجل الجلسات (Sessions)')}</span>
                                </h4>
                                {!isAddingSession && (
                                    <button
                                        type="button"
                                        onClick={() => setIsAddingSession(true)}
                                        className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-600 hover:bg-blue-100 dark:bg-blue-950/60 dark:text-blue-300"
                                    >
                                        <Plus size={12} />
                                        <span>{t('quick_treatment_sheet.add_session', 'إضافة جلسة')}</span>
                                    </button>
                                )}
                            </div>

                            {isAddingSession && (
                                <div className="space-y-3 rounded-xl border-2 border-dashed border-blue-200 bg-blue-50/40 p-3 dark:border-blue-900/60 dark:bg-blue-950/30">
                                    <textarea
                                        autoFocus
                                        value={newSessionData.notes}
                                        onChange={(e) => setNewSessionData((prev) => ({ ...prev, notes: e.target.value }))}
                                        placeholder={t('quick_treatment_sheet.session_notes_placeholder', 'ماذا تم في هذه الجلسة؟')}
                                        className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white min-h-[60px]"
                                    />
                                    <div className="flex flex-wrap items-end justify-between gap-2">
                                        <div className="min-w-[160px] flex-1">
                                            <label htmlFor="quick-treatment-next-session" className="mb-1 block text-[10px] font-bold text-slate-500 dark:text-slate-400">
                                                {t('quick_treatment_sheet.next_session_date', 'موعد الجلسة القادمة (اختياري)')}
                                            </label>
                                            <input
                                                id="quick-treatment-next-session"
                                                type="date"
                                                value={newSessionData.next_session_date}
                                                onChange={(e) => setNewSessionData((prev) => ({ ...prev, next_session_date: e.target.value }))}
                                                className="w-full rounded-lg border border-slate-200 bg-white p-2 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                                            />
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                type="button"
                                                onClick={() => setIsAddingSession(false)}
                                                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                            >
                                                {t('quick_treatment_sheet.cancel_button', 'إلغاء')}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={handleSaveSession}
                                                disabled={!newSessionData.notes || isAddingSessionLoading}
                                                className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-blue-700 disabled:opacity-50"
                                            >
                                                {isAddingSessionLoading ? t('quick_treatment_sheet.saving_button', 'جاري الحفظ...') : t('quick_treatment_sheet.save_session', 'حفظ الجلسة')}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="space-y-2">
                                {sessions.length === 0 ? (
                                    <div data-testid="empty-sessions-notice" className="rounded-xl border border-dashed border-slate-200 bg-white py-6 text-center dark:border-slate-800 dark:bg-slate-900/50">
                                        <Clock size={28} className="mx-auto mb-2 text-slate-300 opacity-50 dark:text-slate-600" />
                                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                            {t('quick_treatment_sheet.no_sessions', 'لا يوجد جلسات مسجلة بعد')}
                                        </p>
                                    </div>
                                ) : (
                                    sessions.map((session, index) => (
                                        <div
                                            key={session.id ? `session-${session.id}-${index}` : `session-idx-${index}`}
                                            className="rounded-xl border border-slate-100 bg-white p-3 shadow-xs transition-all dark:border-slate-800 dark:bg-slate-900"
                                        >
                                            <div className="mb-1 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-50 font-mono text-[10px] font-bold text-blue-600 dark:bg-blue-950 dark:text-blue-300">
                                                        #{sessions.length - index}
                                                    </span>
                                                    <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                                                        {session.created_at ? format(new Date(session.created_at), 'PPP', { locale: ar }) : ''}
                                                    </span>
                                                </div>
                                                <CheckCircle2 size={14} className="text-emerald-500" />
                                            </div>
                                            <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                                                {session.notes}
                                            </p>
                                            {session.next_session_date && (
                                                <div className="mt-2 flex items-center gap-1.5 border-t border-slate-50 pt-2 text-[10px] font-bold text-blue-600 dark:border-slate-800 dark:text-blue-400">
                                                    <Calendar size={12} />
                                                    <span>{t('quick_treatment_sheet.next_visit_prefix', 'الموعد القادم:')} {format(new Date(session.next_session_date), 'PPP', { locale: ar })}</span>
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}

                    {/* Notes textarea */}
                    <div>
                        <label htmlFor="treatment-notes" className="mb-1 block text-xs font-bold text-slate-600 dark:text-slate-300">
                            {t('quick_treatment_sheet.notes_label', 'ملاحظات عامة')}
                        </label>
                        <textarea
                            id="treatment-notes"
                            aria-label="ملاحظات عامة"
                            value={treatment.notes || ''}
                            onChange={(e) => setTreatment((prev) => ({ ...prev, notes: e.target.value }))}
                            placeholder="ملاحظات سريرية..."
                            className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-900 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white min-h-[60px]"
                        />
                    </div>

                    {/* Action buttons: Cancel, Save */}
                    <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                        <button
                            type="button"
                            data-testid="quick-treatment-cancel-button"
                            onClick={() => onClose?.()}
                            className="min-h-11 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                        >
                            {t('quick_treatment_sheet.cancel_button', 'إلغاء')}
                        </button>
                        <button
                            type="submit"
                            data-testid="quick-treatment-save-button"
                            disabled={isSaving}
                            className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-blue-600 px-5 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 disabled:opacity-60"
                        >
                            <Check className="h-4 w-4" aria-hidden="true" />
                            <span>
                                {isSaving
                                    ? t('quick_treatment_sheet.saving_button', 'جاري الحفظ...')
                                    : (isMultiTooth
                                        ? t('quick_treatment_sheet.save_all_button', 'حفظ للكل ({{count}})', { count: effectiveTeeth.length })
                                        : t('quick_treatment_sheet.save_button', 'حفظ'))}
                            </span>
                        </button>
                    </div>
                </form>
            </DentixBottomSheet>

            {/* Smart Inventory Modal */}
            {isSmartConsumptionOpen && (
                <EnhancedMaterialConsumption
                    isOpen={isSmartConsumptionOpen}
                    onClose={() => setIsSmartConsumptionOpen(false)}
                    procedure={matchedProcedure}
                    patientAge={null}
                    patientId={treatment?.patient_id || patient?.id}
                    availableMaterials={availableMaterials}
                    isLoading={isMaterialsLoading}
                    initialMaterials={consumedMaterials}
                    mode={smartConsumptionMode}
                    onSave={(newMaterials) => {
                        const mapped = newMaterials.map((m) => ({
                            material_id: m.material_id || m.id,
                            quantity: m.quantity,
                            unit: m.unit,
                            name: m.name || m.material_name,
                            is_manual_override: true,
                        }));
                        setConsumedMaterials((prev) => {
                            const existingIds = new Set(mapped.map((m) => m.material_id.toString()));
                            const filteredPrev = prev.filter((p) => !existingIds.has((p.material_id || p.id).toString()));
                            return [...filteredPrev, ...mapped];
                        });
                        setIsSmartConsumptionOpen(false);
                    }}
                />
            )}

            {/* Conflict / TrackSession Modal */}
            {isTrackSessionOpen && (
                <TrackSessionModal
                    isOpen={isTrackSessionOpen}
                    onClose={() => {
                        setIsTrackSessionOpen(false);
                        setTrackSessionStockItem(null);
                    }}
                    mode={trackSessionMode}
                    material={trackSessionMaterial}
                    stockItem={trackSessionStockItem}
                    onSuccess={() => {
                        if (trackSessionMode === 'OPEN') {
                            setTimeout(() => handleSave(), 100);
                        }
                    }}
                />
            )}
        </>
    );
}

QuickTreatmentSheet.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    onOpenDetails: PropTypes.func,
    initialData: PropTypes.object,
    isEditing: PropTypes.bool,
    procedures: PropTypes.arrayOf(PropTypes.object),
    patient: PropTypes.object,
    selectedToothCondition: PropTypes.string,
    setSelectedToothCondition: PropTypes.func,
    selectedTeeth: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.number])),
    selectedSurfacesByTooth: PropTypes.object,
    onSelectionChange: PropTypes.func,
    onRefetch: PropTypes.func,
};
