import { useState } from 'react';
import PropTypes from 'prop-types';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, RotateCcw, AlertTriangle, Loader2 } from 'lucide-react';
import { updateClinicalWorkItemStatus } from '@/api/patients';
import Modal from '@/shared/ui/Modal';
import { invalidatePatientClinicalQueries } from '@/features/patients/utils/invalidatePatientClinicalQueries';

/**
 * Normalizes status strings from either native ('active' | 'completed')
 * or legacy ('In Progress' | 'Done' | 'Pending') systems.
 */
export function normalizeProcedureStatus(status) {
    if (!status) return 'active';
    const s = String(status).toLowerCase();
    if (s === 'done' || s === 'completed') return 'completed';
    if (s === 'in progress' || s === 'in_progress' || s === 'active') return 'active';
    if (s === 'pending' || s === 'planned') return 'active';
    return s;
}

/**
 * Reusable Procedure Status Control (~10s inline change, Defect 7).
 * Allows doctors to quickly toggle procedure completion or reopen with correction reason
 * without opening the heavyweight full treatment editor modal.
 */
export default function ProcedureStatusControl({
    patientId,
    workItemId,
    currentStatus = 'active',
    versionId = 1,
    onStatusChanged,
    disabled = false,
    compact = false,
    t: customT,
}) {
    const { t: i18nT } = useTranslation();
    const t = customT || i18nT || ((k, fallback) => fallback || k);
    const queryClient = useQueryClient();

    const normalizedStatus = normalizeProcedureStatus(currentStatus);
    const isCompleted = normalizedStatus === 'completed';

    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState(null);

    // Modal state for reopening completed procedure (requires intent='reopen_correction' & reason)
    const [isReopenModalOpen, setIsReopenModalOpen] = useState(false);
    const [reopenReason, setReopenReason] = useState('');

    // Modal state for completing procedure with override reason if needed
    const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false);
    const [overrideReason, setOverrideReason] = useState('');

    const handleApplyStatus = async ({ targetStatus, intent, reason, override }) => {
        if (!workItemId || !patientId) return;
        setIsLoading(true);
        setErrorMessage(null);

        try {
            const payload = {
                status: targetStatus,
            };
            if (intent) payload.intent = intent;
            if (reason) payload.reason = reason;
            if (override) payload.override_reason = override;
            if (versionId) payload.expected_version_id = versionId;

            const res = await updateClinicalWorkItemStatus(patientId, workItemId, payload);
            const data = res?.data?.data || res?.data || {};

            // Invalidate cached patient queries
            invalidatePatientClinicalQueries(queryClient, patientId);
            queryClient.invalidateQueries({ queryKey: ['patient', String(patientId), 'treatments'] });
            queryClient.invalidateQueries({ queryKey: ['patient', Number(patientId), 'treatments'] });
            queryClient.invalidateQueries({ queryKey: ['patient', String(patientId), 'care-sessions'] });
            queryClient.invalidateQueries({ queryKey: ['patient', Number(patientId), 'care-sessions'] });
            queryClient.invalidateQueries({ queryKey: ['patient', String(patientId), 'workspace'] });

            if (onStatusChanged) {
                onStatusChanged(targetStatus, data);
            }

            setIsReopenModalOpen(false);
            setReopenReason('');
            setIsCompleteModalOpen(false);
            setOverrideReason('');
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || 'Failed to update status';
            // If backend rejected completion because steps are outstanding and override_reason is required:
            if (err.response?.status === 422 && String(detail).includes('override_reason')) {
                setIsCompleteModalOpen(true);
            } else {
                setErrorMessage(typeof detail === 'string' ? detail : JSON.stringify(detail));
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleQuickToggle = () => {
        if (disabled || isLoading) return;
        if (isCompleted) {
            // Reopening requires confirmation dialog and reason
            setIsReopenModalOpen(true);
        } else {
            // Try quick direct completion (~10s workflow)
            handleApplyStatus({ targetStatus: 'completed' });
        }
    };

    const handleConfirmReopen = (e) => {
        e.preventDefault();
        if (!reopenReason.trim()) return;
        handleApplyStatus({
            targetStatus: 'active',
            intent: 'reopen_correction',
            reason: reopenReason.trim(),
        });
    };

    const handleConfirmCompleteWithOverride = (e) => {
        e.preventDefault();
        handleApplyStatus({
            targetStatus: 'completed',
            override: overrideReason.trim() || undefined,
        });
    };

    return (
        <div data-testid="procedure-status-control" className="inline-flex items-center gap-1.5">
            {/* Status Button / Pill */}
            <button
                type="button"
                data-testid="status-toggle-btn"
                onClick={handleQuickToggle}
                disabled={disabled || isLoading}
                aria-label={
                    isCompleted
                        ? t('clinical.status.click_to_reopen', 'Procedure completed. Click to reopen.')
                        : t('clinical.status.click_to_complete', 'Procedure active. Click to mark complete.')
                }
                className={`group relative inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold transition-all shadow-xs ${
                    isCompleted
                        ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:hover:bg-emerald-900/60'
                        : 'bg-blue-100 text-blue-800 hover:bg-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:hover:bg-blue-900/60'
                } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
                {isLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                ) : isCompleted ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                ) : (
                    <RotateCcw className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 group-hover:rotate-45 transition-transform" aria-hidden="true" />
                )}
                <span>
                    {isCompleted
                        ? t('clinical.status.completed', 'Completed')
                        : t('clinical.status.active', 'In Progress')}
                </span>
                {!compact && (
                    <span className="text-[10px] opacity-75 underline ms-1 group-hover:opacity-100">
                        {isCompleted
                            ? t('clinical.status.reopen', 'Reopen')
                            : t('clinical.status.mark_done', 'Mark Done')}
                    </span>
                )}
            </button>

            {errorMessage && (
                <span data-testid="status-error-badge" className="text-xs text-red-600 font-semibold" title={errorMessage}>
                    ⚠ {errorMessage}
                </span>
            )}

            {/* Reopen Correction Modal (Required by Section 2.5) */}
            <Modal
                isOpen={isReopenModalOpen}
                onClose={() => {
                    setIsReopenModalOpen(false);
                    setReopenReason('');
                }}
                title={t('clinical.reopen_modal.title', 'Reopen Procedure')}
                size="sm"
            >
                <form onSubmit={handleConfirmReopen} className="space-y-4" data-testid="reopen-procedure-form">
                    <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
                        <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                        <div>
                            <p className="font-bold">
                                {t('clinical.reopen_modal.warning_title', 'Reopening Procedure Confirmation')}
                            </p>
                            <p className="mt-1">
                                {t(
                                    'clinical.reopen_modal.notice',
                                    'Reopening will change status back to active. Any unbilled pending charges will be automatically voided. Invoiced charges remain untouched and require manual review.'
                                )}
                            </p>
                        </div>
                    </div>

                    <div className="space-y-1 text-xs">
                        <label htmlFor="reopen-reason-input" className="block font-bold text-slate-700 dark:text-slate-300">
                            {t('clinical.reopen_modal.reason_label', 'Clinical Reason for Reopening')} <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            id="reopen-reason-input"
                            data-testid="reopen-reason-input"
                            required
                            value={reopenReason}
                            onChange={(e) => setReopenReason(e.target.value)}
                            placeholder={t('clinical.reopen_modal.reason_placeholder', 'e.g. Additional canal instrumentation required')}
                            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                        />
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={() => setIsReopenModalOpen(false)}
                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                            {t('common.cancel', 'Cancel')}
                        </button>
                        <button
                            type="submit"
                            data-testid="confirm-reopen-btn"
                            disabled={!reopenReason.trim() || isLoading}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-amber-700 disabled:opacity-50"
                        >
                            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                            <span>{t('clinical.reopen_modal.confirm', 'Confirm Reopen')}</span>
                        </button>
                    </div>
                </form>
            </Modal>

            {/* Completion Override Modal (if uncompleted steps exist) */}
            <Modal
                isOpen={isCompleteModalOpen}
                onClose={() => {
                    setIsCompleteModalOpen(false);
                    setOverrideReason('');
                }}
                title={t('clinical.complete_override.title', 'Complete with Incomplete Steps')}
                size="sm"
            >
                <form onSubmit={handleConfirmCompleteWithOverride} className="space-y-4" data-testid="complete-override-form">
                    <p className="text-xs text-slate-600 dark:text-slate-400">
                        {t(
                            'clinical.complete_override.prompt',
                            'This procedure has uncompleted steps in the active care session. Please state a clinical override reason to mark it completed.'
                        )}
                    </p>

                    <div className="space-y-1 text-xs">
                        <label htmlFor="override-reason-input" className="block font-bold text-slate-700 dark:text-slate-300">
                            {t('clinical.complete_override.reason_label', 'Clinical Override Reason')}
                        </label>
                        <input
                            type="text"
                            id="override-reason-input"
                            data-testid="override-reason-input"
                            value={overrideReason}
                            onChange={(e) => setOverrideReason(e.target.value)}
                            placeholder={t('clinical.complete_override.reason_placeholder', 'e.g. Remaining steps deemed unnecessary')}
                            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 shadow-xs focus:border-blue-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                        />
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={() => setIsCompleteModalOpen(false)}
                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                            {t('common.cancel', 'Cancel')}
                        </button>
                        <button
                            type="submit"
                            data-testid="confirm-complete-override-btn"
                            disabled={isLoading}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-50"
                        >
                            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                            <span>{t('clinical.complete_override.confirm', 'Complete Procedure')}</span>
                        </button>
                    </div>
                </form>
            </Modal>
        </div>
    );
}

ProcedureStatusControl.propTypes = {
    patientId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    workItemId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    currentStatus: PropTypes.string,
    versionId: PropTypes.number,
    onStatusChanged: PropTypes.func,
    disabled: PropTypes.bool,
    compact: PropTypes.bool,
    t: PropTypes.func,
};
