import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { createTreatment, updateTreatment, updateToothStatus } from '@/api';
import { palmerToFdi } from '@/utils/toothUtils';
import { showToast } from '@/shared/ui/Toast';

export const useTreatmentOperations = ({
    patientId,
    refetchHistory,
    refetchTeeth,
    setIsTreatmentModalOpen,
    setEditingTreatmentId,
    editingTreatmentId,
    selectedToothCondition
}) => {
    const { t } = useTranslation();

    const handleSaveTreatment = useCallback(async (data) => {
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

            const payload = {
                ...data,
                tooth_number: fdiToothNumber,
                patient_id: parseInt(patientId, 10)
            };

            // 1. Save Treatment
            if (editingTreatmentId) {
                await updateTreatment(editingTreatmentId, payload);
            } else {
                await createTreatment(payload);
            }

            // 2. Update Tooth Status if applicable
            if (data.tooth_number && selectedToothCondition) {
                try {
                    console.log("[DEBUG] Updating Tooth Status:", {
                        patientId,
                        tooth: data.tooth_number,
                        condition: selectedToothCondition
                    });

                    let fdiNumber = palmerToFdi(data.tooth_number);
                    console.log("[DEBUG] FDI Number:", fdiNumber);

                    if (fdiNumber) {
                        await updateToothStatus({
                            patient_id: parseInt(patientId, 10),
                            tooth_number: fdiNumber,
                            condition: selectedToothCondition
                        });
                        console.log("[DEBUG] Tooth status updated successfully");
                        await refetchTeeth(); // Await refetch
                    } else {
                        console.warn("[DEBUG] Failed to convert to FDI:", data.tooth_number);
                    }
                } catch (e) {
                    console.error("Failed to update tooth status", e);
                    showToast('error', t('patient_details.alerts.tooth_update_fail'));
                }
            }

            setIsTreatmentModalOpen(false);
            setEditingTreatmentId(null);
            refetchHistory();
            showToast('success', t('patient_details.alerts.treatment_save_success'));
        } catch (err) {
            console.error(err);
            const res = err.response?.data;
            const detail = res?.detail;
            const envelope = res?.error;
            const msg = envelope?.details?.message || envelope?.message || detail || res?.message;

            // SPECIAL HANDLING: If generic error, show alert. 
            // If "CONFIRM_OPEN_REQUIRED", rethrow so TreatmentModal can handle it.
            if (
                detail?.code === "CONFIRM_OPEN_REQUIRED" ||
                envelope?.details?.code === "CONFIRM_OPEN_REQUIRED" ||
                (typeof msg === 'string' && msg.includes('CONFIRM_OPEN_REQUIRED'))
            ) {
                throw err;
            }

            const finalMsg = typeof msg === 'object' ? JSON.stringify(msg) : (msg || t('patient_details.alerts.treatment_save_fail'));
            showToast('error', finalMsg);
        }
    }, [patientId, editingTreatmentId, refetchHistory, refetchTeeth, selectedToothCondition, setIsTreatmentModalOpen, setEditingTreatmentId, t]);

    return { handleSaveTreatment };
};
