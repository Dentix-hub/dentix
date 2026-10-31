import { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
    Calendar,
    User,
    FileText,
    AlertCircle,
    History,
    Save,
} from 'lucide-react';
import { Button, Modal, Badge } from '@/shared/ui';
import { startCareSession } from '@/api/patients';

/**
 * Historical Care Session Entry Modal (Requirement 4).
 * Allows doctors to record a retrospective visit with distinct actual visit date,
 * performing clinician, associated procedures, and notes.
 * Directly completes the historical visit without creating an active session conflict.
 */
export default function HistoricalCareSessionModal({
    isOpen = false,
    onClose,
    patientId,
    patientWorkItems = [],
    doctors = [],
    currentUserId = null,
    onSuccess,
    t = (k, f) => f || k,
}) {
    // Current local ISO date-time string truncated to minutes (YYYY-MM-DDTHH:MM)
    const nowIso = useMemo(() => {
        const d = new Date();
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().slice(0, 16);
    }, []);

    const [actualVisitDate, setActualVisitDate] = useState(() => {
        // Default to yesterday at 10:00 AM
        const d = new Date();
        d.setDate(d.getDate() - 1);
        d.setHours(10, 0, 0, 0);
        d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
        return d.toISOString().slice(0, 16);
    });

    const [providerUserId, setProviderUserId] = useState(() => {
        return currentUserId ? String(currentUserId) : '';
    });

    const [selectedWorkItemIds, setSelectedWorkItemIds] = useState(() => {
        return patientWorkItems.length > 0 ? [patientWorkItems[0].id] : [];
    });

    const [notes, setNotes] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMsg, setErrorMsg] = useState(null);

    const toggleWorkItem = (id) => {
        setSelectedWorkItemIds((prev) =>
            prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
        );
    };

    const validate = () => {
        if (!actualVisitDate) {
            return t('care_session.error_visit_date_required', 'Actual visit date is required.');
        }
        const selectedDate = new Date(actualVisitDate);
        if (selectedDate > new Date()) {
            return t('care_session.error_future_date', 'Historical visit date cannot be in the future.');
        }
        if (selectedWorkItemIds.length === 0) {
            return t('care_session.error_select_procedure', 'Please select at least one procedure worked on during this visit.');
        }
        return null;
    };

    const handleSubmit = async (e) => {
        e?.preventDefault();
        const err = validate();
        if (err) {
            setErrorMsg(err);
            return;
        }
        setErrorMsg(null);
        setIsSubmitting(true);

        const payload = {
            is_historical: true,
            actual_visit_date: new Date(actualVisitDate).toISOString(),
            provider_user_id: providerUserId ? Number(providerUserId) : null,
            work_item_ids: selectedWorkItemIds,
            notes: notes.trim() || null,
        };

        try {
            await startCareSession(patientId, payload);
            if (onSuccess) onSuccess();
            onClose();
        } catch (err) {
            setErrorMsg(
                err?.response?.data?.detail?.message ||
                err?.response?.data?.detail ||
                err.message ||
                'Failed to record historical visit'
            );
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('care_session.record_historical_visit_title', 'Record Past / Historical Visit')}
            size="lg"
        >
            <form onSubmit={handleSubmit} data-testid="historical-care-session-form" className="space-y-5">
                {/* Information Header Banner */}
                <div className="flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50/50 p-4 dark:border-blue-900/40 dark:bg-blue-950/20">
                    <History className="h-5 w-5 shrink-0 text-primary mt-0.5" />
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-text-primary">
                                {t('care_session.historical_entry_badge', 'Retrospective Documentation')}
                            </span>
                            <Badge variant="primary" size="xs">
                                Historical
                            </Badge>
                        </div>
                        <p className="text-xs text-text-secondary mt-1">
                            {t(
                                'care_session.historical_entry_desc',
                                'Documents care previously delivered. The visit is finalized immediately and will not interrupt any active chairside visit.'
                            )}
                        </p>
                    </div>
                </div>

                {errorMsg && (
                    <div
                        data-testid="historical-entry-error"
                        className="flex items-center gap-2 rounded-xl border border-danger/20 bg-danger/10 p-3 text-xs font-bold text-danger"
                    >
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        <span>{errorMsg}</span>
                    </div>
                )}

                {/* Date & Doctor Selection */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                            <Calendar className="h-3.5 w-3.5 text-primary" />
                            <span>{t('care_session.actual_visit_date', 'Actual Visit Date & Time')} *</span>
                        </label>
                        <input
                            type="datetime-local"
                            value={actualVisitDate}
                            max={nowIso}
                            onChange={(e) => setActualVisitDate(e.target.value)}
                            data-testid="input-historical-visit-date"
                            required
                            className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                            <User className="h-3.5 w-3.5 text-primary" />
                            <span>{t('care_session.treating_provider', 'Treating Provider')}</span>
                        </label>
                        <select
                            value={providerUserId}
                            onChange={(e) => setProviderUserId(e.target.value)}
                            data-testid="select-historical-provider"
                            className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                        >
                            <option value="">{t('care_session.select_provider_prompt', '-- Select Doctor --')}</option>
                            {doctors.map((d) => (
                                <option key={d.id} value={d.id}>
                                    {d.full_name || d.name || d.username}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Procedure Association Checkboxes */}
                <div className="space-y-2">
                    <label className="block text-xs font-bold text-text-primary">
                        {t('care_session.associated_procedures', 'Procedures Addressed During This Visit')} *
                    </label>

                    {patientWorkItems.length === 0 ? (
                        <div className="rounded-xl border border-border bg-surface p-4 text-center text-xs text-text-secondary">
                            {t('care_session.no_patient_procedures', 'No clinical procedures found for this patient.')}
                        </div>
                    ) : (
                        <div className="max-h-48 overflow-y-auto rounded-xl border border-border bg-surface p-2 space-y-1">
                            {patientWorkItems.map((wi) => {
                                const isChecked = selectedWorkItemIds.includes(wi.id);
                                return (
                                    <label
                                        key={wi.id}
                                        data-testid={`checkbox-proc-${wi.id}`}
                                        className={`flex items-center justify-between gap-3 rounded-lg p-2 text-xs cursor-pointer transition-colors ${
                                            isChecked ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-surface-elevated text-text-primary'
                                        }`}
                                    >
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="checkbox"
                                                checked={isChecked}
                                                onChange={() => toggleWorkItem(wi.id)}
                                                className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                                            />
                                            <span>{wi.title || wi.display_label || wi.name || wi.code || `Procedure #${wi.id}`}</span>
                                        </div>
                                        {wi.targets?.[0]?.tooth_key && (
                                            <Badge variant="neutral" size="xs">
                                                Tooth #{wi.targets[0].tooth_key}
                                            </Badge>
                                        )}
                                    </label>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Clinical Notes */}
                <div className="space-y-1">
                    <label className="flex items-center gap-1.5 text-xs font-bold text-text-primary">
                        <FileText className="h-3.5 w-3.5 text-primary" />
                        <span>{t('care_session.visit_notes', 'Visit Clinical Notes & Findings')}</span>
                    </label>
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        data-testid="input-historical-notes"
                        rows={3}
                        placeholder={t('care_session.historical_notes_placeholder', 'Document treatment delivered, findings, anesthesia, materials...')}
                        className="w-full rounded-xl border border-border bg-surface p-3 text-xs text-text-primary focus:border-primary focus:outline-hidden"
                    />
                </div>

                {/* Footer Buttons */}
                <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                    <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
                        {t('common.cancel', 'Cancel')}
                    </Button>
                    <Button
                        variant="primary"
                        size="sm"
                        type="submit"
                        disabled={isSubmitting}
                        data-testid="btn-submit-historical-session"
                        className="gap-1.5 font-bold"
                    >
                        <Save className="h-4 w-4" />
                        <span>
                            {isSubmitting
                                ? t('common.recording', 'Recording...')
                                : t('care_session.record_visit_btn', 'Record Visit')}
                        </span>
                    </Button>
                </div>
            </form>
        </Modal>
    );
}

HistoricalCareSessionModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    patientWorkItems: PropTypes.array,
    doctors: PropTypes.array,
    currentUserId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    onSuccess: PropTypes.func,
    t: PropTypes.func,
};
