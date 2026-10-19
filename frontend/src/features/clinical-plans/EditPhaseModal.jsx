import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { Loader2 } from 'lucide-react';
import { DentixDialog } from '@/shared/ui';

export default function EditPhaseModal({
    editingPhase,
    onClose,
    onSubmit,
    onChangeName,
    onChangeNotes,
    isPending,
    isRtl,
}) {
    const { t } = useTranslation();

    return (
        <DentixDialog
            open={Boolean(editingPhase)}
            onOpenChange={(isOpen) => {
                if (!isOpen) onClose();
            }}
            title={t('clinical_plans.dialog.edit_phase_title', 'Edit Treatment Plan Phase')}
            size="md"
            closeLabel={t('common.close', 'Close')}
            closeOnOutside={!isPending}
        >
            <form
                data-testid="edit-phase-dialog"
                onSubmit={onSubmit}
                className="space-y-4"
                dir={isRtl ? 'rtl' : 'ltr'}
            >
                <div>
                    <label
                        htmlFor="edit-phase-name-input"
                        className="block text-xs font-semibold text-slate-700 dark:text-slate-300"
                    >
                        {t('clinical_plans.dialog.phase_name_label', 'Phase Name')}{' '}
                        <span className="text-red-500">*</span>
                    </label>
                    <input
                        id="edit-phase-name-input"
                        data-testid="edit-phase-name-input"
                        type="text"
                        required
                        value={editingPhase?.name || ''}
                        onChange={(e) => onChangeName(e.target.value)}
                        placeholder={t('clinical_plans.dialog.phase_name_placeholder', 'e.g., Phase 1 - Preparatory')}
                        className="mt-1.5 block w-full min-h-11 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                    />
                </div>

                <div>
                    <label
                        htmlFor="edit-phase-notes-input"
                        className="block text-xs font-semibold text-slate-700 dark:text-slate-300"
                    >
                        {t('clinical_plans.dialog.phase_notes_label', 'Notes (Optional)')}
                    </label>
                    <textarea
                        id="edit-phase-notes-input"
                        data-testid="edit-phase-notes-input"
                        rows={3}
                        value={editingPhase?.notes || ''}
                        onChange={(e) => onChangeNotes(e.target.value)}
                        placeholder={t('clinical_plans.dialog.phase_notes_placeholder', 'Optional clinical instructions for this phase...')}
                        className="mt-1.5 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                    />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isPending}
                        className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                        {t('common.cancel', 'Cancel')}
                    </button>
                    <button
                        type="submit"
                        data-testid="submit-edit-phase-button"
                        disabled={isPending || !editingPhase?.name?.trim()}
                        className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-600 dark:hover:bg-blue-500"
                    >
                        {isPending && (
                            <Loader2 size={16} className="animate-spin" />
                        )}
                        <span>{t('common.save', 'Save')}</span>
                    </button>
                </div>
            </form>
        </DentixDialog>
    );
}

EditPhaseModal.propTypes = {
    editingPhase: PropTypes.shape({
        planId: PropTypes.number,
        phaseId: PropTypes.number,
        name: PropTypes.string,
        notes: PropTypes.string,
    }),
    onClose: PropTypes.func.isRequired,
    onSubmit: PropTypes.func.isRequired,
    onChangeName: PropTypes.func.isRequired,
    onChangeNotes: PropTypes.func.isRequired,
    isPending: PropTypes.bool,
    isRtl: PropTypes.bool,
};
