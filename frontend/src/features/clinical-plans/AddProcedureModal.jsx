import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { Loader2 } from 'lucide-react';
import { DentixDialog } from '@/shared/ui';

export default function AddProcedureModal({
    open,
    phaseName,
    onClose,
    onSubmit,
    isLoading,
    candidates,
    selectedWorkItemId,
    onSelectWorkItemId,
    isPending,
    isRtl,
}) {
    const { t } = useTranslation();

    return (
        <DentixDialog
            open={open}
            onOpenChange={(isOpen) => {
                if (!isOpen) onClose();
            }}
            title={`${t('clinical_plans.add_procedure_dialog.title', 'Add Procedure to Phase')} — ${phaseName}`}
            size="md"
            closeLabel={t('common.close', 'Close')}
            closeOnOutside={!isPending}
        >
            <form
                data-testid="add-procedure-dialog"
                onSubmit={onSubmit}
                className="space-y-4"
                dir={isRtl ? 'rtl' : 'ltr'}
            >
                {isLoading ? (
                    <div
                        data-testid="candidates-loading"
                        className="flex items-center justify-center py-6 text-sm text-slate-500"
                    >
                        <Loader2 size={18} className="animate-spin ltr:mr-2 rtl:ml-2" />
                        <span>{t('common.loading', 'Loading...')}</span>
                    </div>
                ) : candidates.length === 0 ? (
                    <div
                        data-testid="no-candidates-message"
                        className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400"
                    >
                        {t(
                            'clinical_plans.no_candidate_procedures',
                            'No available procedures found for this patient.'
                        )}
                    </div>
                ) : (
                    <div>
                        <label
                            htmlFor="candidate-procedure-select"
                            className="block text-xs font-semibold text-slate-700 dark:text-slate-300"
                        >
                            {t('clinical_plans.add_procedure_dialog.procedure_label', 'Select Procedure')}{' '}
                            <span className="text-red-500">*</span>
                        </label>
                        <select
                            id="candidate-procedure-select"
                            data-testid="candidate-procedure-select"
                            required
                            value={selectedWorkItemId}
                            onChange={(e) => onSelectWorkItemId(e.target.value)}
                            className="mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                        >
                            <option value="">
                                {t('clinical_plans.add_procedure_dialog.choose_placeholder', '-- Select a procedure --')}
                            </option>
                            {candidates.map((candidate) => {
                                const targetStr = (candidate.targets || [])
                                    .map((tg) => (tg.tooth_key ? `${tg.tooth_key}${tg.surface ? ` (${tg.surface})` : ''}` : ''))
                                    .filter(Boolean)
                                    .join(', ');
                                const label = `${candidate.display_name || candidate.procedure_code}${targetStr ? ` — [${targetStr}]` : ''} (${candidate.status})`;

                                return (
                                    <option key={candidate.id} value={candidate.id}>
                                        {label}
                                    </option>
                                );
                            })}
                        </select>
                    </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-2">
                    <button
                        type="button"
                        data-testid="cancel-add-procedure"
                        onClick={onClose}
                        disabled={isPending}
                        className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                        {t('clinical_plans.dialog.cancel', 'Cancel')}
                    </button>
                    <button
                        type="submit"
                        data-testid="submit-add-procedure"
                        disabled={!selectedWorkItemId || isPending || candidates.length === 0}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-60"
                    >
                        {isPending && (
                            <Loader2 size={14} className="animate-spin" />
                        )}
                        <span>
                            {isPending
                                ? t('clinical_plans.add_procedure_dialog.submitting', 'Attaching...')
                                : t('clinical_plans.add_procedure_dialog.submit', 'Attach Procedure')}
                        </span>
                    </button>
                </div>
            </form>
        </DentixDialog>
    );
}

AddProcedureModal.propTypes = {
    open: PropTypes.bool.isRequired,
    phaseName: PropTypes.string,
    onClose: PropTypes.func.isRequired,
    onSubmit: PropTypes.func.isRequired,
    isLoading: PropTypes.bool,
    candidates: PropTypes.array,
    selectedWorkItemId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    onSelectWorkItemId: PropTypes.func.isRequired,
    isPending: PropTypes.bool,
    isRtl: PropTypes.bool,
};
