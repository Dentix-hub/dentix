import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { Loader2 } from 'lucide-react';
import { DentixDialog } from '@/shared/ui';

export default function DeletePhaseConfirm({
    deletingPhase,
    onClose,
    onConfirm,
    isPending,
    isRtl,
}) {
    const { t } = useTranslation();

    return (
        <DentixDialog
            open={Boolean(deletingPhase)}
            onOpenChange={(isOpen) => {
                if (!isOpen && !isPending) onClose();
            }}
            title={t('clinical_plans.dialog.delete_phase_title', 'Delete Phase')}
            size="sm"
            closeLabel={t('common.close', 'Close')}
            closeOnOutside={!isPending}
        >
            <div data-testid="delete-phase-dialog" className="space-y-4" dir={isRtl ? 'rtl' : 'ltr'}>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                    {t(
                        'clinical_plans.dialog.delete_phase_confirm',
                        'Are you sure you want to delete this phase? Any linked procedures will be detached from this phase, but the underlying work items will remain intact.'
                    )}
                </p>
                {deletingPhase && (
                    <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-bold text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
                        {deletingPhase.name}
                    </div>
                )}
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
                        type="button"
                        data-testid="confirm-delete-phase-button"
                        onClick={onConfirm}
                        disabled={isPending}
                        className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-rose-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-rose-700 disabled:opacity-50"
                    >
                        {isPending && (
                            <Loader2 size={16} className="animate-spin" />
                        )}
                        <span>{t('common.delete', 'Delete')}</span>
                    </button>
                </div>
            </div>
        </DentixDialog>
    );
}

DeletePhaseConfirm.propTypes = {
    deletingPhase: PropTypes.shape({
        planId: PropTypes.number,
        phaseId: PropTypes.number,
        name: PropTypes.string,
    }),
    onClose: PropTypes.func.isRequired,
    onConfirm: PropTypes.func.isRequired,
    isPending: PropTypes.bool,
    isRtl: PropTypes.bool,
};
