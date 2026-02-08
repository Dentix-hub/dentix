import React, { useState, useCallback, memo, useMemo, Suspense, lazy, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import PatientInfoCard from '@/features/patients/PatientInfoCard';
import { useProcedures } from '@/shared/context/ProceduresContext';
import TreatmentModal from '@/shared/ui/modals/TreatmentModal';
import PrescriptionModal from '@/shared/ui/modals/PrescriptionModal';
import PaymentModal from '@/shared/ui/modals/PaymentModal';
import { Skeleton } from '@/shared/ui';
import { useTranslation } from 'react-i18next';

// Hooks for lazy data loading
import {
    usePatient,
    usePatientTeeth,
    usePatientTreatments,
    usePatientPayments,
    usePatientAttachments,
    useInvalidatePatientData
} from '@/hooks/usePatientDetails';

import { Baby, User as UserIcon, X } from 'lucide-react';
import { toothToNumber, palmerToFdi, fdiToPalmer, getTodayStr, universalToPalmer } from '../utils/toothUtils';
import { getToken } from '../utils';
import {
    updatePatient, updateToothStatus,
    createTreatment, createPayment, deleteTreatment, deletePayment,
    uploadAttachment, deleteAttachment, updateTreatment,
    createPrescription, getUsers
} from '../api';
import { consumeStock } from '@/api/inventory';
import { showToast } from '@/shared/ui/Toast';

// Lazy load tab components - only loaded when tab is active
const TreatmentHistory = lazy(() => import('@/features/patients/PatientTabs/TreatmentHistory'));
const PatientFiles = lazy(() => import('@/features/patients/PatientTabs/PatientFiles'));
const PatientBilling = lazy(() => import('@/features/patients/PatientTabs/PatientBilling'));
const LabOrdersTab = lazy(() => import('@/features/lab/LabOrdersTab'));

// Tab skeleton component
const TabSkeleton = memo(() => (
    <div className="space-y-4 p-4">
        <Skeleton.Box height="4rem" className="rounded-xl" />
        <Skeleton.Box height="4rem" className="rounded-xl" />
        <Skeleton.Box height="4rem" className="rounded-xl" />
    </div>
));

// Patient info skeleton
const PatientInfoSkeleton = memo(() => (
    <div className="bg-surface rounded-3xl p-6 border border-border animate-pulse">
        <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-slate-200 dark:bg-slate-700 rounded-2xl" />
            <div className="flex-1 space-y-2">
                <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-48" />
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-32" />
            </div>
        </div>
    </div>
));

// Price List Selector Component
const PriceListSelector = ({ value, onChange }) => {
    const { t } = useTranslation();
    const [lists, setLists] = useState([]);
    const [loading, setLoading] = useState(true);

    React.useEffect(() => {
        if (!getToken()) {
            setLoading(false);
            return;
        }
        import('@/api').then(({ getPriceLists }) => {
            getPriceLists()
                .then(res => {
                    setLists(res.data || []);
                })
                .catch(() => {
                    // 401 or other error: keep lists empty, user can still use "Default"
                    setLists([]);
                })
                .finally(() => setLoading(false));
        });
    }, []);

    if (loading) return <div className="text-sm text-gray-400">{t('common.loading')}</div>;

    const valueStr = value === null || value === undefined ? '' : String(value);
    return (
        <select
            value={valueStr}
            onChange={e => {
                const v = e.target.value;
                onChange(v ? parseInt(v, 10) : null);
            }}
            className="w-full p-3 bg-white rounded-xl outline-none border border-gray-200 focus:border-blue-500"
        >
            <option value="">{t('patient_details.edit_modal.default_option')}</option>
            {Array.isArray(lists) && lists.map(l => (
                <option key={l.id} value={String(l.id)}>
                    {l.name} {l.type === 'insurance' ? t('patient_details.edit_modal.insurance_tag') : ''}
                </option>
            ))}
        </select>
    );
};

export default function PatientDetails() {
    const { t } = useTranslation();
    const { id } = useParams();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('chart');

    // Cache procedures from context
    const { procedures } = useProcedures();

    // Invalidation helper
    const invalidateData = useInvalidatePatientData();

    // Feature Toggle
    const [isPediatric, setIsPediatric] = useState(false);

    // === LAZY DATA LOADING ===
    // Patient core data - loads immediately
    const { data: patient, isLoading: patientLoading, isError: patientIsError, error: patientError, refetch: refetchPatient } = usePatient(id);

    // Teeth data - loads for chart tab (default)
    const { data: teethStatus = {}, isLoading: teethLoading, refetch: refetchTeeth } = usePatientTeeth(id, true);

    // Tab-specific data - only loads when tab is active
    const { data: history = [], isLoading: historyLoading, refetch: refetchHistory } = usePatientTreatments(
        id,
        activeTab === 'history' || activeTab === 'billing' // Also needed for billing calculations
    );

    const { data: payments = [], isLoading: paymentsLoading, refetch: refetchPayments } = usePatientPayments(
        id,
        activeTab === 'billing'
    );

    const { data: attachments = [], isLoading: attachmentsLoading, refetch: refetchAttachments } = usePatientAttachments(
        id,
        activeTab === 'files'
    );

    // Local state for teeth (to allow optimistic updates)
    const [localTeethStatus, setLocalTeethStatus] = useState(null);
    const effectiveTeethStatus = localTeethStatus ?? teethStatus;

    // Modals
    const [isEditPatientOpen, setIsEditPatientOpen] = useState(false);
    const [isRxModalOpen, setIsRxModalOpen] = useState(false);
    const [isTreatmentModalOpen, setIsTreatmentModalOpen] = useState(false);
    const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
    const [isToothSelectModalOpen, setIsToothSelectModalOpen] = useState(false);

    const getInitialTreatment = () => ({
        date: getTodayStr(), diagnosis: '', procedure: '', cost: '', discount: '',
        tooth_number: '', canal_count: '', canals: [{ name: '', length: '' }],
        sessions: '', complications: '', notes: ''
    });

    const [newTreatment, setNewTreatment] = useState(getInitialTreatment());
    const [editingTreatmentId, setEditingTreatmentId] = useState(null);
    const [selectedToothCondition, setSelectedToothCondition] = useState('Healthy');
    const [doctors, setDoctors] = useState([]);

    // Fetch doctors for the edit modal
    useEffect(() => {
        if (isEditPatientOpen) {
            getUsers({ role: 'doctor' })
                .then(res => setDoctors(res.data))
                .catch(err => console.error("Failed to fetch doctors", err));
        }
    }, [isEditPatientOpen]);

    // === HANDLERS ===
    const handleFileUpload = useCallback(async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        try {
            await uploadAttachment(id, file);
            refetchAttachments();
        } catch (err) {
            showToast('error', t('patient_details.alerts.upload_fail'));
        }
    }, [id, refetchAttachments, t]);

    const handleDeleteAttachment = useCallback(async (attachmentId) => {
        if (!confirm('Delete this file?')) return;
        try {
            await deleteAttachment(attachmentId);
            refetchAttachments();
        } catch (err) {
            // Silent error
        }
    }, [refetchAttachments]);

    const handleToothClick = useCallback((number) => {
        const fdi = toothToNumber(number);
        const current = effectiveTeethStatus[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);
        const palmerPrefix = universalToPalmer(number, isPediatric);
        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: palmerPrefix,
            default_price_list_id: patient?.default_price_list_id // Inject default price list
        });
        setIsTreatmentModalOpen(true);
    }, [effectiveTeethStatus, isPediatric, patient]);


    // Form Data State
    const [formData, setFormData] = useState({});

    useEffect(() => {
        if (isEditPatientOpen && patient) {
            setFormData({
                name: patient.name,
                age: patient.age,
                phone: patient.phone,
                address: patient.address,
                default_price_list_id: patient.default_price_list_id,
                assigned_doctor_id: patient.assigned_doctor_id
            });
        }
    }, [isEditPatientOpen, patient]);

    const handleSavePatient = useCallback(async (e) => {
        e.preventDefault();
        try {
            await updatePatient(id, formData);
            setIsEditPatientOpen(false);
            refetchPatient();
        } catch (err) {
            showToast('error', t('common.error') + ': ' + (err.response?.data?.detail || err.message));
        }
    }, [id, formData, refetchPatient, t]);
    const handleNewAppointment = useCallback(() => {
        navigate(`/appointments?patient_id=${id}`);
    }, [navigate, id]);

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
                patient_id: parseInt(id, 10)
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
                        patientId: id,
                        tooth: data.tooth_number,
                        condition: selectedToothCondition
                    });

                    // Start of Fix: Ensure we convert Palmer/Display string back to Internal FDI Integer
                    let fdiNumber = palmerToFdi(data.tooth_number);
                    console.log("[DEBUG] FDI Number:", fdiNumber);

                    if (fdiNumber) {
                        await updateToothStatus({
                            patient_id: parseInt(id, 10),
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
    }, [id, editingTreatmentId, refetchHistory, refetchTeeth, selectedToothCondition, t]);

    const handleSavePayment = useCallback(async (data) => {
        try {
            await createPayment({ ...data, patient_id: parseInt(id, 10) });
            setIsPaymentModalOpen(false);
            setIsPaymentModalOpen(false);
            refetchPayments();
        } catch (err) {
            showToast('error', err.response?.data?.detail || t('patient_details.alerts.payment_save_fail'));
        }
    }, [id, refetchPayments, t]);

    const openManualTreatment = useCallback(() => {
        setEditingTreatmentId(null);
        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: '',
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
        } catch { /* ignore */ }

        setNewTreatment({
            date: item.date ? new Date(item.date).toLocaleDateString('en-CA') : getTodayStr(),
            diagnosis: item.diagnosis || '',
            procedure: item.procedure || '',
            cost: item.cost ?? '',
            discount: item.discount ?? '',
            tooth_number: item.tooth_number ? fdiToPalmer(item.tooth_number) : '',
            canal_count: item.canal_count ?? '',
            canals,
            sessions: item.sessions || '',
            complications: item.complications || '',
            notes: item.notes || '',
            default_price_list_id: patient?.default_price_list_id
        });
        setIsTreatmentModalOpen(true);
    }, [patient]);

    const handleDeleteTreatment = useCallback(async (treatmentId) => {
        if (!window.confirm(t('patient_details.alerts.delete_treatment_confirm'))) return;
        try {
            await deleteTreatment(treatmentId);
            refetchHistory();
        } catch (err) {
            showToast('error', err.response?.data?.detail || t('patient_details.alerts.delete_treatment_fail'));
        }
    }, [refetchHistory, t]);

    const handleDeletePayment = useCallback(async (paymentId) => {
        if (!window.confirm(t('patient_details.alerts.delete_payment_confirm'))) return;
        try {
            await deletePayment(paymentId);
            refetchPayments();
        } catch (err) {
            showToast('error', err.response?.data?.detail || t('patient_details.alerts.delete_payment_fail'));
        }
    }, [refetchPayments, t]);

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
            sessionStorage.setItem('print_rx_data', JSON.stringify({
                patient,
                prescription: res.data
            }));
            setIsRxModalOpen(false);
            navigate(`/print/rx/${id}`);
            setIsRxModalOpen(false);
            navigate(`/print/rx/${id}`);
        } catch (err) {
            showToast('error', err.response?.data?.detail || t('patient_details.alerts.rx_fail'));
        }
    }, [id, patient, navigate, t]);

    return (
        <div className="space-y-6 p-4 md:p-6">
            {patientIsError ? (
                <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-700">
                    <div className="font-bold mb-1">{t('patient_details.loading_error')}</div>
                    <div className="text-sm">
                        {patientError?.response?.data?.detail || patientError?.message || t('patient_details.unknown_error')}
                    </div>
                    <div className="mt-3 flex gap-2">
                        <button
                            onClick={() => refetchPatient()}
                            className="px-4 py-2 bg-white border border-red-200 rounded-lg text-sm font-bold hover:bg-red-50"
                        >
                            {t('patient_details.retry')}
                        </button>
                        <button
                            onClick={() => navigate('/')}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-bold hover:bg-red-700"
                        >
                            {t('patient_details.login')}
                        </button>
                    </div>
                </div>
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
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 text-slate-700">
                    {t('patient_details.no_data')}
                </div>
            )}

            {/* Tabs */}
            <div className="bg-white rounded-2xl border border-slate-100 p-2 flex flex-wrap gap-2">
                {[
                    { id: 'chart', label: t('patient_details.tabs.chart') },
                    { id: 'history', label: t('patient_details.tabs.history') },
                    { id: 'files', label: t('patient_details.tabs.files') },
                    { id: 'billing', label: t('patient_details.tabs.billing') },
                    { id: 'labs', label: t('patient_details.tabs.labs') },
                ].map(t => (
                    <button
                        key={t.id}
                        onClick={() => setActiveTab(t.id)}
                        className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${activeTab === t.id ? 'bg-primary text-white shadow' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'chart' && (
                <div className="bg-white rounded-2xl border border-slate-100 p-4 space-y-4">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div>
                            <h3 className="font-bold text-slate-800">{t('patient_details.chart.title')}</h3>
                            <p className="text-xs text-slate-400">{t('patient_details.chart.subtitle')}</p>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setIsPediatric(v => !v)}
                                className={`px-4 py-2 rounded-xl text-sm font-bold border transition-colors ${isPediatric ? 'bg-amber-50 border-amber-200 text-amber-700' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
                                title={t('patient_details.chart.pediatric_mode')}
                            >
                                <Baby size={16} className="inline-block scale-x-[-1] ml-2 rtl:ml-0 rtl:mr-2" />
                                {isPediatric ? t('patient_details.chart.child') : t('patient_details.chart.adult')}
                            </button>
                            <button
                                onClick={() => setIsToothSelectModalOpen(true)}
                                className="px-4 py-2 rounded-xl text-sm font-bold bg-emerald-500 text-white hover:bg-emerald-600"
                            >
                                {t('patient_details.chart.new_treatment')}
                            </button>
                        </div>
                    </div>

                    {teethLoading ? (
                        <TabSkeleton />
                    ) : (
                        <DentalChartSVG
                            teethStatus={effectiveTeethStatus}
                            onToothClick={handleToothClick}
                            isPediatric={isPediatric}
                        />
                    )}
                </div>
            )}

            {activeTab === 'history' && (
                <Suspense fallback={<TabSkeleton />}>
                    <TreatmentHistory
                        history={history}
                        onAdd={openManualTreatment}
                        onEdit={handleEditTreatment}
                        onDelete={handleDeleteTreatment}
                    />
                </Suspense>
            )}

            {activeTab === 'files' && (
                <Suspense fallback={<TabSkeleton />}>
                    <PatientFiles
                        attachments={attachments}
                        handleFileUpload={handleFileUpload}
                        handleDeleteAttachment={handleDeleteAttachment}
                        loading={attachmentsLoading}
                        reloadAttachments={refetchAttachments}
                    />
                </Suspense>
            )}

            {activeTab === 'billing' && (
                <Suspense fallback={<TabSkeleton />}>
                    <PatientBilling
                        patientId={id}
                        history={history}
                        payments={payments}
                        onAddPayment={() => setIsPaymentModalOpen(true)}
                        onDeletePayment={handleDeletePayment}
                        onPrintInvoice={handlePrintInvoice}
                    />
                </Suspense>
            )}

            {activeTab === 'labs' && (
                <Suspense fallback={<TabSkeleton />}>
                    <LabOrdersTab patientId={id} />
                </Suspense>
            )}

            {/* Edit Patient Modal */}
            {
                isEditPatientOpen && (
                    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                        <div className="bg-white w-full max-w-lg rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                            <h3 className="text-xl font-bold mb-4">{t('patient_details.edit_modal.title')}</h3>
                            <form onSubmit={handleSavePatient} className="space-y-4">
                                <input value={formData.name || ''} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary" placeholder={t('patients.form.name_label')} />
                                <div className="grid grid-cols-2 gap-4">
                                    <input value={formData.age || ''} onChange={(e) => setFormData({ ...formData, age: e.target.value })} className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary" placeholder={t('patients.form.age_label')} />
                                    <input value={formData.phone || ''} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary" placeholder={t('patients.form.phone_label')} />
                                </div>
                                <input value={formData.address || ''} onChange={(e) => setFormData({ ...formData, address: e.target.value })} className="w-full p-3 bg-slate-50 rounded-xl outline-none border focus:border-primary" placeholder={t('patients.form.address_label')} />

                                {/* Price List Selector */}
                                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                                    <label className="block text-sm font-bold text-slate-700 mb-2">{t('patient_details.edit_modal.price_list_label')}</label>
                                    <PriceListSelector
                                        value={formData.default_price_list_id ?? ''}
                                        onChange={(val) => setFormData(prev => ({ ...prev, default_price_list_id: val }))}
                                    />
                                    <p className="text-xs text-slate-400 mt-1">{t('patient_details.edit_modal.price_list_hint')}</p>
                                </div>

                                {/* Doctor Assignment */}
                                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                                    <label className="block text-sm font-bold text-slate-700 mb-2">{t('patient_details.edit_modal.doctor_label')}</label>
                                    <select
                                        value={formData.assigned_doctor_id || ''}
                                        onChange={(e) => setFormData({ ...formData, assigned_doctor_id: e.target.value })}
                                        className="w-full p-3 bg-white rounded-xl outline-none border border-gray-200 focus:border-blue-500"
                                    >
                                        <option value="">{t('patient_details.edit_modal.doctor_select')}</option>
                                        {doctors.map(doc => (
                                            <option key={doc.id} value={doc.id}>
                                                د. {doc.username}
                                            </option>
                                        ))}
                                    </select>
                                    <p className="text-xs text-slate-400 mt-1">{t('patient_details.edit_modal.doctor_hint')}</p>
                                </div>

                                <div className="flex justify-end gap-3"><button type="button" onClick={() => setIsEditPatientOpen(false)} className="px-4 py-2 hover:bg-slate-100 rounded-lg">{t('common.cancel')}</button><button type="submit" className="px-6 py-2 bg-primary text-white rounded-lg">{t('common.save')}</button></div>
                            </form>
                        </div>
                    </div >
                )
            }

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

            {
                isToothSelectModalOpen && (
                    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4 backdrop-blur-md">
                        <div className="bg-white w-full max-w-4xl rounded-3xl p-6 shadow-2xl overflow-y-auto max-h-[95vh]">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-2xl font-bold text-slate-800">{t('patient_details.chart.tooth_modal_title')}</h3>
                                <button onClick={() => setIsToothSelectModalOpen(false)} className="p-2 hover:bg-slate-100 rounded-full"><X /></button>
                            </div>
                            <div className="mb-8">
                                <DentalChartSVG
                                    teethStatus={effectiveTeethStatus}
                                    onToothClick={(num) => {
                                        handleToothClick(num);
                                        setIsToothSelectModalOpen(false);
                                    }}
                                    isPediatric={isPediatric}
                                />
                            </div>
                            <div className="flex justify-center gap-4">
                                <button
                                    onClick={() => {
                                        setNewTreatment({
                                            ...getInitialTreatment(),
                                            tooth_number: '',
                                            default_price_list_id: patient?.default_price_list_id
                                        });
                                        setIsTreatmentModalOpen(true);
                                        setIsToothSelectModalOpen(false);
                                    }}
                                    className="px-8 py-3 bg-slate-100 text-slate-600 font-bold rounded-xl hover:bg-slate-200 transition-all"
                                >
                                    {t('patient_details.chart.continue_no_tooth')}
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
}
