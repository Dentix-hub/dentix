import { memo, useState } from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import {
    ChevronDown,
    ChevronUp,
    ClipboardList,
    Plus,
    Calendar,
    Layers,
    FileText,
    X,
    Loader2,
} from 'lucide-react';
import { toast } from '@/shared/ui';
import {
    usePatientClinicalPlans,
    useCreatePatientClinicalPlan,
} from '@/hooks/usePatientDetails';

const TreatmentPlansCard = memo(({ patientId }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar' || document.documentElement.dir === 'rtl';

    const [isCollapsed, setIsCollapsed] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [title, setTitle] = useState('');
    const [notes, setNotes] = useState('');

    const {
        data: plans = [],
        isLoading,
        isError,
        error,
    } = usePatientClinicalPlans(patientId, { enabled: !!patientId });

    const createPlanMutation = useCreatePatientClinicalPlan();

    const handleOpenCreate = () => {
        setTitle('');
        setNotes('');
        setIsCreateOpen(true);
    };

    const handleCloseCreate = () => {
        if (createPlanMutation.isPending) return;
        setIsCreateOpen(false);
    };

    const handleSubmitCreate = async (e) => {
        e.preventDefault();
        const trimmedTitle = title.trim();
        if (!trimmedTitle) {
            toast.error(t('clinical_plans.alerts.title_required', 'Plan title is required'));
            return;
        }

        try {
            await createPlanMutation.mutateAsync({
                patientId,
                data: {
                    title: trimmedTitle,
                    notes: notes.trim() || null,
                },
            });
            toast.success(t('clinical_plans.alerts.create_success', 'Treatment plan created successfully'));
            setIsCreateOpen(false);
            setTitle('');
            setNotes('');
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.create_error', 'Failed to create treatment plan')
            );
        }
    };

    return (
        <section
            data-testid="clinical-treatment-plans-card"
            className="rounded-2xl border border-slate-200 bg-white shadow-sm transition-all dark:border-slate-800 dark:bg-slate-900"
            dir={isRtl ? 'rtl' : 'ltr'}
        >
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
                        <ClipboardList size={20} aria-hidden="true" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="font-bold text-slate-800 dark:text-white">
                                {t('clinical_plans.title', 'Treatment Plans')}
                            </h3>
                            {!isLoading && !isError && (
                                <span
                                    data-testid="clinical-plans-count-badge"
                                    className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                >
                                    {plans.length}
                                </span>
                            )}
                        </div>
                        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                            {t('clinical_plans.subtitle', 'Patient treatment plans and phases')}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        data-testid="new-clinical-plan-button"
                        onClick={handleOpenCreate}
                        className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl bg-emerald-500 px-3.5 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    >
                        <Plus size={16} aria-hidden="true" />
                        <span>{t('clinical_plans.new_plan', 'New Plan')}</span>
                    </button>

                    <button
                        type="button"
                        data-testid="toggle-clinical-plans-collapse"
                        onClick={() => setIsCollapsed((prev) => !prev)}
                        className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
                        title={isCollapsed ? t('clinical_plans.expand', 'Expand') : t('clinical_plans.collapse', 'Collapse')}
                        aria-label={isCollapsed ? t('clinical_plans.expand', 'Expand') : t('clinical_plans.collapse', 'Collapse')}
                    >
                        {isCollapsed ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
                    </button>
                </div>
            </div>

            {/* Collapsible Content */}
            {!isCollapsed && (
                <div className="border-t border-slate-100 p-4 pt-3 dark:border-slate-800/80 sm:p-5 sm:pt-4">
                    {isLoading ? (
                        <div
                            data-testid="clinical-plans-loading"
                            className="flex items-center justify-center py-8 text-sm text-slate-500 dark:text-slate-400"
                        >
                            <Loader2 size={20} className="animate-spin ltr:mr-2 rtl:ml-2" />
                            <span>{t('common.loading', 'Loading...')}</span>
                        </div>
                    ) : isError ? (
                        <div
                            data-testid="clinical-plans-error"
                            className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-400"
                        >
                            {error?.response?.data?.detail || error?.message || t('patient_details.unknown_error')}
                        </div>
                    ) : plans.length === 0 ? (
                        <div
                            data-testid="clinical-plans-empty"
                            className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 py-8 px-4 text-center dark:border-slate-800 dark:bg-slate-900/50"
                        >
                            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                                <ClipboardList size={24} />
                            </div>
                            <p className="mt-3 text-sm font-semibold text-slate-700 dark:text-slate-300">
                                {t('clinical_plans.empty_state', 'No treatment plans created yet.')}
                            </p>
                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                                {t('clinical_plans.empty_cta', 'Create your first plan for this patient')}
                            </p>
                            <button
                                type="button"
                                data-testid="empty-cta-create-plan"
                                onClick={handleOpenCreate}
                                className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-white px-3 py-1.5 text-xs font-bold text-emerald-700 shadow-sm transition-colors hover:bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300"
                            >
                                <Plus size={14} />
                                <span>{t('clinical_plans.new_plan', 'New Plan')}</span>
                            </button>
                        </div>
                    ) : (
                        <div data-testid="clinical-plans-list" className="space-y-3">
                            {plans.map((plan) => {
                                const phasesCount = plan.phases?.length || 1;
                                const defaultPhaseName =
                                    plan.phases?.[0]?.name || t('clinical_plans.default_phase', 'Phase 1');
                                const formattedDate = plan.created_at
                                    ? new Date(plan.created_at).toLocaleDateString(i18n.language, {
                                          year: 'numeric',
                                          month: 'short',
                                          day: 'numeric',
                                      })
                                    : '';

                                return (
                                    <div
                                        key={plan.id}
                                        data-testid={`clinical-plan-item-${plan.id}`}
                                        className="group rounded-xl border border-slate-200/90 bg-white p-4 transition-all hover:border-emerald-200 hover:shadow-sm dark:border-slate-800 dark:bg-slate-950/40 dark:hover:border-slate-700"
                                    >
                                        <div className="flex flex-wrap items-start justify-between gap-2">
                                            <div className="min-w-0">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <h4 className="font-bold text-slate-800 dark:text-white">
                                                        {plan.title}
                                                    </h4>
                                                    <span
                                                        data-testid={`clinical-plan-status-${plan.id}`}
                                                        className="inline-flex items-center rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                                                    >
                                                        {t(
                                                            `clinical_plans.status.${plan.status}`,
                                                            plan.status === 'draft' ? 'Draft' : plan.status
                                                        )}
                                                    </span>

                                                </div>

                                                <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                                                    <span className="inline-flex items-center gap-1">
                                                        <Layers size={14} className="text-slate-400" />
                                                        <span>
                                                            {defaultPhaseName} ({phasesCount}{' '}
                                                            {phasesCount === 1
                                                                ? t('clinical_plans.phases_count', 'Phase')
                                                                : t('clinical_plans.phases_count_plural', 'Phases')}
                                                            )
                                                        </span>
                                                    </span>

                                                    {formattedDate && (
                                                        <span className="inline-flex items-center gap-1">
                                                            <Calendar size={14} className="text-slate-400" />
                                                            <span>{formattedDate}</span>
                                                        </span>
                                                    )}
                                                </div>

                                                {plan.notes && (
                                                    <div className="mt-2.5 flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                                                        <FileText size={14} className="mt-0.5 shrink-0 text-slate-400" />
                                                        <p className="whitespace-pre-wrap">{plan.notes}</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Create Plan Dialog / Modal */}
            {isCreateOpen && (
                <div
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="create-plan-dialog-title"
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                >
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
                        onClick={handleCloseCreate}
                    />

                    {/* Dialog Container */}
                    <div
                        data-testid="create-clinical-plan-dialog"
                        className="relative z-10 w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900"
                        dir={isRtl ? 'rtl' : 'ltr'}
                    >
                        <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                            <h3
                                id="create-plan-dialog-title"
                                className="text-base font-bold text-slate-900 dark:text-white"
                            >
                                {t('clinical_plans.dialog.title', 'Create Treatment Plan')}
                            </h3>
                            <button
                                type="button"
                                onClick={handleCloseCreate}
                                disabled={createPlanMutation.isPending}
                                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
                                aria-label={t('common.close', 'Close')}
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmitCreate} className="mt-4 space-y-4">
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
                                    disabled={createPlanMutation.isPending}
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
                                    disabled={createPlanMutation.isPending}
                                />
                            </div>

                            <div className="flex items-center justify-end gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={handleCloseCreate}
                                    disabled={createPlanMutation.isPending}
                                    className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                                >
                                    {t('clinical_plans.dialog.cancel', 'Cancel')}
                                </button>
                                <button
                                    type="submit"
                                    data-testid="submit-create-clinical-plan"
                                    disabled={createPlanMutation.isPending}
                                    className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-60"
                                >
                                    {createPlanMutation.isPending && (
                                        <Loader2 size={14} className="animate-spin" />
                                    )}
                                    <span>
                                        {createPlanMutation.isPending
                                            ? t('clinical_plans.dialog.creating', 'Creating...')
                                            : t('clinical_plans.dialog.submit', 'Create Plan')}
                                    </span>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </section>
    );
});

TreatmentPlansCard.displayName = 'TreatmentPlansCard';

TreatmentPlansCard.propTypes = {
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
};

export default TreatmentPlansCard;
