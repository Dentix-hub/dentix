import React, { useState, useMemo, useCallback, memo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { Calendar, Clock, Plus, User, CheckCircle, XCircle, Trash2, LayoutGrid, List as ListIcon, Edit2, Filter } from 'lucide-react';
import { createAppointment, updateAppointmentStatus, deleteAppointment } from '@/api';
import { useAppointments } from '@/hooks/useAppointments';
import { usePatients } from '@/hooks/usePatients';
import { getTodayDateTimeStr } from '@/utils/toothUtils';
import { Button, Input, Modal, Badge, Skeleton, EmptyState, toast } from '@/shared/ui';

export default function Appointments() {
    const [searchParams, setSearchParams] = useSearchParams();
    const { t } = useTranslation();
    const preselectPatientId = searchParams.get('patient_id');
    const [viewMode, setViewMode] = useState('board'); // 'list' | 'board'
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [newAppt, setNewAppt] = useState({ patient_id: '', date_time: getTodayDateTimeStr(), notes: '' });

    useEffect(() => {
        if (preselectPatientId) {
            setNewAppt(prev => ({ ...prev, patient_id: preselectPatientId }));
            setIsModalOpen(true);
            setSearchParams({}, { replace: true });
        }
    }, [preselectPatientId, setSearchParams]);

    // Use cached hooks instead of direct API calls
    const { data: appointments = [], isLoading: apptsLoading, refetch: refetchAppointments } = useAppointments();
    const { data: patients = [], isLoading: patientsLoading } = usePatients();

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
            setNewAppt({ patient_id: '', date_time: getTodayDateTimeStr(), notes: '' });
            refetchAppointments(); // Use cached refetch
            toast.success(t('appointments.messages.booking_success'), { id: toastId });
        } catch (err) {
            toast.error(t('appointments.messages.booking_error'), { id: toastId });
        }
    }, [newAppt, refetchAppointments, t]);

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

    const handleDelete = useCallback(async (id) => {
        if (!window.confirm(t('appointments.confirm_delete'))) return;
        const toastId = toast.loading(t('appointments.messages.deleting'));
        try {
            await deleteAppointment(id);
            refetchAppointments(); // Use cached refetch
            toast.success(t('appointments.messages.delete_success'), { id: toastId });
        } catch (err) {
            toast.error(t('appointments.messages.delete_error'), { id: toastId });
        }
    }, [refetchAppointments, t]);

    // Kanban Columns
    const columns = useMemo(() => [
        { id: 'Scheduled', title: t('appointments.status.scheduled'), icon: Calendar, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800' },
        { id: 'Waiting', title: t('appointments.status.waiting'), icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800' },
        { id: 'In-Chair', title: t('appointments.status.in_chair'), icon: User, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-200 dark:border-purple-800' },
        { id: 'Completed', title: t('appointments.status.completed'), icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-800' },
        { id: 'Cancelled', title: t('appointments.status.cancelled_noshow'), icon: XCircle, color: 'text-slate-600', bg: 'bg-slate-50 dark:bg-slate-800', border: 'border-slate-200 dark:border-slate-700' },
    ], [t]);

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

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 min-h-screen pb-20">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h2 className="text-3xl font-black text-text-primary tracking-tight">{t('appointments.title')}</h2>
                    <p className="text-text-secondary mt-1 font-medium">{t('appointments.subtitle')}</p>
                </div>
                <div className="flex items-center gap-3 w-full md:w-auto">
                    {/* View Toggle */}
                    <div className="bg-surface p-1 rounded-xl flex border border-border">
                        <button
                            onClick={() => setViewMode('list')}
                            className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-primary text-white shadow' : 'text-text-secondary hover:bg-surface-hover'}`}
                        >
                            <ListIcon size={18} />
                        </button>
                        <button
                            onClick={() => setViewMode('board')}
                            className={`p-2 rounded-lg transition-all ${viewMode === 'board' ? 'bg-primary text-white shadow' : 'text-text-secondary hover:bg-surface-hover'}`}
                        >
                            <LayoutGrid size={18} />
                        </button>
                    </div>

                    <Button onClick={() => setIsModalOpen(true)}>
                        <Plus size={20} className="mr-2" />
                        {t('appointments.new_booking')}
                    </Button>
                </div>
            </div>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Skeleton.Box className="h-96 w-full rounded-3xl" />
                    <Skeleton.Box className="h-96 w-full rounded-3xl" />
                    <Skeleton.Box className="h-96 w-full rounded-3xl" />
                </div>
            ) : appointments.length === 0 ? (
                <EmptyState
                    title={t('appointments.no_appointments')}
                    description={t('appointments.no_appointments_desc')}
                    icon={Calendar}
                    action={<Button onClick={() => setIsModalOpen(true)}>{t('appointments.add_appointment')}</Button>}
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
                                                        onClick={() => handleDelete(appt.id)}
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
                <div className="flex gap-6 overflow-x-auto pb-6 items-start min-h-[500px]">
                    {columns.map(col => (
                        <div key={col.id} className={`min-w-[300px] w-[300px] flex-shrink-0 bg-surface rounded-[2rem] p-4 flex flex-col gap-4 border border-border shadow-sm`}>
                            {/* Column Header */}
                            <div className={`p-3 rounded-2xl border ${col.border} ${col.bg} flex justify-between items-center`}>
                                <div className="flex items-center gap-3">
                                    <div className={`p-1.5 rounded-lg bg-background/50 ${col.color}`}>
                                        <col.icon size={18} />
                                    </div>
                                    <span className={`font-black text-sm ${col.color}`}>{col.title}</span>
                                </div>
                                <span className={`bg-background/80 px-2 py-0.5 rounded-lg text-xs font-black ${col.color}`}>
                                    {getColumnAppointments(col.id).length}
                                </span>
                            </div>

                            {/* Cards */}
                            <div className="flex flex-col gap-3 min-h-[100px]">
                                {getColumnAppointments(col.id).map(appt => {
                                    const patient = patients.find(p => p.id === appt.patient_id);
                                    return (
                                        <div key={appt.id} className="bg-background hover:bg-surface-hover p-4 rounded-2xl shadow-sm border border-border transition-all group relative">
                                            <div className="flex justify-between items-start mb-3">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                                                        {patient?.name?.charAt(0)}
                                                    </div>
                                                    <h4 className="font-bold text-text-primary text-sm line-clamp-1">
                                                        {patient?.name || 'Unknown'}
                                                    </h4>
                                                </div>
                                                <button
                                                    onClick={() => handleDelete(appt.id)}
                                                    className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-red-500 rounded-lg transition-opacity"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>

                                            <div className="flex items-center gap-2 text-text-secondary text-xs font-bold mb-3 bg-surface p-2 rounded-lg border border-border/50">
                                                <Clock size={14} className="text-primary" />
                                                <span dir="ltr">
                                                    {new Date(appt.date_time).toLocaleString(t('language.switch_to_en') === 'English' ? 'ar-EG' : 'en-US', {
                                                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                                    })}
                                                </span>
                                            </div>

                                            {appt.notes && (
                                                <p className="text-text-secondary text-xs p-2 bg-surface rounded-lg mb-3 border border-border/50">
                                                    {appt.notes}
                                                </p>
                                            )}

                                            <select
                                                className="w-full text-xs p-2 bg-surface rounded-lg border border-border font-bold outline-none focus:border-primary"
                                                value={appt.status}
                                                onChange={(e) => handleStatus(appt.id, e.target.value)}
                                            >
                                                <option value="Scheduled">{t('appointments.status.scheduled')}</option>
                                                <option value="Waiting">{t('appointments.status.waiting')}</option>
                                                <option value="In-Chair">{t('appointments.status.in_chair')}</option>
                                                <option value="Completed">{t('appointments.status.completed')}</option>
                                                <option value="Cancelled">{t('appointments.status.cancelled')}</option>
                                            </select>
                                        </div>
                                    );
                                })}
                                {getColumnAppointments(col.id).length === 0 && (
                                    <div className="h-24 flex flex-col items-center justify-center border-2 border-dashed border-border rounded-xl text-text-secondary/50 text-xs font-medium">
                                        <span>{t('appointments.no_appointments')}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <Modal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                title={t('appointments.form.title')}
                size="md"
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-bold text-text-primary mb-2">{t('appointments.form.select_patient')}</label>
                        <select
                            className="w-full p-3 bg-surface rounded-xl border border-border outline-none focus:ring-2 focus:ring-primary/20 text-sm font-bold"
                            value={newAppt.patient_id}
                            onChange={e => setNewAppt({ ...newAppt, patient_id: e.target.value })}
                        >
                            <option value="">{t('appointments.form.select_patient_placeholder')}</option>
                            {patients.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
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
                </div>
            </Modal>
        </div>
    );
}
