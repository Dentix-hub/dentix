import React, { useState, useCallback, memo, Suspense, lazy, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import PatientInfoCard from '@/features/patients/PatientInfoCard';
import { useProcedures } from '@/shared/context/ProceduresContext';
import TreatmentModal from '@/shared/ui/modals/TreatmentModal';
import PrescriptionModal from '@/shared/ui/modals/PrescriptionModal';
import PaymentModal from '@/shared/ui/modals/PaymentModal';
import EditPatientModal from '@/features/patients/modals/EditPatientModal';
import { SkeletonBox, Breadcrumb, TabGroup } from '@/shared/ui';
import { useTranslation } from 'react-i18next';
import { useHotkeys } from 'react-hotkeys-hook';
// Hooks for lazy data loading
import {
    usePatient,
    usePatientTeeth,
    usePatientTreatments,
    usePatientPayments,
    usePatientAttachments,
    useInvalidatePatientData
} from '@/hooks/usePatientDetails';
import { useTreatmentOperations } from '@/features/patients/hooks/useTreatmentOperations';
import { Baby, User as X } from 'lucide-react';
import { toothToNumber, fdiToPalmer, getTodayStr, universalToPalmer } from '../utils/toothUtils';
import {
    updatePatient, createPayment, deleteTreatment, deletePayment,
    uploadAttachment, deleteAttachment,
    createPrescription
} from '../api';
import { toast } from '@/shared/ui';

// Lazy load tab components
const TreatmentHistory = lazy(() => import('@/features/patients/PatientTabs/TreatmentHistory'));
const PatientFiles = lazy(() => import('@/features/patients/PatientTabs/PatientFiles'));
const PatientBilling = lazy(() => import('@/features/patients/PatientTabs/PatientBilling'));
const LabOrdersTab = lazy(() => import('@/features/lab/LabOrdersTab'));
const PatientTimeline = lazy(() => import('@/features/patients/PatientTabs/PatientTimeline'));

// Tab skeleton component
const TabSkeleton = memo(() => (
    <div className="space-y-4 p-4">
        <SkeletonBox height="4rem" className="rounded-xl" />
        <SkeletonBox height="4rem" className="rounded-xl" />
        <SkeletonBox height="4rem" className="rounded-xl" />
    </div>
));
TabSkeleton.displayName = 'TabSkeleton';

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
PatientInfoSkeleton.displayName = 'PatientInfoSkeleton';

export default function PatientDetails() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const { id } = useParams();
    const [searchParams, setSearchParams] = useSearchParams();
    const initialTab = searchParams.get('tab') || 'chart';
    const [activeTab, setActiveTab] = useState(initialTab);

    // Sync tab changes to URL
    const handleTabChange = (tabId) => {
        setActiveTab(tabId);
        setSearchParams({ tab: tabId }, { replace: true });
    };

    // Cache procedures from context
    const { procedures } = useProcedures();

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
        activeTab === 'history' || activeTab === 'billing' || activeTab === 'timeline' // Also needed for timeline
    );
    const { data: payments = [], isLoading: paymentsLoading, refetch: refetchPayments } = usePatientPayments(
        id,
        activeTab === 'billing' || activeTab === 'timeline' // Also needed for timeline
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

    // === CUSTOM HOOK FOR TREATMENT OPERATIONS ===
    const { handleSaveTreatment } = useTreatmentOperations({
        patientId: id,
        refetchHistory,
        refetchTeeth,
        setIsTreatmentModalOpen,
        setEditingTreatmentId,
        editingTreatmentId,
        selectedToothCondition
    });

    // === HANDLERS ===
    const handleFileUpload = useCallback(async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
            await uploadAttachment(id, file);
            refetchAttachments();
        } catch (err) {
            toast.error(t('patient_details.alerts.upload_fail'));
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

    const handleSavePatient = useCallback(async (updatedData) => {
        try {
            await updatePatient(id, updatedData);
            setIsEditPatientOpen(false);
            refetchPatient();
            toast.success(t('patients.update_success'));
        } catch (err) {
            toast.error(t('common.error') + ': ' + (err.response?.data?.detail || err.message));
        }
    }, [id, refetchPatient, t]);

    const handleNewAppointment = useCallback(() => {
        navigate(`/appointments?patient_id=${id}`);
    }, [navigate, id]);

    const handleSavePayment = useCallback(async (data) => {
        try {
            await createPayment({ ...data, patient_id: parseInt(id, 10) });
            setIsPaymentModalOpen(false);
            refetchPayments();
        } catch (err) {
            toast.error(err.response?.data?.detail || t('patient_details.alerts.payment_save_fail'));
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
            toast.error(err.response?.data?.detail || t('patient_details.alerts.delete_treatment_fail'));
        }
    }, [refetchHistory, t]);

    const handleDeletePayment = useCallback(async (paymentId) => {
        if (!window.confirm(t('patient_details.alerts.delete_payment_confirm'))) return;
        try {
            await deletePayment(paymentId);
            refetchPayments();
        } catch (err) {
            toast.error(err.response?.data?.detail || t('patient_details.alerts.delete_payment_fail'));
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
            window.open(`/print/rx/${id}`, '_blank');
        } catch (err) {
            toast.error(err.response?.data?.detail || t('patient_details.alerts.rx_fail'));
        }
    }, [id, patient, navigate, t]);

    // === KEYBOARD SHORTCUTS ===
    useHotkeys('n', (e) => {
        e.preventDefault();
        handleNewAppointment();
    }, [handleNewAppointment]);

    useHotkeys('t', (e) => {
        e.preventDefault();
        setIsToothSelectModalOpen(true);
    });

    useHotkeys('e', (e) => {
        e.preventDefault();
        setIsEditPatientOpen(true);
    });

    return (
        <div className="space-y-6 p-4 md:p-6">
            {!patientIsError && !patientLoading && patient && (
                <Breadcrumb items={[
                    { label: t('sidebar.patients'), to: '/patients' },
                    { label: patient.name }
                ]} />
            )}
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
            {/* Content Cards */}
            <div className="bg-surface border border-border rounded-2xl p-6 shadow-sm min-h-[600px]">
                {/* Tabs */}
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

                {/* Tab Content */}
                <div className="mt-8">
                    <Suspense fallback={<TabSkeleton />}>
                        {activeTab === 'chart' && (
                            <div className="space-y-4">
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

                        {activeTab === 'timeline' && (
                            <PatientTimeline 
                                history={history} 
                                payments={payments} 
                                t={t} 
                            />
                        )}

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

                        {activeTab === 'labs' && (
                            <LabOrdersTab patientId={id} />
                        )}
                    </Suspense>
                </div>
            </div>

            {/* Edit Patient Modal */}
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

            {isToothSelectModalOpen && (
                <div 
                    className="fixed inset-0 flex items-center justify-center p-4 z-[60]"
                    onClick={(e) => e.target === e.currentTarget && setIsToothSelectModalOpen(false)}
                >
                    <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
                    <div className="bg-surface border border-border rounded-2xl p-6 shadow-2xl relative overflow-y-auto max-h-[95vh] z-10 w-full max-w-lg">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-text-primary">
                                {t('patientDetails.chart.select_tooth')}
                            </h3>
                            <button 
                                onClick={() => setIsToothSelectModalOpen(false)}
                                className="p-2 hover:bg-surface-hover rounded-xl text-text-secondary transition-colors"
                            >
                                <X size={20} />
                            </button>
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
            )}
        </div>
    );
}

