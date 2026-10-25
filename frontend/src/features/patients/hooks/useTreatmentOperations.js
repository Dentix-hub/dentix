import { useCallback, useContext } from 'react';
import { QueryClientContext } from '@tanstack/react-query';
import { invalidatePatientClinicalQueries } from '../utils/invalidatePatientClinicalQueries';
import logger from '@/utils/logger';
import { useTranslation } from 'react-i18next';
import { createTreatment, updateTreatment, updateToothStatus, createLabOrder } from '@/api';
import { palmerToFdi } from '@/utils/toothUtils';
import { toast } from '@/shared/ui';

export const useTreatmentOperations = ({
    patientId,
    refetchHistory,
    refetchTeeth,
    refetchWorkspace,
    setIsTreatmentSheetOpen,
    setEditingTreatmentId,
    editingTreatmentId,
    selectedToothCondition: _selectedToothCondition
}) => {
    const { t } = useTranslation();
    const queryClient = useContext(QueryClientContext);

    const refetchClinicalData = useCallback(async () => {
        await Promise.all([
            Promise.resolve(refetchHistory?.()),
            Promise.resolve(refetchWorkspace?.()),
        ]);
        if (queryClient && patientId) {
            invalidatePatientClinicalQueries(queryClient, patientId);
        }
    }, [refetchHistory, refetchWorkspace, queryClient, patientId]);

    const handleSaveTreatment = useCallback(async (data, options = {}) => {
        if (!data && options?.refetchOnly) {
            await refetchClinicalData();
            return;
        }

        const {
            skipToast = false,
            skipRefetch = false,
        } = options;

        try {
            // Prepare payload: convert Palmer tooth number (e.g. "UR5") to FDI integer (e.g. 15)
            // Backend expects integer or null
            let fdiToothNumber = data.tooth_number;
            if (typeof data.tooth_number === 'string') {
                fdiToothNumber = palmerToFdi(data.tooth_number);
            }
            // If conversion fails (e.g. generic input) but we have a string, set to null to avoid 422
            // unless backend handles string (it doesn't, schema is int)
            if (data.tooth_number && !fdiToothNumber) {
                // Warning: Invalid tooth number string, stripping it to prevent crash
                fdiToothNumber = null;
            }

            const cleanData = { ...data };
            delete cleanData.prefill_source;
            delete cleanData.materials_usage;
            delete cleanData.raw_tooth_number;
            delete cleanData.escalated_from_quick_sheet;
            delete cleanData.escalation_error;
            delete cleanData.explicit_tooth_condition;
            const labOrderData = cleanData.lab_order;
            delete cleanData.lab_order;

            const payload = {
                ...cleanData,
                tooth_number: fdiToothNumber,
                patient_id: parseInt(patientId, 10)
            };

            // 1. Save Treatment
            let savedTreatment = null;
            if (editingTreatmentId) {
                const res = await updateTreatment(editingTreatmentId, payload);
                savedTreatment = res?.data || res || { id: editingTreatmentId, ...payload };
            } else {
                const res = await createTreatment(payload);
                savedTreatment = res?.data || res;
            }

            const targetTreatmentId = savedTreatment?.id || editingTreatmentId;

            // 2. Create linked lab order if specified (D2, D3)
            let labOrderError = null;
            let labOrderExisting = false;
            if (labOrderData?.laboratory_id && targetTreatmentId) {
                try {
                    const labRes = await createLabOrder({
                        patient_id: parseInt(patientId, 10),
                        treatment_id: targetTreatmentId,
                        laboratory_id: parseInt(labOrderData.laboratory_id, 10),
                        work_type: data.procedure || 'Crown',
                        tooth_number: data.tooth_number ? String(data.tooth_number) : '',
                        shade: labOrderData.shade || undefined,
                        material: labOrderData.material || undefined,
                        delivery_date: labOrderData.delivery_date || undefined,
                        cost: parseFloat(labOrderData.cost) || 0,
                        paid_now: parseFloat(labOrderData.paid_now) || 0,
                        price_to_patient: 0,
                        notes: labOrderData.notes || undefined,
                    });
                    const labBody = labRes?.data || labRes;
                    if (labBody?.is_existing) {
                        labOrderExisting = true;
                    }
                } catch (labErr) {
                    logger.error("Failed to create linked lab order:", labErr);
                    labOrderError = labErr;
                }
            }

            // 3. Update Tooth Status ONLY if user explicitly changed the condition in QuickTreatmentSheet
            const conditionToUpdate = data.explicit_tooth_condition;
            if (data.tooth_number && conditionToUpdate) {
                try {
                    logger.log("[DEBUG] Updating Tooth Status:", {
                        patientId,
                        tooth: data.tooth_number,
                        condition: conditionToUpdate
                    });

                    let fdiNumber = palmerToFdi(data.tooth_number);
                    logger.log("[DEBUG] FDI Number:", fdiNumber);

                    if (fdiNumber) {
                        await updateToothStatus({
                            patient_id: parseInt(patientId, 10),
                            tooth_number: fdiNumber,
                            condition: conditionToUpdate
                        });
                        logger.log("[DEBUG] Tooth status updated successfully");
                        await refetchTeeth(); // Await refetch
                    } else {
                        logger.warn("[DEBUG] Failed to convert to FDI:", data.tooth_number);
                    }
                } catch (e) {
                    logger.error("Failed to update tooth status", e);
                    toast.error(t('patient_details.alerts.tooth_update_fail'));
                }
            }

            setIsTreatmentSheetOpen?.(false);
            setEditingTreatmentId(null);
            if (!skipRefetch) {
                await refetchClinicalData();
            }
            if (!skipToast) {
                if (labOrderError) {
                    const res = labOrderError.response?.data;
                    const detail = res?.detail;
                    const envelope = res?.error;
                    const backendMsg = (typeof detail === 'string' && detail) ||
                        envelope?.details?.message ||
                        envelope?.message ||
                        (typeof res?.message === 'string' && res.message);
                    toast.error(backendMsg || t('patient_details.alerts.treatment_saved_lab_failed'));
                } else {
                    if (labOrderExisting) {
                        toast.info(t('patient_details.alerts.lab_order_already_exists'));
                    }
                    toast.success(t('patient_details.alerts.treatment_save_success'));
                }
            }
            return savedTreatment;
        } catch (err) {
            logger.error(err);
            const res = err.response?.data;
            const detail = res?.detail;
            const envelope = res?.error;
            const msg = envelope?.details?.message || envelope?.message || detail || res?.message;

            // SPECIAL HANDLING: Rethrow specific errors so QuickTreatmentSheet can handle them.
            // 1. CONFIRM_OPEN_REQUIRED — QuickTreatmentSheet shows session tracking modal
            // 2. Stock validation errors — QuickTreatmentSheet shows "save without stock" option
            // 3. CLINICAL_LINK_* — QuickTreatmentSheet shows localized plan item link error banner
            const isConfirmOpen = (
                detail?.code === "CONFIRM_OPEN_REQUIRED" ||
                envelope?.details?.code === "CONFIRM_OPEN_REQUIRED" ||
                (typeof msg === 'string' && msg.includes('CONFIRM_OPEN_REQUIRED'))
            );
            const isStockError = err.response?.status === 400 && (
                (typeof detail === 'string' && (detail.includes('مخزون') || detail.includes('stock') || detail.includes('Insufficient'))) ||
                (typeof msg === 'string' && (msg.includes('مخزون') || msg.includes('Insufficient')))
            );
            const isClinicalLink = (
                (typeof detail === 'string' && detail.startsWith('CLINICAL_LINK_')) ||
                (typeof msg === 'string' && msg.includes('CLINICAL_LINK_'))
            );

            if (isConfirmOpen || isStockError || isClinicalLink) {
                throw err; // Let QuickTreatmentSheet handle with specialized UI
            }

            const finalMsg = typeof msg === 'object' ? JSON.stringify(msg) : (msg || t('patient_details.alerts.treatment_save_fail'));
            toast.error(finalMsg);
            err.alreadyNotified = true;
            throw err;
        }
    }, [patientId, editingTreatmentId, refetchTeeth, refetchClinicalData, setIsTreatmentSheetOpen, setEditingTreatmentId, t]);

    return { handleSaveTreatment, refetchClinicalData };
};
