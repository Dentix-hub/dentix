import { useState, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
    AlertCircle,
    CheckCircle2,
    ShieldAlert,
    Calendar,
} from 'lucide-react';
import { Button, Modal, Badge } from '@/shared/ui';
import { amendCareObservation } from '@/api/patients';

/**
 * Care Observation Amendment Modal (Requirement 4 / G10-M18).
 * Provides a compliant UI for retrospective clinical amendments.
 * Preserves the original record and author/date, requires an explicit amendment reason,
 * and posts an append-only superseding observation.
 */
export default function CareObservationAmendmentModal({
    isOpen = false,
    onClose,
    patientId,
    sessionId,
    observation = null,
    onSuccess,
    t = (k, f) => f || k,
}) {
    const sv = useMemo(() => observation?.structured_value || {}, [observation]);
    const isCanalLength = useMemo(() => {
        if (!observation) return false;
        return (
            observation.observation_code === 'canal_length' ||
            sv.length_mm != null ||
            Boolean(observation.canal_id)
        );
    }, [observation, sv]);

    // Initial state derived from existing observation
    const [lengthMm, setLengthMm] = useState('');
    const [maf, setMaf] = useState('');
    const [generalValue, setGeneralValue] = useState('');
    const [additionalNotes, setAdditionalNotes] = useState('');
    const [reason, setReason] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMsg, setErrorMsg] = useState(null);

    useEffect(() => {
        if (observation) {
            const curSv = observation.structured_value || {};
            setLengthMm(curSv.length_mm != null ? String(curSv.length_mm) : '');
            setMaf(curSv.maf != null ? String(curSv.maf) : '');
            const isCanal =
                observation.observation_code === 'canal_length' ||
                curSv.length_mm != null ||
                Boolean(observation.canal_id);
            if (isCanal) {
                setGeneralValue('');
            } else if (typeof curSv.value === 'string') {
                setGeneralValue(curSv.value);
            } else if (typeof curSv.value === 'number') {
                setGeneralValue(String(curSv.value));
            } else {
                setGeneralValue(observation.notes || '');
            }
            setAdditionalNotes('');
            setReason('');
            setErrorMsg(null);
        }
    }, [observation]);

    const formattedOriginalValue = useMemo(() => {
        if (!observation) return '';
        const parts = [];
        if (sv.length_mm != null) parts.push(`Length: ${sv.length_mm} mm`);
        if (sv.maf != null) parts.push(`MAF: #${sv.maf}`);
        if (sv.value != null) parts.push(`Value: ${sv.value}`);
        if (parts.length === 0 && observation.notes) parts.push(observation.notes);
        if (parts.length === 0) return JSON.stringify(sv);
        return parts.join(' | ');
    }, [sv, observation]);

    const formattedDate = useMemo(() => {
        if (!observation) return '--';
        const d = observation.recorded_at || observation.created_at;
        if (!d) return '--';
        try {
            return new Date(d).toLocaleString([], {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return String(d);
        }
    }, [observation]);

    if (!isOpen || !observation) return null;

    const handleSubmit = async (e) => {
        e?.preventDefault();
        const trimmedReason = reason.trim();
        if (!trimmedReason) {
            setErrorMsg(t('care_session.amendment_reason_required', 'Mandatory amendment reason is required.'));
            return;
        }

        setErrorMsg(null);
        setIsSubmitting(true);

        const newStructuredValue = { ...sv };
        if (isCanalLength) {
            if (lengthMm !== '') {
                newStructuredValue.length_mm = parseFloat(lengthMm);
            }
            if (maf !== '') {
                newStructuredValue.maf = maf;
            }
        } else if (generalValue.trim()) {
            newStructuredValue.value = generalValue.trim();
        }

        const payload = {
            reason: trimmedReason,
            observation_code: observation.observation_code,
            tooth_key: observation.tooth_key || null,
            canal_id: observation.canal_id || sv.canal_id || null,
            root_id: observation.root_id || sv.root_id || null,
            surface_code: observation.surface_code || sv.surface_code || null,
            structured_value: newStructuredValue,
            notes: additionalNotes.trim() || null,
        };

        try {
            await amendCareObservation(patientId, sessionId, observation.id, payload);
            if (onSuccess) onSuccess();
            onClose();
        } catch (err) {
            setErrorMsg(
                err?.response?.data?.detail?.message ||
                err?.response?.data?.detail ||
                err.message ||
                'Failed to submit observation amendment'
            );
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={t('care_session.amend_observation_title', 'Amend Chairside Observation')}
            size="md"
        >
            <form onSubmit={handleSubmit} className="space-y-4 p-1" data-testid="amend-observation-form">
                {/* Governance Alert */}
                <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50/80 p-3 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
                    <ShieldAlert className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
                    <div>
                        <span className="font-bold">Append-Only Clinical Audit Rule:</span>{' '}
                        <span>
                            Original records and historical provenance are permanently preserved. This action creates a new
                            superseding entry with mandatory justification.
                        </span>
                    </div>
                </div>

                {/* Original Observation Card */}
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 space-y-2 dark:border-slate-700 dark:bg-slate-800/60">
                    <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                        <span className="font-semibold uppercase tracking-wider text-[10px]">Original Observation</span>
                        <Badge variant="outline" className="font-mono text-[10px]">
                            ID #{observation.id}
                        </Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                            <span className="text-slate-500 block text-[11px]">Measurement / Target:</span>
                            <span className="font-bold text-slate-900 dark:text-slate-100">
                                {observation.observation_code}
                                {observation.tooth_key ? ` (Tooth ${observation.tooth_key})` : ''}
                                {observation.canal_id ? ` - ${observation.canal_id}` : ''}
                            </span>
                        </div>
                        <div>
                            <span className="text-slate-500 block text-[11px]">Recorded At:</span>
                            <span className="font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {formattedDate}
                            </span>
                        </div>
                    </div>

                    <div className="pt-1.5 border-t border-slate-200 dark:border-slate-700">
                        <span className="text-slate-500 block text-[11px]">Original Value:</span>
                        <div className="mt-0.5 font-mono text-xs font-bold text-slate-800 bg-white p-2 rounded-lg border border-slate-200 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-200">
                            {formattedOriginalValue}
                        </div>
                    </div>
                </div>

                {/* Correction Fields */}
                <div className="space-y-3 pt-1">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                        Corrected Clinical Value
                    </h4>

                    {isCanalLength ? (
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                                    Corrected Length (mm) <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="50"
                                    data-testid="amend-length-input"
                                    value={lengthMm}
                                    onChange={(e) => setLengthMm(e.target.value)}
                                    placeholder="e.g. 21.5"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs font-mono font-bold focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                                    MAF (Master Apical File)
                                </label>
                                <input
                                    type="text"
                                    data-testid="amend-maf-input"
                                    value={maf}
                                    onChange={(e) => setMaf(e.target.value)}
                                    placeholder="e.g. 25 or #30"
                                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs font-mono focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                                />
                            </div>
                        </div>
                    ) : (
                        <div>
                            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                                Corrected Observation Value <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                data-testid="amend-general-value-input"
                                value={generalValue}
                                onChange={(e) => setGeneralValue(e.target.value)}
                                placeholder="Enter correct measurement or finding"
                                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                                required
                            />
                        </div>
                    )}

                    {/* Mandatory Reason */}
                    <div>
                        <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                            Mandatory Correction Reason <span className="text-red-500">*</span>
                        </label>
                        <textarea
                            rows={2}
                            data-testid="amend-reason-input"
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            placeholder="State clinical justification (e.g., 'Apex locator re-confirmation showed 21.0mm after anatomical curvature adjustment')"
                            maxLength={500}
                            className="w-full rounded-lg border border-slate-300 p-2.5 text-xs focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                            required
                        />
                        <span className="text-[10px] text-slate-400 block text-end">
                            {reason.length}/500
                        </span>
                    </div>

                    {/* Additional Notes */}
                    <div>
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                            Optional Supplementary Notes
                        </label>
                        <input
                            type="text"
                            data-testid="amend-notes-input"
                            value={additionalNotes}
                            onChange={(e) => setAdditionalNotes(e.target.value)}
                            placeholder="Additional context if required"
                            className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                        />
                    </div>
                </div>

                {/* Error Banner */}
                {errorMsg && (
                    <div className="flex items-center gap-2 rounded-lg bg-red-50 p-2.5 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        <span>{errorMsg}</span>
                    </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={onClose}
                        disabled={isSubmitting}
                    >
                        {t('common.cancel', 'Cancel')}
                    </Button>
                    <Button
                        type="submit"
                        variant="primary"
                        size="sm"
                        disabled={isSubmitting || !reason.trim()}
                        data-testid="confirm-amendment-button"
                    >
                        {isSubmitting ? (
                            <span>Submitting...</span>
                        ) : (
                            <span className="flex items-center gap-1.5">
                                <CheckCircle2 className="h-4 w-4" />
                                {t('care_session.confirm_amendment', 'Confirm Amendment')}
                            </span>
                        )}
                    </Button>
                </div>
            </form>
        </Modal>
    );
}

CareObservationAmendmentModal.propTypes = {
    isOpen: PropTypes.bool,
    onClose: PropTypes.func.isRequired,
    patientId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    sessionId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    observation: PropTypes.object,
    onSuccess: PropTypes.func,
    t: PropTypes.func,
};
