import { useState } from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import {
    Ban,
    Calendar,
    ArrowRightLeft,
    AlertCircle,
    Loader2,
} from 'lucide-react';
import Modal from '@/shared/ui/Modal';
import {
    stopNextVisitRequest,
    postponeNextVisitRequest,
    resumeNextVisitRequest,
    handoffNextVisitRequest,
} from '@/api/patients';
import { getDoctors } from '@/api/admin';

/**
 * FollowUpManagementModal (Slice S25 / G11-M10..M13).
 * Enables stopping, postponing, resuming, and clinical handoff of next-visit requests
 * with required reasons and audit trail.
 */
export default function FollowUpManagementModal({
    isOpen,
    onClose,
    request,
    doctors: doctorsProp = [],
    onSuccess,
}) {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    const doctorsQuery = useQuery({
        queryKey: ['doctors', 'follow-up-modal'],
        queryFn: async () => {
            const res = await getDoctors();
            const docs = res?.data?.doctors || res?.data || [];
            return Array.isArray(docs) ? docs : [];
        },
        enabled: Boolean(isOpen && (!doctorsProp || doctorsProp.length === 0)),
        staleTime: 5 * 60 * 1000,
    });

    const doctors = doctorsProp && doctorsProp.length > 0 ? doctorsProp : (doctorsQuery.data || []);

    const [activeAction, setActiveAction] = useState('postpone'); // 'postpone' | 'stop' | 'handoff' | 'resume'
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState(null);

    // Form fields
    const [stopReason, setStopReason] = useState('');
    const [postponeDate, setPostponeDate] = useState('');
    const [postponeReason, setPostponeReason] = useState('');
    const [handoffUserId, setHandoffUserId] = useState('');
    const [handoffReason, setHandoffReason] = useState('');
    const [handoffNotes, setHandoffNotes] = useState('');

    if (!request) return null;

    const patientId = request.patient_id;
    const requestId = request.id;

    const handleFormSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setErrorMessage(null);

        try {
            if (activeAction === 'stop') {
                if (!stopReason.trim()) return;
                await stopNextVisitRequest(patientId, requestId, { reason: stopReason.trim() });
            } else if (activeAction === 'postpone') {
                if (!postponeDate || !postponeReason.trim()) return;
                await postponeNextVisitRequest(patientId, requestId, {
                    postponed_to_date: new Date(postponeDate).toISOString(),
                    reason: postponeReason.trim(),
                });
            } else if (activeAction === 'handoff') {
                if (!handoffUserId || !handoffReason.trim()) return;
                await handoffNextVisitRequest(patientId, requestId, {
                    handoff_to_user_id: Number(handoffUserId),
                    reason: handoffReason.trim(),
                    notes: handoffNotes.trim() || undefined,
                });
            } else if (activeAction === 'resume') {
                await resumeNextVisitRequest(patientId, requestId);
            }

            // Invalidate query caches
            queryClient.invalidateQueries({ queryKey: ['next-visit-requests'] });
            queryClient.invalidateQueries({ queryKey: ['patient', String(patientId), 'care-sessions'] });
            queryClient.invalidateQueries({ queryKey: ['patient', Number(patientId), 'care-sessions'] });

            if (onSuccess) onSuccess();
            onClose();
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || 'Operation failed';
            setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('follow_up.manage_title', 'Manage Follow-up Request')}
            size="md"
        >
            <div className="space-y-4" data-testid="follow-up-management-modal">
                {/* Request Header Summary */}
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-900/60">
                    <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 dark:text-slate-100">
                            Request #{request.id} &bull; {request.reason}
                        </span>
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">
                            {request.status}
                        </span>
                    </div>
                    {request.patient_name && (
                        <p className="mt-1 text-slate-600 dark:text-slate-400">
                            Patient: {request.patient_name}
                        </p>
                    )}
                </div>

                {/* Action Switcher Tabs */}
                <div className="grid grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1 text-xs font-bold dark:bg-slate-800">
                    <button
                        type="button"
                        data-testid="tab-postpone"
                        onClick={() => setActiveAction('postpone')}
                        className={`flex items-center justify-center gap-1.5 rounded-lg py-1.5 transition-colors ${
                            activeAction === 'postpone'
                                ? 'bg-white text-blue-700 shadow-xs dark:bg-slate-700 dark:text-blue-300'
                                : 'text-slate-600 hover:text-slate-900 dark:text-slate-400'
                        }`}
                    >
                        <Calendar className="h-3.5 w-3.5" />
                        <span>{t('follow_up.action_postpone', 'Postpone')}</span>
                    </button>
                    <button
                        type="button"
                        data-testid="tab-handoff"
                        onClick={() => setActiveAction('handoff')}
                        className={`flex items-center justify-center gap-1.5 rounded-lg py-1.5 transition-colors ${
                            activeAction === 'handoff'
                                ? 'bg-white text-indigo-700 shadow-xs dark:bg-slate-700 dark:text-indigo-300'
                                : 'text-slate-600 hover:text-slate-900 dark:text-slate-400'
                        }`}
                    >
                        <ArrowRightLeft className="h-3.5 w-3.5" />
                        <span>{t('follow_up.action_handoff', 'Handoff')}</span>
                    </button>
                    <button
                        type="button"
                        data-testid="tab-stop"
                        onClick={() => setActiveAction('stop')}
                        className={`flex items-center justify-center gap-1.5 rounded-lg py-1.5 transition-colors ${
                            activeAction === 'stop'
                                ? 'bg-white text-red-700 shadow-xs dark:bg-slate-700 dark:text-red-300'
                                : 'text-slate-600 hover:text-slate-900 dark:text-slate-400'
                        }`}
                    >
                        <Ban className="h-3.5 w-3.5" />
                        <span>{t('follow_up.action_stop', 'Stop')}</span>
                    </button>
                </div>

                {errorMessage && (
                    <div
                        data-testid="followup-error-alert"
                        className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
                    >
                        <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                        <span>{errorMessage}</span>
                    </div>
                )}

                <form onSubmit={handleFormSubmit} className="space-y-3.5 text-xs">
                    {/* POSTPONE ACTION */}
                    {activeAction === 'postpone' && (
                        <div className="space-y-3" data-testid="postpone-form">
                            <div className="space-y-1">
                                <label htmlFor="postpone-date" className="block font-bold text-slate-700 dark:text-slate-300">
                                    {t('follow_up.new_target_date', 'New Target Date')} <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="datetime-local"
                                    id="postpone-date"
                                    data-testid="postpone-date-input"
                                    required
                                    value={postponeDate}
                                    onChange={(e) => setPostponeDate(e.target.value)}
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                            <div className="space-y-1">
                                <label htmlFor="postpone-reason" className="block font-bold text-slate-700 dark:text-slate-300">
                                    {t('follow_up.postpone_reason', 'Reason for Postponing')} <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    id="postpone-reason"
                                    data-testid="postpone-reason-input"
                                    required
                                    value={postponeReason}
                                    onChange={(e) => setPostponeReason(e.target.value)}
                                    placeholder={t('follow_up.postpone_placeholder', 'e.g. Patient requested delay, traveling')}
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                        </div>
                    )}

                    {/* HANDOFF ACTION */}
                    {activeAction === 'handoff' && (
                        <div className="space-y-3" data-testid="handoff-form">
                            <div className="space-y-1">
                                <label htmlFor="handoff-user" className="block font-bold text-slate-700 dark:text-slate-300">
                                    {t('follow_up.target_doctor', 'Select Target Doctor')} <span className="text-red-500">*</span>
                                </label>
                                <select
                                    id="handoff-user"
                                    data-testid="handoff-doctor-select"
                                    required
                                    value={handoffUserId}
                                    onChange={(e) => setHandoffUserId(e.target.value)}
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                >
                                    <option value="">{t('follow_up.choose_doctor', '-- Choose Doctor --')}</option>
                                    {doctors.map((doc) => (
                                        <option key={doc.id} value={doc.id}>
                                            Dr. {doc.name || doc.username}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="space-y-1">
                                <label htmlFor="handoff-reason" className="block font-bold text-slate-700 dark:text-slate-300">
                                    {t('follow_up.handoff_reason', 'Clinical Reason for Handoff')} <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    id="handoff-reason"
                                    data-testid="handoff-reason-input"
                                    required
                                    value={handoffReason}
                                    onChange={(e) => setHandoffReason(e.target.value)}
                                    placeholder={t('follow_up.handoff_placeholder', 'e.g. Surgical specialist required for apicoectomy')}
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                            <div className="space-y-1">
                                <label htmlFor="handoff-notes" className="block font-bold text-slate-700 dark:text-slate-300">
                                    {t('follow_up.handoff_instructions', 'Instructions for Receiving Clinician (optional)')}
                                </label>
                                <textarea
                                    id="handoff-notes"
                                    data-testid="handoff-notes-input"
                                    rows={2}
                                    value={handoffNotes}
                                    onChange={(e) => setHandoffNotes(e.target.value)}
                                    placeholder={t('follow_up.handoff_notes_placeholder', 'e.g. Previous radiographs attached, patient has latex sensitivity')}
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                        </div>
                    )}

                    {/* STOP ACTION */}
                    {activeAction === 'stop' && (
                        <div className="space-y-3" data-testid="stop-form">
                            <div className="space-y-1">
                                <label htmlFor="stop-reason" className="block font-bold text-slate-700 dark:text-slate-300">
                                    {t('follow_up.stop_reason', 'Reason for Stopping Reminders')} <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    id="stop-reason"
                                    data-testid="stop-reason-input"
                                    required
                                    value={stopReason}
                                    onChange={(e) => setStopReason(e.target.value)}
                                    placeholder={t('follow_up.stop_placeholder', 'e.g. Treatment completed elsewhere / Patient declined further care')}
                                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                />
                            </div>
                        </div>
                    )}

                    <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-lg border border-slate-300 px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                            {t('common.cancel', 'Cancel')}
                        </button>
                        <button
                            type="submit"
                            data-testid="confirm-followup-action-btn"
                            disabled={isLoading}
                            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-bold text-white shadow-xs transition-colors disabled:opacity-50 ${
                                activeAction === 'stop'
                                    ? 'bg-red-600 hover:bg-red-700'
                                    : activeAction === 'handoff'
                                    ? 'bg-indigo-600 hover:bg-indigo-700'
                                    : 'bg-blue-600 hover:bg-blue-700'
                            }`}
                        >
                            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                            <span>
                                {activeAction === 'stop'
                                    ? t('follow_up.stop_confirm', 'Stop Reminders')
                                    : activeAction === 'handoff'
                                    ? t('follow_up.handoff_confirm', 'Handoff Follow-up')
                                    : t('follow_up.postpone_confirm', 'Postpone Request')}
                            </span>
                        </button>
                    </div>
                </form>
            </div>
        </Modal>
    );
}

FollowUpManagementModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    request: PropTypes.object,
    doctors: PropTypes.arrayOf(PropTypes.object),
    onSuccess: PropTypes.func,
};
