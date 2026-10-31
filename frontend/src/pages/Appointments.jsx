import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import {
    DndContext,
    DragOverlay,
    closestCorners,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors
} from '@dnd-kit/core';
import {
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
    Calendar,
    Clock,
    Plus,
    User,
    CheckCircle,
    XCircle,
    Trash2,
    LayoutGrid,
    List as ListIcon,
    Home,
    GripVertical,
    StickyNote,
    Edit2,
    CalendarClock
} from 'lucide-react';
import { createAppointment, deleteAppointment, updateAppointmentStatus } from '@/api';
import { getDoctors } from '@/api/admin';
import {
    useAppointments,
    useUpdateAppointmentStatus,
    useUpdateAppointment,
    useNextVisitRequests,
    useScheduleNextVisitRequest,
    useCancelNextVisitRequest
} from '@/hooks/useAppointments';
import NextVisitQueue from '@/features/appointments/components/NextVisitQueue';
import { usePatients, useCreatePatient } from '@/hooks/usePatients';
import { getTodayDateTimeStr } from '@/utils/toothUtils';
import { getDateInTimeZone, selectAppointmentsForBusinessDate } from '@/utils/dateTime';
import {
    Button,
    Input,
    Modal,
    Badge,
    SkeletonBox,
    EmptyState,
    toast,
    ConfirmDialog,
    PageHeader,
    PatientSelect,
    StatCard,
    DateTimePicker
} from '@/shared/ui';
import WeeklyCalendar from '@/shared/ui/WeeklyCalendar';
import { useAuth } from '@/auth/useAuth';
import { useTenantStore } from '@/store/tenant.store';

const STATUS_OPTIONS = [
    'Scheduled',
    'Waiting',
    'In-Chair',
    'Completed',
    'Postponed',
    'No Show',
    'Cancelled'
];

const getInitialViewMode = () => {
    if (typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches) return 'list';
    return 'calendar';
};

export default function Appointments() {
    const { user } = useAuth();
    const tenantTimezone = useTenantStore((state) => state.tenant?.timezone);
    const [searchParams, setSearchParams] = useSearchParams();
    const { t, i18n } = useTranslation();
    const preselectPatientId = searchParams.get('patient_id');
    // Command palette links use ?action=new or ?id=<patientId>
    const openNewAction = searchParams.get('action') === 'new';
    const commandPalettePatientId = preselectPatientId || searchParams.get('id');
    const [viewMode, setViewMode] = useState(getInitialViewMode);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState({ open: false, id: null });
    const [activeRequestId, setActiveRequestId] = useState(null);
    const [newAppt, setNewAppt] = useState({
        patient_id: '',
        date_time: getTodayDateTimeStr(),
        notes: '',
        doctor_id: user?.role === 'doctor' ? user.id : '',
        duration_minutes: 30
    });
    const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
    const [quickPatient, setQuickPatient] = useState({ name: '', phone: '' });

    useEffect(() => {
        if (preselectPatientId) {
            setNewAppt(prev => ({ ...prev, patient_id: preselectPatientId }));
            setIsModalOpen(true);
            setSearchParams({}, { replace: true });
        } else if (commandPalettePatientId || openNewAction) {
            // Support /appointments?id=<patientId> and /appointments?action=new
            // links emitted by the Command Palette.
            if (commandPalettePatientId) {
                setNewAppt(prev => ({ ...prev, patient_id: commandPalettePatientId }));
            }
            setIsModalOpen(true);
            setSearchParams({}, { replace: true });
        }
    }, [preselectPatientId, commandPalettePatientId, openNewAction, setSearchParams]);

    useEffect(() => {
        if (user?.id && !newAppt.doctor_id && user.role === 'doctor') {
            setNewAppt(prev => ({ ...prev, doctor_id: user.id }));
        }
    }, [user, newAppt.doctor_id]);

    const { data: appointments = [], isLoading: apptsLoading, refetch: refetchAppointments } = useAppointments();
    const { data: patients = [], isLoading: patientsLoading, refetch: refetchPatients } = usePatients();
    const { data: nextVisitRequests = [], isLoading: nvrLoading } = useNextVisitRequests({ status: 'all' });
    const updateMutation = useUpdateAppointment();
    const createPatientMutation = useCreatePatient();
    const scheduleRequestMutation = useScheduleNextVisitRequest();
    const cancelRequestMutation = useCancelNextVisitRequest();
    const loading = apptsLoading || patientsLoading;

    const [doctors, setDoctors] = useState([]);

    useEffect(() => {
        let active = true;
        getDoctors()
            .then((res) => {
                if (active) {
                    setDoctors(res?.data?.doctors || res?.data || []);
                }
            })
            .catch(() => {});
        return () => {
            active = false;
        };
    }, []);

    const [editModal, setEditModal] = useState({
        open: false,
        appt: null,
        date_time: '',
        duration_minutes: 30,
        doctor_id: '',
        notes: ''
    });

    const [postponeModal, setPostponeModal] = useState({
        open: false,
        appt: null,
        date_time: ''
    });

    const handleOpenEdit = useCallback((appt) => {
        setEditModal({
            open: true,
            appt,
            date_time: appt.date_time ? appt.date_time.substring(0, 16) : '',
            duration_minutes: appt.duration_minutes || 30,
            doctor_id: appt.doctor_id ? appt.doctor_id.toString() : '',
            notes: appt.notes || ''
        });
    }, []);

    const handleUpdateAppointment = async () => {
        if (!editModal.appt) return;
        const toastId = toast.loading(t('appointments.messages.updating'));
        try {
            const formattedDate = editModal.date_time ? editModal.date_time.substring(0, 19) : undefined;
            const payload = {
                date_time: formattedDate,
                duration_minutes: editModal.duration_minutes ? parseInt(editModal.duration_minutes, 10) : 30,
                doctor_id: editModal.doctor_id ? parseInt(editModal.doctor_id, 10) : null,
                notes: editModal.notes || ''
            };
            await updateMutation.mutateAsync({ id: editModal.appt.id, data: payload });
            toast.success(t('appointments.messages.update_success'), { id: toastId });
            setEditModal({ open: false, appt: null, date_time: '', duration_minutes: 30, doctor_id: '', notes: '' });
            refetchAppointments();
        } catch (err) {
            const errorMsg = err.response?.data?.detail || t('appointments.messages.update_error');
            toast.error(errorMsg, { id: toastId });
        }
    };

    const handleOpenPostpone = useCallback((appt) => {
        setPostponeModal({
            open: true,
            appt,
            date_time: ''
        });
    }, []);

    const handleConfirmPostpone = async () => {
        if (!postponeModal.appt) return;
        const toastId = toast.loading(t('appointments.messages.updating'));
        try {
            const payload = {
                status: 'Postponed',
                ...(postponeModal.date_time ? { date_time: postponeModal.date_time.substring(0, 19) } : {})
            };
            await updateMutation.mutateAsync({ id: postponeModal.appt.id, data: payload });
            toast.success(t('appointments.messages.update_success'), { id: toastId });
            setPostponeModal({ open: false, appt: null, date_time: '' });
            refetchAppointments();
        } catch (err) {
            const errorMsg = err.response?.data?.detail || t('appointments.messages.update_error');
            toast.error(errorMsg, { id: toastId });
        }
    };

    const handleScheduleRequest = useCallback((request) => {
        setActiveRequestId(request.id);
        const preferredDate = request.preferred_time_window_start
            ? new Date(request.preferred_time_window_start).toISOString().substring(0, 16)
            : getTodayDateTimeStr();

        setNewAppt({
            patient_id: request.patient_id.toString(),
            date_time: preferredDate,
            notes: request.reason || '',
            doctor_id: user?.role === 'doctor' ? user.id : '',
            duration_minutes: request.suggested_duration_minutes || 30
        });
        setIsModalOpen(true);
    }, [user]);

    const handleDismissRequest = useCallback(async (request) => {
        const toastId = toast.loading(t('common.processing', 'Processing...'));
        try {
            await cancelRequestMutation.mutateAsync({
                requestId: request.id,
                data: { reason: 'Dismissed from reception triage' }
            });
            toast.success(t('appointments.request_dismissed', 'Next-visit request dismissed'), { id: toastId });
        } catch {
            toast.error(t('common.error_occurred', 'Failed to dismiss request'), { id: toastId });
        }
    }, [cancelRequestMutation, t]);

    const handleCreate = useCallback(async () => {
        if (!newAppt.patient_id || !newAppt.date_time) {
            toast.error(t('appointments.messages.fill_all'));
            return;
        }
        const toastId = toast.loading(t('appointments.messages.booking'));
        try {
            if (activeRequestId) {
                await scheduleRequestMutation.mutateAsync({
                    requestId: activeRequestId,
                    data: {
                        date_time: newAppt.date_time,
                        doctor_id: newAppt.doctor_id ? parseInt(newAppt.doctor_id, 10) : null,
                        duration_minutes: newAppt.duration_minutes || 30,
                        price_list_id: newAppt.price_list_id ? parseInt(newAppt.price_list_id, 10) : null,
                        notes: newAppt.notes,
                    }
                });
            } else {
                const payload = {
                    ...newAppt,
                    patient_id: parseInt(newAppt.patient_id, 10),
                    doctor_id: newAppt.doctor_id ? parseInt(newAppt.doctor_id, 10) : null,
                    price_list_id: newAppt.price_list_id ? parseInt(newAppt.price_list_id, 10) : null
                };
                await createAppointment(payload);
            }
            setIsModalOpen(false);
            setActiveRequestId(null);
            setNewAppt({
                patient_id: '',
                date_time: getTodayDateTimeStr(),
                notes: '',
                doctor_id: user?.role === 'doctor' ? user.id : '',
                duration_minutes: 30
            });
            refetchAppointments();
            toast.success(t('appointments.messages.booking_success'), { id: toastId });
        } catch {
            toast.error(t('appointments.messages.booking_error'), { id: toastId });
        }
    }, [activeRequestId, newAppt, refetchAppointments, scheduleRequestMutation, t, user]);

    const handleEventDrop = async (id, newDateTime) => {
        const toastId = toast.loading(t('appointments.messages.updating'));
        try {
            const formattedDate = newDateTime.substring(0, 19);
            await updateMutation.mutateAsync({ id, data: { date_time: formattedDate } });
            toast.success(t('appointments.messages.update_success'), { id: toastId });
            refetchAppointments();
        } catch (err) {
            const errorMsg = err.response?.data?.detail || t('appointments.messages.update_error');
            toast.error(errorMsg, { id: toastId });
            refetchAppointments();
        }
    };

    const handleSelectSlot = (dateTime) => {
        setNewAppt(prev => ({ ...prev, date_time: dateTime.substring(0, 16) }));
        setIsModalOpen(true);
    };

    const handleQuickAdd = (query) => {
        setQuickPatient({ name: query, phone: '' });
        setIsQuickAddOpen(true);
    };

    const handleQuickCreatePatient = async () => {
        if (!quickPatient.name) {
            toast.error(t('patients.messages.name_required', 'Patient name is required'));
            return;
        }
        const toastId = toast.loading(t('patients.messages.creating', 'Creating patient...'));
        try {
            const res = await createPatientMutation.mutateAsync(quickPatient);
            const newPatientId = res.data.id;
            setNewAppt(prev => ({ ...prev, patient_id: newPatientId.toString() }));
            setIsQuickAddOpen(false);
            refetchPatients();
            toast.success(t('patients.messages.create_success', 'Patient created successfully'), { id: toastId });
        } catch (error) {
            const errorMsg = error.response?.data?.detail || t('patients.messages.create_error', 'Failed to create patient');
            toast.error(errorMsg, { id: toastId });
        }
    };

    const handleStatus = useCallback(async (id, status) => {
        const toastId = toast.loading(t('appointments.messages.updating'));
        try {
            await updateAppointmentStatus(id, status);
            refetchAppointments();
            toast.success(t('appointments.messages.update_success'), { id: toastId });
        } catch {
            toast.error(t('appointments.messages.update_error'), { id: toastId });
        }
    }, [refetchAppointments, t]);

    const handleDeleteConfirm = useCallback(async (id) => {
        const toastId = toast.loading(t('appointments.messages.deleting'));
        try {
            await deleteAppointment(id);
            refetchAppointments();
            toast.success(t('appointments.messages.delete_success'), { id: toastId });
            setConfirmDelete({ open: false, id: null });
        } catch {
            toast.error(t('appointments.messages.delete_error'), { id: toastId });
        }
    }, [refetchAppointments, t]);

    const columns = useMemo(() => [
        { id: 'Scheduled', title: t('appointments.status.scheduled'), icon: Calendar, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800' },
        { id: 'Waiting', title: t('appointments.status.waiting'), icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800' },
        { id: 'In-Chair', title: t('appointments.status.in_chair'), icon: User, color: 'text-teal-600', bg: 'bg-teal-50 dark:bg-teal-900/20', border: 'border-teal-200 dark:border-teal-800' },
        { id: 'Completed', title: t('appointments.status.completed'), icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-800' },
        { id: 'Cancelled', title: t('appointments.status.cancelled_noshow'), icon: XCircle, color: 'text-slate-600', bg: 'bg-slate-50 dark:bg-slate-800', border: 'border-slate-200 dark:border-slate-700' },
    ], [t]);

    const updateStatusMutation = useUpdateAppointmentStatus();
    const [activeId, setActiveId] = useState(null);
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    const handleDragStart = (event) => setActiveId(event.active.id);

    const handleDragEnd = useCallback(async (event) => {
        const { active, over } = event;
        setActiveId(null);
        if (!over) return;

        const appointmentId = active.id;
        let targetColumnId = over.id;
        const overAppt = appointments.find(a => a.id === targetColumnId);
        if (overAppt) targetColumnId = overAppt.status;
        if (['Cancelled', 'No Show'].includes(targetColumnId)) targetColumnId = 'Cancelled';

        const activeAppt = appointments.find(a => a.id === appointmentId);
        if (activeAppt && activeAppt.status !== targetColumnId && columns.find(c => c.id === targetColumnId)) {
            try {
                await updateStatusMutation.mutateAsync({ id: appointmentId, status: targetColumnId });
                toast.success(t('appointments.messages.update_success'));
            } catch {
                // Hook/API handling remains authoritative for mutation errors.
            }
        }
    }, [appointments, columns, t, updateStatusMutation]);

    const getColumnAppointments = (status) => status === 'Cancelled'
        ? appointments.filter(a => ['Cancelled', 'No Show'].includes(a.status))
        : appointments.filter(a => a.status === status);

    const getStatusVariant = (status) => {
        switch (status) {
            case 'Scheduled': return 'info';
            case 'Completed': return 'success';
            case 'Cancelled':
            case 'No Show': return 'danger';
            case 'Waiting': return 'warning';
            case 'In-Chair': return 'primary';
            default: return 'default';
        }
    };

    const getStatusLabel = (status) => {
        const labels = {
            Scheduled: t('appointments.status.scheduled'),
            Completed: t('appointments.status.completed'),
            Cancelled: t('appointments.status.cancelled'),
            Waiting: t('appointments.status.waiting'),
            'In-Chair': t('appointments.status.in_chair'),
            Postponed: t('appointments.status.postponed'),
            'No Show': t('appointments.status.no_show')
        };
        return labels[status] || status;
    };

    const formatAppointmentDateTime = (value) => new Date(value).toLocaleString(
        i18n.language === 'ar' ? 'ar-EG' : 'en-US',
        { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
    );

    const stats = useMemo(() => {
        const today = getDateInTimeZone(tenantTimezone);
        const todayAppts = selectAppointmentsForBusinessDate(appointments, today);
        return [
            { label: t('appointments.stats.today_total'), value: todayAppts.length, icon: Calendar, color: 'blue' },
            { label: t('appointments.stats.waiting'), value: appointments.filter(a => a.status === 'Waiting').length, icon: Clock, color: 'amber' },
            { label: t('appointments.stats.in_chair'), value: appointments.filter(a => a.status === 'In-Chair').length, icon: User, color: 'teal' },
            { label: t('appointments.stats.completed_today'), value: todayAppts.filter(a => a.status === 'Completed').length, icon: CheckCircle, color: 'emerald' },
        ];
    }, [appointments, t, tenantTimezone]);

    return (
        <div className="min-w-0 space-y-5 pb-8 animate-in fade-in slide-in-from-bottom-4 duration-700 sm:space-y-6 sm:pb-12 lg:space-y-8">
            <PageHeader
                title={t('appointments.title')}
                subtitle={t('appointments.subtitle')}
                breadcrumbs={[
                    { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                    { label: t('appointments.title') }
                ]}
                actions={
                    <>
                        <div className="flex min-h-11 w-full rounded-xl border border-border bg-surface p-1 sm:w-auto" role="group" aria-label={t('appointments.view.label', 'Appointment view')}>
                            <ViewButton active={viewMode === 'calendar'} onClick={() => setViewMode('calendar')} title={t('appointments.view.calendar')} icon={Calendar} />
                            <ViewButton active={viewMode === 'list'} onClick={() => setViewMode('list')} title={t('appointments.view.list')} icon={ListIcon} />
                            <ViewButton active={viewMode === 'board'} onClick={() => setViewMode('board')} title={t('appointments.view.board')} icon={LayoutGrid} />
                        </div>
                        <Button onClick={() => setIsModalOpen(true)} className="min-h-11 justify-center">
                            <Plus size={20} className="me-2" aria-hidden="true" />
                            {t('appointments.new_booking')}
                        </Button>
                    </>
                }
            />

            <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:gap-6">
                {stats.map((stat) => (
                    <StatCard
                        key={stat.label}
                        title={stat.label}
                        value={stat.value}
                        icon={stat.icon}
                        color={stat.color}
                    />
                ))}
            </div>

            <NextVisitQueue
                requests={nextVisitRequests}
                isLoading={nvrLoading}
                doctors={doctors}
                onSchedule={handleScheduleRequest}
                onDismiss={handleDismissRequest}
            />

            {loading ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-6">
                    <SkeletonBox className="h-72 w-full rounded-3xl md:h-96" />
                    <SkeletonBox className="h-72 w-full rounded-3xl md:h-96" />
                    <SkeletonBox className="h-72 w-full rounded-3xl md:h-96" />
                </div>
            ) : appointments.length === 0 ? (
                <EmptyState
                    title={t('appointments.no_appointments')}
                    description={t('appointments.no_appointments_desc')}
                    icon={Calendar}
                    action={<Button onClick={() => setIsModalOpen(true)}>{t('appointments.add_appointment')}</Button>}
                />
            ) : viewMode === 'calendar' ? (
                <div className="min-w-0 overflow-hidden rounded-2xl border border-border bg-surface-elevated sm:rounded-3xl">
                    <WeeklyCalendar
                        appointments={appointments}
                        onEventClick={(appt) => {
                            toast(`${t('appointments.table.patient')}: ${appt.patient_name}`, { icon: 'ℹ️' });
                        }}
                        onEventDrop={handleEventDrop}
                        onSelectSlot={handleSelectSlot}
                    />
                </div>
            ) : viewMode === 'list' ? (
                <AppointmentList
                    appointments={appointments}
                    patients={patients}
                    t={t}
                    formatAppointmentDateTime={formatAppointmentDateTime}
                    getStatusLabel={getStatusLabel}
                    getStatusVariant={getStatusVariant}
                    onStatusChange={handleStatus}
                    onDelete={(id) => setConfirmDelete({ open: true, id })}
                    onEdit={handleOpenEdit}
                    onPostpone={handleOpenPostpone}
                />
            ) : (
                <DndContext
                    sensors={sensors}
                    collisionDetection={closestCorners}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                >
                    <div className="min-w-0">
                        <p className="mb-2 text-xs font-medium text-text-secondary md:hidden">
                            {t('appointments.board.swipe_hint', 'Swipe horizontally to view stages. You can also change status from each card without dragging.')}
                        </p>
                        <div className="flex min-h-[32rem] snap-x snap-mandatory items-start gap-3 overflow-x-auto overscroll-x-contain pb-5 sm:gap-4 lg:gap-6">
                            {columns.map(col => (
                                <SortableContext
                                    key={col.id}
                                    items={getColumnAppointments(col.id).map(a => a.id)}
                                    strategy={verticalListSortingStrategy}
                                >
                                    <KanbanColumn
                                        col={col}
                                        appointments={getColumnAppointments(col.id)}
                                        patients={patients}
                                        t={t}
                                        getStatusVariant={getStatusVariant}
                                        getStatusLabel={getStatusLabel}
                                        formatAppointmentDateTime={formatAppointmentDateTime}
                                        onStatusChange={handleStatus}
                                        onDelete={(id) => setConfirmDelete({ open: true, id })}
                                        onEdit={handleOpenEdit}
                                        onPostpone={handleOpenPostpone}
                                    />
                                </SortableContext>
                            ))}
                        </div>
                    </div>

                    <DragOverlay>
                        {activeId ? (
                            <AppointmentCard
                                appt={appointments.find(a => a.id === activeId)}
                                patient={patients.find(p => p.id === appointments.find(a => a.id === activeId)?.patient_id)}
                                t={t}
                                getStatusVariant={getStatusVariant}
                                getStatusLabel={getStatusLabel}
                                formatAppointmentDateTime={formatAppointmentDateTime}
                                onStatusChange={handleStatus}
                                onDelete={(id) => setConfirmDelete({ open: true, id })}
                                onEdit={handleOpenEdit}
                                onPostpone={handleOpenPostpone}
                                isOverlay
                            />
                        ) : null}
                    </DragOverlay>
                </DndContext>
            )}

            <Modal
                isOpen={isModalOpen}
                onClose={() => {
                    setIsModalOpen(false);
                    setIsQuickAddOpen(false);
                    setActiveRequestId(null);
                }}
                title={activeRequestId ? (i18n.language === 'ar' ? 'تأكيد حجز موعد المتابعة' : 'Schedule Next-Visit Follow-up') : t('appointments.form.title')}
                size="md"
            >
                <div className="min-w-0 space-y-4">
                    {!isQuickAddOpen ? (
                        <>
                            <PatientSelect
                                patients={patients}
                                value={newAppt.patient_id}
                                onChange={event => setNewAppt({ ...newAppt, patient_id: event.target.value })}
                                onQuickAdd={handleQuickAdd}
                                label={t('appointments.form.select_patient')}
                                placeholder={t('appointments.form.select_patient_placeholder')}
                            />
                            <DateTimePicker
                                label={t('appointments.form.datetime')}
                                value={newAppt.date_time}
                                onChange={event => setNewAppt({ ...newAppt, date_time: event.target.value })}
                            />
                            <div>
                                <label className="mb-2 block text-sm font-bold text-text-primary">{t('appointments.form.notes')}</label>
                                <textarea
                                    className="w-full resize-none rounded-xl border border-border bg-surface p-3 text-sm font-bold outline-none focus:ring-2 focus:ring-primary/20"
                                    rows={3}
                                    placeholder={t('appointments.form.notes_placeholder')}
                                    value={newAppt.notes}
                                    onChange={event => setNewAppt({ ...newAppt, notes: event.target.value })}
                                />
                            </div>
                            <div className="sticky bottom-0 z-10 -mx-3 flex gap-2 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 sm:-mx-4 sm:px-4">
                                <Button variant="ghost" onClick={() => setIsModalOpen(false)} className="min-h-11 flex-1 justify-center">
                                    {t('appointments.form.cancel_btn')}
                                </Button>
                                <Button onClick={handleCreate} className="min-h-11 flex-[2] justify-center">
                                    {t('appointments.form.confirm_btn')}
                                </Button>
                            </div>
                        </>
                    ) : (
                        <div className="min-w-0 space-y-4 animate-in fade-in slide-in-from-end-4 duration-300">
                            <div className="rounded-2xl border border-primary/10 bg-primary/5 p-3 sm:p-4">
                                <h4 className="mb-1 text-sm font-bold uppercase tracking-wider text-primary">{t('patients.quick_add_title', 'Quick Add New Patient')}</h4>
                                <p className="text-xs font-bold text-slate-500">{t('patients.quick_add_desc', 'Enter the basic details to register this patient immediately.')}</p>
                            </div>
                            <Input
                                label={t('patients.form.name', 'Patient Name')}
                                value={quickPatient.name}
                                onChange={event => setQuickPatient({ ...quickPatient, name: event.target.value })}
                                autoFocus
                            />
                            <Input
                                label={t('patients.form.phone', 'Phone Number')}
                                value={quickPatient.phone}
                                onChange={event => setQuickPatient({ ...quickPatient, phone: event.target.value })}
                                inputMode="tel"
                            />
                            <div className="sticky bottom-0 z-10 -mx-3 flex gap-2 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 sm:-mx-4 sm:px-4">
                                <Button variant="ghost" onClick={() => setIsQuickAddOpen(false)} className="min-h-11 flex-1 justify-center">
                                    {t('common.back', 'Back')}
                                </Button>
                                <Button onClick={handleQuickCreatePatient} isLoading={createPatientMutation.isPending} className="min-h-11 flex-[2] justify-center">
                                    {t('patients.form.create_btn', 'Create & Select')}
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            </Modal>

            <ConfirmDialog
                isOpen={confirmDelete.open}
                onClose={() => setConfirmDelete({ open: false, id: null })}
                onConfirm={() => handleDeleteConfirm(confirmDelete.id)}
                title={t('appointments.confirm_delete')}
                message={t('appointments.confirm_delete_desc', 'هل أنت متأكد من حذف هذا الموعد؟ هذه العملية لا يمكن التراجع عنها.')}
            />

            <Modal
                isOpen={editModal.open}
                onClose={() => setEditModal({ open: false, appt: null, date_time: '', duration_minutes: 30, doctor_id: '', notes: '' })}
                title={t('appointments.edit_form.title')}
                size="md"
            >
                <div className="min-w-0 space-y-4">
                    <div>
                        <label className="mb-2 block text-sm font-bold text-text-primary">{t('appointments.edit_form.patient')}</label>
                        <div className="rounded-xl border border-border bg-surface-subtle p-3 text-sm font-bold text-text-primary">
                            {patients.find(p => p.id === editModal.appt?.patient_id)?.name || editModal.appt?.patient_name || t('common.unknown', 'Unknown')}
                        </div>
                    </div>
                    <DateTimePicker
                        label={t('appointments.edit_form.datetime')}
                        value={editModal.date_time}
                        onChange={event => setEditModal(prev => ({ ...prev, date_time: event.target.value }))}
                    />
                    <div>
                        <label className="mb-2 block text-sm font-bold text-text-primary">{t('appointments.edit_form.duration')}</label>
                        <Input
                            type="number"
                            min="5"
                            step="5"
                            value={editModal.duration_minutes}
                            onChange={event => setEditModal(prev => ({ ...prev, duration_minutes: event.target.value }))}
                        />
                    </div>
                    {doctors && doctors.length > 0 && (
                        <div>
                            <label className="mb-2 block text-sm font-bold text-text-primary">{t('appointments.edit_form.doctor')}</label>
                            <select
                                className="w-full rounded-xl border border-border bg-surface p-3 text-sm font-bold text-text-primary outline-none focus:ring-2 focus:ring-primary/20"
                                value={editModal.doctor_id}
                                onChange={event => setEditModal(prev => ({ ...prev, doctor_id: event.target.value }))}
                            >
                                <option value="">{t('appointments.edit_form.select_doctor')}</option>
                                {doctors.map(doc => (
                                    <option key={doc.id} value={doc.id}>{doc.name || doc.username}</option>
                                ))}
                            </select>
                        </div>
                    )}
                    <div>
                        <label className="mb-2 block text-sm font-bold text-text-primary">{t('appointments.edit_form.notes')}</label>
                        <textarea
                            className="w-full resize-none rounded-xl border border-border bg-surface p-3 text-sm font-bold outline-none focus:ring-2 focus:ring-primary/20"
                            rows={3}
                            placeholder={t('appointments.edit_form.notes_placeholder')}
                            value={editModal.notes}
                            onChange={event => setEditModal(prev => ({ ...prev, notes: event.target.value }))}
                        />
                    </div>
                    <div className="sticky bottom-0 z-10 -mx-3 flex gap-2 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 sm:-mx-4 sm:px-4">
                        <Button
                            variant="ghost"
                            onClick={() => setEditModal({ open: false, appt: null, date_time: '', duration_minutes: 30, doctor_id: '', notes: '' })}
                            className="min-h-11 flex-1 justify-center"
                        >
                            {t('appointments.edit_form.cancel_btn')}
                        </Button>
                        <Button
                            onClick={handleUpdateAppointment}
                            isLoading={updateMutation.isPending}
                            className="min-h-11 flex-[2] justify-center"
                        >
                            {t('appointments.edit_form.save_btn')}
                        </Button>
                    </div>
                </div>
            </Modal>

            <Modal
                isOpen={postponeModal.open}
                onClose={() => setPostponeModal({ open: false, appt: null, date_time: '' })}
                title={t('appointments.postpone.title')}
                size="md"
            >
                <div className="min-w-0 space-y-4">
                    <p className="text-sm text-text-secondary leading-relaxed">
                        {t('appointments.postpone.desc')}
                    </p>
                    <DateTimePicker
                        label={t('appointments.postpone.new_datetime')}
                        value={postponeModal.date_time}
                        onChange={event => setPostponeModal(prev => ({ ...prev, date_time: event.target.value }))}
                    />
                    <div className="sticky bottom-0 z-10 -mx-3 flex gap-2 border-t border-border bg-surface-elevated px-3 pb-[max(0.25rem,env(safe-area-inset-bottom))] pt-3 sm:-mx-4 sm:px-4">
                        <Button
                            variant="ghost"
                            onClick={() => setPostponeModal({ open: false, appt: null, date_time: '' })}
                            className="min-h-11 flex-1 justify-center"
                        >
                            {t('appointments.postpone.cancel_btn')}
                        </Button>
                        <Button
                            onClick={handleConfirmPostpone}
                            isLoading={updateMutation.isPending}
                            className="min-h-11 flex-[2] justify-center"
                        >
                            {t('appointments.postpone.confirm_btn')}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

function ViewButton({ active, onClick, title, icon: Icon }) {
    return (
        <button
            type="button"
            onClick={onClick}
            title={title}
            aria-label={title}
            aria-pressed={active}
            className={`inline-flex min-h-9 min-w-11 flex-1 items-center justify-center rounded-lg px-3 transition-colors sm:flex-none ${active ? 'bg-primary text-white shadow-low' : 'text-text-secondary hover:bg-surface-hover'}`}
        >
            <Icon size={18} aria-hidden="true" />
        </button>
    );
}

function StatusSelect({ appt, t, onStatusChange, className = '' }) {
    return (
        <select
            className={`min-h-11 w-full rounded-xl border border-border bg-background px-3 py-2 text-xs font-bold text-text-primary outline-none focus:ring-2 focus:ring-primary/20 ${className}`}
            value={appt.status}
            onChange={(event) => onStatusChange(appt.id, event.target.value)}
            onPointerDown={(event) => event.stopPropagation()}
            aria-label={t('appointments.table.change_status')}
        >
            {STATUS_OPTIONS.map(status => (
                <option key={status} value={status}>
                    {status === 'Scheduled' ? t('appointments.status.scheduled') :
                        status === 'Waiting' ? t('appointments.status.waiting') :
                            status === 'In-Chair' ? t('appointments.status.in_chair') :
                                status === 'Completed' ? t('appointments.status.completed') :
                                    status === 'Postponed' ? t('appointments.status.postponed') :
                                        status === 'No Show' ? t('appointments.status.no_show') : t('appointments.status.cancelled')}
                </option>
            ))}
        </select>
    );
}

function AppointmentList({
    appointments,
    patients,
    t,
    formatAppointmentDateTime,
    getStatusLabel,
    getStatusVariant,
    onStatusChange,
    onDelete,
    onEdit,
    onPostpone
}) {
    return (
        <div className="min-w-0">
            <div className="grid gap-3 md:hidden">
                {appointments.map(appt => {
                    const patient = patients.find(p => p.id === appt.patient_id);
                    return (
                        <article key={appt.id} className="min-w-0 rounded-2xl border border-border bg-surface-elevated p-3 shadow-low sm:p-4">
                            <div className="flex min-w-0 items-start gap-3">
                                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 font-bold text-primary">
                                    {patient?.name?.charAt(0) || '?'}
                                </div>
                                <div className="min-w-0 flex-1">
                                    <h3 className="truncate text-sm font-bold text-text-primary" dir="auto">{patient?.name || t('common.unknown', 'Unknown')}</h3>
                                    <p className="mt-1 flex items-center gap-1.5 text-xs font-medium text-text-secondary">
                                        <Clock size={14} className="shrink-0 text-primary" aria-hidden="true" />
                                        <span dir="ltr" className="min-w-0 truncate">{formatAppointmentDateTime(appt.date_time)}</span>
                                    </p>
                                </div>
                                <div className="flex items-center gap-1">
                                    <button
                                        type="button"
                                        onClick={() => onPostpone(appt)}
                                        className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-text-muted transition-colors hover:bg-amber-50 hover:text-amber-600 dark:hover:bg-amber-900/20"
                                        title={t('appointments.actions.postpone')}
                                        aria-label={t('appointments.actions.postpone')}
                                    >
                                        <CalendarClock size={17} aria-hidden="true" />
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => onEdit(appt)}
                                        className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-text-muted transition-colors hover:bg-primary/10 hover:text-primary dark:hover:bg-primary/20"
                                        title={t('appointments.actions.edit')}
                                        aria-label={t('appointments.actions.edit')}
                                    >
                                        <Edit2 size={17} aria-hidden="true" />
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => onDelete(appt.id)}
                                        className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-text-muted transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
                                        aria-label={t('common.delete', 'Delete')}
                                    >
                                        <Trash2 size={17} aria-hidden="true" />
                                    </button>
                                </div>
                            </div>

                            {appt.notes && (
                                <p className="mt-3 flex min-w-0 items-start gap-2 rounded-xl bg-surface-subtle p-2.5 text-xs text-text-secondary">
                                    <StickyNote size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
                                    <span className="min-w-0 break-words line-clamp-2">{appt.notes}</span>
                                </p>
                            )}

                            <div className="mt-3 flex items-center justify-between gap-2">
                                <Badge variant={getStatusVariant(appt.status)} size="sm">
                                    {getStatusLabel(appt.status)}
                                </Badge>
                            </div>
                            <div className="mt-3">
                                <StatusSelect appt={appt} t={t} onStatusChange={onStatusChange} />
                            </div>
                        </article>
                    );
                })}
            </div>

            <div className="hidden overflow-hidden rounded-3xl border border-border bg-surface shadow-sm md:block">
                <div className="overflow-x-auto">
                    <table className="w-full min-w-[760px] text-start">
                        <thead className="border-b border-border bg-surface-hover text-xs font-bold uppercase tracking-wider text-text-secondary">
                            <tr>
                                <th className="p-4 text-start">{t('appointments.table.patient')}</th>
                                <th className="p-4 text-start">{t('appointments.table.datetime')}</th>
                                <th className="p-4 text-start">{t('appointments.table.notes')}</th>
                                <th className="p-4 text-start">{t('appointments.table.status')}</th>
                                <th className="p-4 text-start">{t('appointments.table.change_status')}</th>
                                <th className="p-4 text-center">{t('appointments.table.actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {appointments.map(appt => {
                                const patient = patients.find(p => p.id === appt.patient_id);
                                return (
                                    <tr key={appt.id} className="transition-colors hover:bg-surface-hover">
                                        <td className="p-4">
                                            <div className="flex min-w-0 items-center gap-3">
                                                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 font-bold text-primary">
                                                    {patient?.name?.charAt(0) || '?'}
                                                </div>
                                                <span className="max-w-48 truncate font-bold text-text-primary" dir="auto">{patient?.name || t('common.unknown', 'Unknown')}</span>
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <div className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                                                <Calendar size={14} className="shrink-0" aria-hidden="true" />
                                                <span dir="ltr">{formatAppointmentDateTime(appt.date_time)}</span>
                                            </div>
                                        </td>
                                        <td className="max-w-xs truncate p-4 text-sm text-text-secondary">{appt.notes || '-'}</td>
                                        <td className="p-4">
                                            <Badge variant={getStatusVariant(appt.status)} size="sm">{getStatusLabel(appt.status)}</Badge>
                                        </td>
                                        <td className="p-4">
                                            <StatusSelect appt={appt} t={t} onStatusChange={onStatusChange} className="min-w-36" />
                                        </td>
                                        <td className="p-4">
                                            <div className="flex justify-center gap-1">
                                                <button
                                                    type="button"
                                                    onClick={() => onPostpone(appt)}
                                                    className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-text-secondary transition-colors hover:bg-amber-50 hover:text-amber-600 dark:hover:bg-amber-900/20"
                                                    title={t('appointments.actions.postpone')}
                                                    aria-label={t('appointments.actions.postpone')}
                                                >
                                                    <CalendarClock size={16} aria-hidden="true" />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => onEdit(appt)}
                                                    className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-text-secondary transition-colors hover:bg-primary/10 hover:text-primary dark:hover:bg-primary/20"
                                                    title={t('appointments.actions.edit')}
                                                    aria-label={t('appointments.actions.edit')}
                                                >
                                                    <Edit2 size={16} aria-hidden="true" />
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => onDelete(appt.id)}
                                                    className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-text-secondary transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
                                                    aria-label={t('common.delete', 'Delete')}
                                                >
                                                    <Trash2 size={16} aria-hidden="true" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

const KanbanColumn = ({
    col,
    appointments,
    patients,
    t,
    getStatusVariant,
    getStatusLabel,
    formatAppointmentDateTime,
    onStatusChange,
    onDelete,
    onEdit,
    onPostpone
}) => {
    const { setNodeRef } = useSortable({ id: col.id });

    return (
        <section
            ref={setNodeRef}
            className="w-[min(18rem,calc(100vw-1.5rem))] min-w-[min(18rem,calc(100vw-1.5rem))] snap-start rounded-2xl border border-slate-200 bg-white/60 p-3 shadow-sm backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/60 sm:w-72 sm:min-w-72 sm:rounded-3xl sm:p-4 lg:p-5"
        >
            <div className={`mb-3 flex min-h-12 items-center justify-between gap-2 rounded-xl border p-3 shadow-sm sm:mb-4 sm:rounded-2xl ${col.border} ${col.bg}`}>
                <div className="flex min-w-0 items-center gap-2">
                    <div className={`shrink-0 rounded-xl bg-white/50 p-2 dark:bg-black/20 ${col.color}`}>
                        <col.icon size={19} aria-hidden="true" />
                    </div>
                    <span className={`min-w-0 break-words text-xs font-bold tracking-tight sm:text-sm ${col.color}`}>{col.title}</span>
                </div>
                <span className={`shrink-0 rounded-lg bg-white/60 px-2.5 py-1 text-xs font-bold dark:bg-black/30 ${col.color}`}>{appointments.length}</span>
            </div>

            <div className="flex min-h-[12rem] flex-col gap-3 sm:gap-4">
                {appointments.map(appt => (
                    <AppointmentCard
                        key={appt.id}
                        appt={appt}
                        patient={patients.find(p => p.id === appt.patient_id)}
                        t={t}
                        getStatusVariant={getStatusVariant}
                        getStatusLabel={getStatusLabel}
                        formatAppointmentDateTime={formatAppointmentDateTime}
                        onStatusChange={onStatusChange}
                        onDelete={onDelete}
                        onEdit={onEdit}
                        onPostpone={onPostpone}
                    />
                ))}
                {appointments.length === 0 && (
                    <div className="flex min-h-36 flex-1 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 p-5 text-slate-400 dark:border-slate-800/50 dark:text-slate-600">
                        <Plus size={24} className="mb-2 opacity-30" aria-hidden="true" />
                        <span className="text-center text-xs font-bold opacity-60">{t('appointments.no_appointments')}</span>
                    </div>
                )}
            </div>
        </section>
    );
};

const AppointmentCard = ({
    appt,
    patient,
    t,
    getStatusVariant,
    getStatusLabel,
    formatAppointmentDateTime,
    onStatusChange,
    onDelete,
    onEdit,
    onPostpone,
    isOverlay
}) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: appt?.id || 'null' });

    if (!appt) return null;

    const style = {
        transform: CSS.Translate.toString(transform),
        transition,
        zIndex: isOverlay ? 1000 : undefined,
    };

    return (
        <article
            ref={setNodeRef}
            style={style}
            className={`relative min-w-0 rounded-2xl border border-slate-100 bg-white p-3 shadow-sm transition-shadow dark:border-white/5 dark:bg-slate-800 sm:p-4 ${isDragging ? 'opacity-0' : 'opacity-100'} ${isOverlay ? 'scale-[1.02] shadow-2xl ring-2 ring-primary' : 'hover:shadow-md'}`}
        >
            <div className="mb-3 flex min-w-0 items-start gap-2">
                {!isOverlay && (
                    <button
                        type="button"
                        {...attributes}
                        {...listeners}
                        className="inline-flex h-11 w-9 shrink-0 cursor-grab touch-none items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 active:cursor-grabbing dark:hover:bg-slate-700"
                        aria-label={t('appointments.drag_handle', 'Drag appointment')}
                    >
                        <GripVertical size={18} aria-hidden="true" />
                    </button>
                )}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-sm font-bold text-primary shadow-inner">
                    {patient?.name?.charAt(0) || '?'}
                </div>
                <div className="min-w-0 flex-1 pt-0.5">
                    <h4 className="truncate text-sm font-bold tracking-tight text-slate-800 dark:text-slate-100" dir="auto">
                        {patient?.name || t('common.unknown', 'Unknown')}
                    </h4>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">#{appt.id}</p>
                </div>
                {!isOverlay && (
                    <div className="flex items-center gap-0.5">
                        <button
                            type="button"
                            onPointerDown={(event) => event.stopPropagation()}
                            onClick={() => onPostpone(appt)}
                            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-amber-50 hover:text-amber-600 dark:hover:bg-amber-900/20"
                            title={t('appointments.actions.postpone')}
                            aria-label={t('appointments.actions.postpone')}
                        >
                            <CalendarClock size={15} aria-hidden="true" />
                        </button>
                        <button
                            type="button"
                            onPointerDown={(event) => event.stopPropagation()}
                            onClick={() => onEdit(appt)}
                            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-primary/10 hover:text-primary dark:hover:bg-primary/20"
                            title={t('appointments.actions.edit')}
                            aria-label={t('appointments.actions.edit')}
                        >
                            <Edit2 size={15} aria-hidden="true" />
                        </button>
                        <button
                            type="button"
                            onPointerDown={(event) => event.stopPropagation()}
                            onClick={() => onDelete(appt.id)}
                            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-slate-400 transition-colors hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
                            aria-label={t('common.delete', 'Delete')}
                        >
                            <Trash2 size={15} aria-hidden="true" />
                        </button>
                    </div>
                )}
            </div>

            <div className="mb-3 flex min-w-0 items-center gap-2 rounded-xl border border-slate-100 bg-slate-50 p-2.5 text-xs font-bold text-slate-600 shadow-inner dark:border-white/5 dark:bg-slate-900/50 dark:text-slate-300">
                <Clock size={14} className="shrink-0 text-primary" aria-hidden="true" />
                <span dir="ltr" className="min-w-0 truncate">{formatAppointmentDateTime(appt.date_time)}</span>
            </div>

            {appt.notes && (
                <p className="mb-3 line-clamp-2 break-words rounded-xl border border-slate-100/50 bg-slate-50/50 p-2.5 text-xs italic text-slate-500 dark:border-white/5 dark:bg-slate-900/30 dark:text-slate-400">
                    {appt.notes}
                </p>
            )}

            <Badge variant={getStatusVariant(appt.status)} size="xs" className="w-full justify-center rounded-xl py-2 text-[10px] font-bold uppercase tracking-wider">
                {getStatusLabel(appt.status)}
            </Badge>

            {!isOverlay && (
                <div className="mt-3">
                    <StatusSelect appt={appt} t={t} onStatusChange={onStatusChange} />
                </div>
            )}
        </article>
    );
};
