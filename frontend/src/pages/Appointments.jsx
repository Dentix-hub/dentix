import { useState, useMemo, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    DndContext, 
    DragOverlay, 
    closestCorners, 
    KeyboardSensor, 
    PointerSensor, 
    useSensor, 
    useSensors,
    PointerActivationConstraint
} from '@dnd-kit/core';
import { 
    arrayMove, 
    SortableContext, 
    sortableKeyboardCoordinates, 
    verticalListSortingStrategy,
    useSortable 
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Calendar, Clock, Plus, User, CheckCircle, XCircle, Trash2, LayoutGrid, List as ListIcon, Home, GripVertical } from 'lucide-react';
import { createAppointment, deleteAppointment, updateAppointmentStatus } from '@/api';
import { useAppointments, useUpdateAppointmentStatus, useUpdateAppointment } from '@/hooks/useAppointments';
import { usePatients, useCreatePatient } from '@/hooks/usePatients';
import { getTodayDateTimeStr } from '@/utils/toothUtils';
import { Button, Input, Modal, Badge, SkeletonBox, EmptyState, toast, ConfirmDialog, PageHeader, PatientSelect, WeeklyCalendar, StatCard } from '@/shared/ui';
import { useAuth } from '@/auth/useAuth';

export default function Appointments() {
    const { user } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();
    const { t } = useTranslation();
    const preselectPatientId = searchParams.get('patient_id');
    const [viewMode, setViewMode] = useState('calendar'); // 'list' | 'board' | 'calendar'
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState({ open: false, id: null });
    const [newAppt, setNewAppt] = useState({ 
        patient_id: '', 
        date_time: getTodayDateTimeStr(), 
        notes: '',
        doctor_id: user?.role === 'doctor' ? user.id : ''
    });
    const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
    const [quickPatient, setQuickPatient] = useState({ name: '', phone: '' });
    useEffect(() => {
        if (preselectPatientId) {
            setNewAppt(prev => ({ ...prev, patient_id: preselectPatientId }));
            setIsModalOpen(true);
            setSearchParams({}, { replace: true });
        }
    }, [preselectPatientId, setSearchParams]);
    // Sync doctor_id if user changes (e.g. after silent load)
    useEffect(() => {
        if (user?.id && !newAppt.doctor_id && user.role === 'doctor') {
            setNewAppt(prev => ({ ...prev, doctor_id: user.id }));
        }
    }, [user, newAppt.doctor_id]);
    // Use cached hooks instead of direct API calls
    const { data: appointments = [], isLoading: apptsLoading, refetch: refetchAppointments } = useAppointments();
    const { data: patients = [], isLoading: patientsLoading, refetch: refetchPatients } = usePatients();
    const updateMutation = useUpdateAppointment();
    const createPatientMutation = useCreatePatient();
    const loading = apptsLoading || patientsLoading;
    const handleCreate = useCallback(async () => {
        if (!newAppt.patient_id || !newAppt.date_time) {
            toast.error(t('appointments.messages.fill_all'));
            return;
        }
        const toastId = toast.loading(t('appointments.messages.booking'));
        try {
            await createAppointment({
                ...newAppt,
                patient_id: parseInt(newAppt.patient_id)
            });
            setIsModalOpen(false);
            setNewAppt({ 
                patient_id: '', 
                date_time: getTodayDateTimeStr(), 
                notes: '',
                doctor_id: user?.role === 'doctor' ? user.id : ''
            });
            refetchAppointments(); // Use cached refetch
            toast.success(t('appointments.messages.booking_success'), { id: toastId });
        } catch (err) {
            toast.error(t('appointments.messages.booking_error'), { id: toastId });
        }
    }, [newAppt, refetchAppointments, t, user]);

    const handleEventDrop = async (id, newDateTime) => {
        const toastId = toast.loading(t('appointments.messages.updating'));
        try {
            // Trim timezone offset if needed by server
            const formattedDate = newDateTime.split('.')[0];
            await updateMutation.mutateAsync({ id, data: { date_time: formattedDate } });
            toast.success(t('appointments.messages.update_success'), { id: toastId });
        } catch (err) {
            toast.error(t('appointments.messages.update_error'), { id: toastId });
        }
    };

    const handleSelectSlot = (dateTime) => {
        // dateTime is usually "2026-05-01T10:00:00"
        const formatted = dateTime.substring(0, 16); // "2026-05-01T10:00"
        setNewAppt(prev => ({ ...prev, date_time: formatted }));
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
        } catch (err) {
            toast.error(t('patients.messages.create_error', 'Failed to create patient'), { id: toastId });
        }
    };

    const handleStatus = useCallback(async (id, status) => {
        const toastId = toast.loading(t('appointments.messages.updating'));
        try {
            await updateAppointmentStatus(id, status);
            refetchAppointments(); // Use cached refetch
            toast.success(t('appointments.messages.update_success'), { id: toastId });
        } catch (err) {
            toast.error(t('appointments.messages.update_error'), { id: toastId });
        }
    }, [refetchAppointments, t]);
    const handleDeleteConfirm = useCallback(async (id) => {
        const toastId = toast.loading(t('appointments.messages.deleting'));
        try {
            await deleteAppointment(id);
            refetchAppointments(); // Use cached refetch
            toast.success(t('appointments.messages.delete_success'), { id: toastId });
            setConfirmDelete({ open: false, id: null });
        } catch (err) {
            toast.error(t('appointments.messages.delete_error'), { id: toastId });
        }
    }, [refetchAppointments, t]);
    // Kanban Columns
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
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragStart = (event) => {
        setActiveId(event.active.id);
    };

    const handleDragEnd = useCallback(async (event) => {
        const { active, over } = event;
        setActiveId(null);

        if (!over) return;

        const appointmentId = active.id;
        let targetColumnId = over.id;

        // If dropping on a card, get its column
        const overAppt = appointments.find(a => a.id === targetColumnId);
        if (overAppt) {
            targetColumnId = overAppt.status;
        }

        // Standardize column ID
        if (['Cancelled', 'No Show'].includes(targetColumnId)) {
            targetColumnId = 'Cancelled';
        }

        const activeAppt = appointments.find(a => a.id === appointmentId);
        if (activeAppt && activeAppt.status !== targetColumnId && columns.find(c => c.id === targetColumnId)) {
            try {
                await updateStatusMutation.mutateAsync({ id: appointmentId, status: targetColumnId });
                toast.success(t('appointments.messages.update_success'));
            } catch (err) {
                // Error handled by mutateAsync if needed, but we can toast here too
            }
        }
    }, [appointments, columns, t, updateStatusMutation]);

    const getColumnAppointments = (status) => {
        if (status === 'Cancelled') {
            return appointments.filter(a => ['Cancelled', 'No Show'].includes(a.status));
        }
        return appointments.filter(a => a.status === status);
    };

    const getStatusVariant = (status) => {
        switch (status) {
            case 'Scheduled': return 'info';
            case 'Completed': return 'success';
            case 'Cancelled': case 'No Show': return 'danger';
            case 'Waiting': return 'warning';
            case 'In-Chair': return 'primary';
            default: return 'default';
        }
    };

    const getStatusLabel = (status) => {
        const labels = {
            'Scheduled': t('appointments.status.scheduled'),
            'Completed': t('appointments.status.completed'),
            'Cancelled': t('appointments.status.cancelled'),
            'Waiting': t('appointments.status.waiting'),
            'In-Chair': t('appointments.status.in_chair'),
            'Postponed': t('appointments.status.postponed'),
            'No Show': t('appointments.status.no_show')
        };
        return labels[status] || status;
    };

    const stats = useMemo(() => {
        const today = new Date().toISOString().split('T')[0];
        const todayAppts = appointments.filter(a => a.date_time.startsWith(today));
        
        return [
            { 
                label: t('appointments.stats.today_total'), 
                value: todayAppts.length, 
                icon: Calendar, 
                color: 'blue' 
            },
            { 
                label: t('appointments.stats.waiting'), 
                value: appointments.filter(a => a.status === 'Waiting').length, 
                icon: Clock, 
                color: 'amber' 
            },
            { 
                label: t('appointments.stats.in_chair'), 
                value: appointments.filter(a => a.status === 'In-Chair').length, 
                icon: User, 
                color: 'teal' 
            },
            { 
                label: t('appointments.stats.completed_today'), 
                value: todayAppts.filter(a => a.status === 'Completed').length, 
                icon: CheckCircle, 
                color: 'emerald' 
            },
        ];
    }, [appointments, t]);

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 min-h-screen pb-20">
            <PageHeader
                title={t('appointments.title')}
                subtitle={t('appointments.subtitle')}
                breadcrumbs={[
                    { label: t('nav.home', 'Home'), icon: Home, path: '/' },
                    { label: t('appointments.title') }
                ]}
                actions={
                    <>
                        <div className="bg-surface p-1 rounded-xl flex border border-border">
                            <button
                                onClick={() => setViewMode('calendar')}
                                title={t('appointments.view.calendar')}
                                className={`p-2 rounded-lg transition-all ${viewMode === 'calendar' ? 'bg-primary text-white shadow' : 'text-text-secondary hover:bg-surface-hover'}`}
                            >
                                <Calendar size={18} />
                            </button>
                            <button
                                onClick={() => setViewMode('list')}
                                title={t('appointments.view.list')}
                                className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-primary text-white shadow' : 'text-text-secondary hover:bg-surface-hover'}`}
                            >
                                <ListIcon size={18} />
                            </button>
                            <button
                                onClick={() => setViewMode('board')}
                                title={t('appointments.view.board')}
                                className={`p-2 rounded-lg transition-all ${viewMode === 'board' ? 'bg-primary text-white shadow' : 'text-text-secondary hover:bg-surface-hover'}`}
                            >
                                <LayoutGrid size={18} />
                            </button>
                        </div>
                        <Button onClick={() => setIsModalOpen(true)}>
                            <Plus size={20} className="mr-2" />
                            {t('appointments.new_booking')}
                        </Button>
                    </>
                }
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {stats.map((stat, idx) => (
                    <StatCard
                        key={idx}
                        title={stat.label}
                        value={stat.value}
                        icon={stat.icon}
                        color={stat.color}
                    />
                ))}
            </div>
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <SkeletonBox className="h-96 w-full rounded-3xl" />
                    <SkeletonBox className="h-96 w-full rounded-3xl" />
                    <SkeletonBox className="h-96 w-full rounded-3xl" />
                </div>
            ) : appointments.length === 0 ? (
                <EmptyState
                    title={t('appointments.no_appointments')}
                    description={t('appointments.no_appointments_desc')}
                    icon={Calendar}
                    action={<Button onClick={() => setIsModalOpen(true)}>{t('appointments.add_appointment')}</Button>}
                />
            ) : viewMode === 'calendar' ? (
                <WeeklyCalendar 
                    appointments={appointments}
                    onEventClick={(appt) => {
                        // Open modal or details if needed
                        toast.info(`${t('appointments.table.patient')}: ${appt.patient_name}`);
                    }}
                    onEventDrop={handleEventDrop}
                    onSelectSlot={handleSelectSlot}
                />
            ) : viewMode === 'list' ? (
                // List View
                <div className="bg-surface rounded-3xl shadow-sm border border-border overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-start">
                            <thead className="bg-surface-hover text-text-secondary text-xs font-bold uppercase tracking-wider border-b border-border">
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
                                        <tr key={appt.id} className="hover:bg-surface-hover transition-colors">
                                            <td className="p-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold">
                                                        {patient?.name?.charAt(0) || '?'}
                                                    </div>
                                                    <span className="font-bold text-text-primary">{patient?.name || 'Unknown'}</span>
                                                </div>
                                            </td>
                                            <td className="p-4">
                                                <div className="flex items-center gap-2 text-text-secondary text-sm font-medium">
                                                    <Calendar size={14} />
                                                    <span dir="ltr">
                                                        {new Date(appt.date_time).toLocaleString(t('language.switch_to_en') === 'English' ? 'ar-EG' : 'en-US', {
                                                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                                        })}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="p-4 text-sm text-text-secondary max-w-xs truncate">
                                                {appt.notes || '-'}
                                            </td>
                                            <td className="p-4">
                                                <Badge variant={getStatusVariant(appt.status)} size="sm">
                                                    {getStatusLabel(appt.status)}
                                                </Badge>
                                            </td>
                                            <td className="p-4">
                                                <select
                                                    className="px-3 py-1.5 bg-background rounded-lg border border-border text-xs font-bold focus:ring-2 focus:ring-primary/20 outline-none"
                                                    value={appt.status}
                                                    onChange={(e) => handleStatus(appt.id, e.target.value)}
                                                >
                                                    <option value="Scheduled">{t('appointments.status.scheduled')}</option>
                                                    <option value="Waiting">{t('appointments.status.waiting')}</option>
                                                    <option value="In-Chair">{t('appointments.status.in_chair')}</option>
                                                    <option value="Completed">{t('appointments.status.completed')}</option>
                                                    <option value="Postponed">{t('appointments.status.postponed')}</option>
                                                    <option value="No Show">{t('appointments.status.no_show')}</option>
                                                    <option value="Cancelled">{t('appointments.status.cancelled')}</option>
                                                </select>
                                            </td>
                                            <td className="p-4">
                                                <div className="flex justify-center">
                                                    <button
                                                        onClick={() => setConfirmDelete({ open: true, id: appt.id })}
                                                        className="p-2 text-text-secondary hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                    >
                                                        <Trash2 size={16} />
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
            ) : (
                // Kanban Board View
                <DndContext
                    sensors={sensors}
                    collisionDetection={closestCorners}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                >
                    <div className="flex gap-6 overflow-x-auto pb-8 items-start min-h-[600px] -mx-4 px-4">
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
                                    setConfirmDelete={setConfirmDelete}
                                />
                            </SortableContext>
                        ))}
                    </div>

                    <DragOverlay>
                        {activeId ? (
                            <AppointmentCard
                                appt={appointments.find(a => a.id === activeId)}
                                patient={patients.find(p => p.id === appointments.find(a => a.id === activeId)?.patient_id)}
                                t={t}
                                getStatusVariant={getStatusVariant}
                                getStatusLabel={getStatusLabel}
                                setConfirmDelete={setConfirmDelete}
                                isOverlay
                            />
                        ) : null}
                    </DragOverlay>
                </DndContext>
            )}
            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={t('appointments.form.title')}
                size="md"
            >
                <div className="space-y-4">
                    {!isQuickAddOpen ? (
                        <>
                            <div>
                                <PatientSelect
                                    patients={patients}
                                    value={newAppt.patient_id}
                                    onChange={e => setNewAppt({ ...newAppt, patient_id: e.target.value })}
                                    onQuickAdd={handleQuickAdd}
                                    label={t('appointments.form.select_patient')}
                                    placeholder={t('appointments.form.select_patient_placeholder')}
                                />
                            </div>
                            <Input
                                type="datetime-local"
                                label={t('appointments.form.datetime')}
                                value={newAppt.date_time}
                                onChange={e => setNewAppt({ ...newAppt, date_time: e.target.value })}
                            />
                            <div>
                                <label className="block text-sm font-bold text-text-primary mb-2">{t('appointments.form.notes')}</label>
                                <textarea
                                    className="w-full p-3 bg-surface rounded-xl border border-border outline-none focus:ring-2 focus:ring-primary/20 text-sm font-bold resize-none"
                                    rows={3}
                                    placeholder={t('appointments.form.notes_placeholder')}
                                    value={newAppt.notes}
                                    onChange={e => setNewAppt({ ...newAppt, notes: e.target.value })}
                                />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <Button variant="ghost" onClick={() => setIsModalOpen(false)} className="flex-1">{t('appointments.form.cancel_btn')}</Button>
                                <Button onClick={handleCreate} className="flex-[2]">{t('appointments.form.confirm_btn')}</Button>
                            </div>
                        </>
                    ) : (
                        <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                            <div className="p-4 bg-primary/5 rounded-2xl border border-primary/10 mb-2">
                                <h4 className="text-sm font-black text-primary uppercase tracking-wider mb-1">{t('patients.quick_add_title', 'Quick Add New Patient')}</h4>
                                <p className="text-[11px] font-bold text-slate-500">{t('patients.quick_add_desc', 'Enter the basic details to register this patient immediately.')}</p>
                            </div>
                            <Input
                                label={t('patients.form.name', 'Patient Name')}
                                value={quickPatient.name}
                                onChange={e => setQuickPatient({ ...quickPatient, name: e.target.value })}
                                autoFocus
                            />
                            <Input
                                label={t('patients.form.phone', 'Phone Number')}
                                value={quickPatient.phone}
                                onChange={e => setQuickPatient({ ...quickPatient, phone: e.target.value })}
                            />
                            <div className="flex gap-3 pt-4">
                                <Button variant="ghost" onClick={() => setIsQuickAddOpen(false)} className="flex-1">
                                    {t('common.back', 'Back')}
                                </Button>
                                <Button onClick={handleQuickCreatePatient} loading={createPatientMutation.isPending} className="flex-[2]">
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
        </div>
    );
}

const KanbanColumn = ({ col, appointments, patients, t, getStatusVariant, getStatusLabel, setConfirmDelete }) => {
    const { setNodeRef } = useSortable({
        id: col.id,
    });

    return (
        <div ref={setNodeRef} className="min-w-[320px] w-[320px] flex-shrink-0 bg-white/40 dark:bg-slate-900/40 backdrop-blur-md rounded-3xl p-5 flex flex-col gap-5 border border-slate-200 dark:border-slate-800 shadow-sm">
            {/* Column Header */}
            <div className={`p-4 rounded-2xl border ${col.border} ${col.bg} flex justify-between items-center shadow-sm`}>
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-xl bg-white/50 dark:bg-black/20 ${col.color}`}>
                        <col.icon size={20} />
                    </div>
                    <span className={`font-black text-sm tracking-tight ${col.color}`}>{col.title}</span>
                </div>
                <span className={`bg-white/60 dark:bg-black/30 px-2.5 py-1 rounded-lg text-xs font-black ${col.color}`}>
                    {appointments.length}
                </span>
            </div>

            {/* Cards Area */}
            <div className="flex flex-col gap-4 min-h-[200px]">
                {appointments.map(appt => (
                    <AppointmentCard
                        key={appt.id}
                        appt={appt}
                        patient={patients.find(p => p.id === appt.patient_id)}
                        t={t}
                        getStatusVariant={getStatusVariant}
                        getStatusLabel={getStatusLabel}
                        setConfirmDelete={setConfirmDelete}
                    />
                ))}
                {appointments.length === 0 && (
                    <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 dark:border-slate-800/50 rounded-2xl p-8 text-slate-300 dark:text-slate-700">
                        <Plus size={24} className="mb-2 opacity-20" />
                        <span className="text-xs font-bold opacity-40">{t('appointments.no_appointments')}</span>
                    </div>
                )}
            </div>
        </div>
    );
};

const AppointmentCard = ({ appt, patient, t, getStatusVariant, getStatusLabel, setConfirmDelete, isOverlay }) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: appt?.id || 'null' });

    const style = {
        transform: CSS.Translate.toString(transform),
        transition,
        zIndex: isOverlay ? 1000 : undefined,
    };

    if (!appt) return null;

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            className={`
                bg-white dark:bg-slate-800 p-5 rounded-[1.5rem] shadow-sm border border-slate-100 dark:border-white/5 transition-all group relative cursor-grab active:cursor-grabbing
                ${isDragging ? 'opacity-0' : 'opacity-100'}
                ${isOverlay ? 'shadow-2xl ring-2 ring-primary scale-105 rotate-2' : 'hover:shadow-md hover:-translate-y-1'}
            `}
        >
            <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-2xl bg-primary/10 text-primary flex items-center justify-center text-sm font-black shrink-0 shadow-inner">
                        {patient?.name?.charAt(0) || '?'}
                    </div>
                    <div className="min-w-0">
                        <h4 className="font-black text-slate-800 dark:text-slate-100 text-sm line-clamp-1 tracking-tight">
                            {patient?.name || 'Unknown'}
                        </h4>
                        <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                             #{appt.id}
                        </p>
                    </div>
                </div>
                <button
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={() => setConfirmDelete({ open: true, id: appt.id })}
                    className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all opacity-0 group-hover:opacity-100"
                >
                    <Trash2 size={16} />
                </button>
            </div>

            <div className="flex items-center gap-2.5 text-slate-600 dark:text-slate-300 text-xs font-bold mb-4 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-2xl border border-slate-100 dark:border-white/5 shadow-inner">
                <Clock size={14} className="text-primary" />
                <span dir="ltr">
                    {new Date(appt.date_time).toLocaleString(t('language.switch_to_en') === 'English' ? 'ar-EG' : 'en-US', {
                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                    })}
                </span>
            </div>

            {appt.notes && (
                <p className="text-slate-500 dark:text-slate-400 text-[11px] p-3 bg-slate-50/50 dark:bg-slate-900/30 rounded-xl mb-4 border border-slate-100/50 dark:border-white/5 italic line-clamp-2">
                    {appt.notes}
                </p>
            )}

            <Badge variant={getStatusVariant(appt.status)} size="xs" className="w-full justify-center py-2 rounded-xl text-[10px] font-black uppercase tracking-wider">
                {getStatusLabel(appt.status)}
            </Badge>
            
            <div className="absolute top-2 left-1/2 -translate-x-1/2 w-8 h-1 bg-slate-100 dark:bg-slate-700 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
    );
};

