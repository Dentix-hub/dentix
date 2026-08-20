import { lazy, memo, Suspense, useCallback, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
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
    usePatientTreatments,
    usePatientPayments,
    usePatientAttachments,
    useCreatePayment,
    useDeletePayment
} from '@/hooks/usePatientDetails';
import { useTreatmentOperations } from '@/features/patients/hooks/useTreatmentOperations';
import { Baby } from 'lucide-react';
import { toothToNumber, fdiToPalmer, getTodayStr, universalToPalmer } from '../utils/toothUtils';
import {
    updatePatient,
    deleteTreatment,
    uploadAttachment,
    deleteAttachment,
    createPrescription
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
    const { t } = useTranslation();
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

    const {
        data: patient,
        isLoading: patientLoading,
        isError: patientIsError,
        error: patientError,
        refetch: refetchPatient
    } = usePatient(id);
    const { data: teethStatus = {}, isLoading: teethLoading, refetch: refetchTeeth } = usePatientTeeth(id, true);
    const { data: history = [], refetch: refetchHistory } = usePatientTreatments(
        id,
        activeTab === 'history' || activeTab === 'billing' || activeTab === 'timeline'
    );
    const { data: payments = [] } = usePatientPayments(
        id,
        activeTab === 'billing' || activeTab === 'timeline'
    );
    const {
        data: attachments = [],
        isLoading: attachmentsLoading,
        refetch: refetchAttachments
    } = usePatientAttachments(id, activeTab === 'files');

    const [localTeethStatus] = useState(null);
    const effectiveTeethStatus = localTeethStatus ?? teethStatus;

    const [isEditPatientOpen, setIsEditPatientOpen] = useState(false);
    const [isRxModalOpen, setIsRxModalOpen] = useState(false);
    const [isTreatmentModalOpen, setIsTreatmentModalOpen] = useState(false);
    const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
    const [isToothSelectModalOpen, setIsToothSelectModalOpen] = useState(false);

    const getInitialTreatment = () => ({
        date: getTodayStr(),
        diagnosis: '',
        procedure: '',
        cost: '',
        discount: '',
        tooth_number: '',
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

    const { handleSaveTreatment } = useTreatmentOperations({
        patientId: id,
        refetchHistory,
        refetchTeeth,
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

    const handleToothClick = useCallback((number) => {
        const fdi = toothToNumber(number);
        const current = effectiveTeethStatus[fdi]?.condition || 'Healthy';
        setSelectedToothCondition(current);
        const palmerPrefix = universalToPalmer(number, isPediatric);
        setNewTreatment({
            ...getInitialTreatment(),
            tooth_number: palmerPrefix,
            default_price_list_id: patient?.default_price_list_id
        });
        setIsTreatmentModalOpen(true);
    }, [effectiveTeethStatus, isPediatric, patient]);

    const handleSavePatient = useCallback(async (updatedData) => {
        try {
            await updatePatient(id, updatedData);
            setIsEditPatientOpen(false);
            refetchPatient();
            toast.success(t('patients.update_success'));
        } catch (error) {
            toast.error(`${t('common.error')}: ${error.response?.data?.detail || error.message}`);
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
            refetchHistory();
            toast.success(t('common.delete_success', 'تم الحذف بنجاح'));
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.delete_treatment_fail'));
        }
    }, [refetchHistory, t]);

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
            sessionStorage.setItem('print_rx_data', JSON.stringify({ patient, prescription: res.data }));
            setIsRxModalOpen(false);
            window.open(`/print/rx/${id}`, '_blank');
        } catch (error) {
            toast.error(error.response?.data?.detail || t('patient_details.alerts.rx_fail'));
        }
    }, [id, patient, t]);

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
                                        <h3 className="break-words font-bold text-slate-800 dark:text-white">{t('patient_details.chart.title')}</h3>
                                        <p className="mt-1 break-words text-xs text-slate-500 dark:text-slate-400">{t('patient_details.chart.subtitle')}</p>
                                    </div>
                                    <div className="grid w-full grid-cols-1 gap-2 min-[400px]:grid-cols-2 md:w-auto">
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
                                            onClick={() => setIsToothSelectModalOpen(true)}
                                            className="min-h-11 rounded-xl bg-emerald-500 px-3 py-2 text-sm font-bold text-white transition-colors hover:bg-emerald-600"
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
                    <DentalChartSVG
                        teethStatus={effectiveTeethStatus}
                        onToothClick={(number) => {
                            handleToothClick(number);
                            setIsToothSelectModalOpen(false);
                        }}
                        isPediatric={isPediatric}
                    />
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
