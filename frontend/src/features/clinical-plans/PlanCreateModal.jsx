import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { Loader2 } from 'lucide-react';
import { DentixDialog } from '@/shared/ui';

export default function PlanCreateModal({
    open,
    onClose,
    onSubmit,
    title,
    setTitle,
    notes,
    setNotes,
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
            title={t('clinical_plans.dialog.title', 'Create Treatment Plan')}
            size="md"
            closeLabel={t('common.close', 'Close')}
            closeOnOutside={!isPending}
        >
            <form
                data-testid="create-clinical-plan-dialog"
                onSubmit={onSubmit}
                className="space-y-4"
                dir={isRtl ? 'rtl' : 'ltr'}
            >
                <div>
                    <label
                        htmlFor="plan-title-input"
                        className="block text-xs font-semibold text-slate-700 dark:text-slate-300"
                    >
                        {t('clinical_plans.dialog.title_label', 'Plan Title')}{' '}
                        <span className="text-red-500">*</span>
                    </label>
                    <input
                        id="plan-title-input"
                        data-testid="clinical-plan-title-input"
                        type="text"
                        required
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder={t(
                            'clinical_plans.dialog.title_placeholder',
                            'e.g. Comprehensive Rehabilitation'
                        )}
                        className="mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder-slate-500"
                        disabled={isPending}
                    />
                </div>

                <div>
                    <label
                        htmlFor="plan-notes-input"
                        className="block text-xs font-semibold text-slate-700 dark:text-slate-300"
                    >
                        {t('clinical_plans.dialog.notes_label', 'Notes (optional)')}
                    </label>
                    <textarea
                        id="plan-notes-input"
                        data-testid="clinical-plan-notes-input"
                        rows={3}
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder={t(
                            'clinical_plans.dialog.notes_placeholder',
                            'Clinical observations, strategy, or patient preferences...'
                        )}
                        className="mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder-slate-500"
                        disabled={isPending}
                    />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={isPending}
                        className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                        {t('clinical_plans.dialog.cancel', 'Cancel')}
                    </button>
                    <button
                        type="submit"
                        data-testid="submit-create-clinical-plan"
                        disabled={isPending}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-60"
                    >
                        {isPending && (
                            <Loader2 size={14} className="animate-spin" />
                        )}
                        <span>
                            {isPending
                                ? t('clinical_plans.dialog.creating', 'Creating...')
                                : t('clinical_plans.dialog.submit', 'Create Plan')}
                        </span>
                    </button>
                </div>
            </form>
        </DentixDialog>
    );
}

PlanCreateModal.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onSubmit: PropTypes.func.isRequired,
    title: PropTypes.string.isRequired,
    setTitle: PropTypes.func.isRequired,
    notes: PropTypes.string.isRequired,
    setNotes: PropTypes.func.isRequired,
    isPending: PropTypes.bool,
    isRtl: PropTypes.bool,
};
