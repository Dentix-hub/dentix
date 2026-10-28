import { useCallback, useContext } from 'react';
import { QueryClientContext } from '@tanstack/react-query';
import { invalidatePatientClinicalQueries } from '../utils/invalidatePatientClinicalQueries';
import { toast } from '@/shared/ui';
import { fdiToPalmer, getTodayStr } from '@/utils/toothUtils';
import {
    updatePatient,
    deleteTreatment,
    uploadAttachment,
    deleteAttachment,
    createPrescription,
    updatePatientClinicalWorkItem,
} from '@/api';

export function usePatientRecordActions({
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
}) {
    const queryClient = useContext(QueryClientContext);

    const handleFileUpload = useCallback(async (event) => {
        const file = event.target?.files?.[0];
        if (!file) return;
        try {
            await uploadAttachment(id, file);
            refetchAttachments();
            queryClient?.invalidateQueries?.({ queryKey: ['patient', id, 'attachments'] });
        } catch (error) {
            const detail = error?.response?.data?.detail;
            const message = error?.response?.data?.message;
            let displayMessage = t('patient_details.alerts.upload_fail');

            if (typeof detail === 'string' && detail.trim()) {
                displayMessage = detail.trim();
            } else if (Array.isArray(detail) && detail[0]?.msg) {
                displayMessage = detail[0].msg;
            } else if (typeof message === 'string' && message.trim()) {
                displayMessage = message.trim();
            }

            toast.error(displayMessage);
        } finally {
            if (event.target) {
                event.target.value = '';
            }
        }
    }, [id, refetchAttachments, t]);

    const handleDeleteAttachment = useCallback(async (attachmentId) => {
        if (!window.confirm('Delete this file?')) return;
        try {
            await deleteAttachment(attachmentId);
            refetchAttachments();
            queryClient?.invalidateQueries?.({ queryKey: ['patient', id, 'attachments'] });
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
    }, [id, refetchPatient, setIsEditPatientOpen, t]);

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
    }, [id, createPaymentMutate, setIsPaymentModalOpen, t]);

    const openManualTreatment = useCallback(() => {
        setEditingTreatmentId(null);
        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: '',
            surface: '',
            surfaces: [],
            target_kind: 'tooth',
            default_price_list_id: patient?.default_price_list_id,
        });
        setIsTreatmentSheetOpen(true);
    }, [patient, setEditingTreatmentId, setNewTreatment, getInitialTreatment, setIsTreatmentSheetOpen]);

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
            treatment_sessions: item.treatment_sessions || [],
            default_price_list_id: patient?.default_price_list_id,
        });
        setIsTreatmentSheetOpen(true);
    }, [patient, setEditingTreatmentId, setNewTreatment, setIsTreatmentSheetOpen]);

    const handleDeleteTreatment = useCallback(async (treatmentId) => {
        if (!window.confirm(t('patient_details.alerts.delete_treatment_confirm'))) return;
        try {
            await deleteTreatment(treatmentId);
            await Promise.all([refetchHistory(), refetchWorkspace()]);
            invalidatePatientClinicalQueries(queryClient, id);
            toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.delete_treatment_fail'));
        }
    }, [refetchHistory, refetchWorkspace, t, queryClient, id]);

    const handleRemoveWorkItemOrTreatment = useCallback(async (item) => {
        try {
            if (item.sourceType === 'treatment' || (!item.sourceType && item.treatment_id)) {
                await deleteTreatment(item.id);
                await Promise.all([refetchHistory(), refetchWorkspace()]);
                invalidatePatientClinicalQueries(queryClient, id);
                toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
            } else {
                const workItemId = item.id;
                if (workItemId && !String(workItemId).startsWith('ve-')) {
                    await updatePatientClinicalWorkItem(id, workItemId, { status: 'cancelled' });
                }
                await refetchWorkspace();
                invalidatePatientClinicalQueries(queryClient, id);
                toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
            }
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.delete_treatment_fail', 'Failed to remove item'));
        }
    }, [id, refetchHistory, refetchWorkspace, t, queryClient]);

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
                notes: notes || '',
            };
            const res = await createPrescription(payload);
            // Print route carries the real prescription id; no PHI in sessionStorage.
            setIsRxModalOpen(false);
            window.open(`/print/rx/${res.data?.id}`, '_blank');
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.rx_fail'));
        }
    }, [id, setIsRxModalOpen, t]);

    return {
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
    };
}
