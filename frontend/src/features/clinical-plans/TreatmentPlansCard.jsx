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
    Loader2,
    Trash2,
} from 'lucide-react';
import { toast, DentixDialog } from '@/shared/ui';
import {
    usePatientClinicalPlans,
    useCreatePatientClinicalPlan,
    usePatientClinicalPlanCandidates,
    useAddPatientClinicalPlanPhase,
    useAddPatientClinicalPlanItem,
    useRemovePatientClinicalPlanItem,
} from '@/hooks/usePatientDetails';

const TreatmentPlansCard = memo(({ patientId }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar' || document.documentElement.dir === 'rtl';

    const [isCollapsed, setIsCollapsed] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [title, setTitle] = useState('');
    const [notes, setNotes] = useState('');

    // Accordion state per plan ID (default to expanded)
    const [expandedPlans, setExpandedPlans] = useState({});

    // Add Procedure Modal state
    const [procedureModal, setProcedureModal] = useState({
        open: false,
        planId: null,
        phaseId: null,
        phaseName: '',
    });
    const [selectedWorkItemId, setSelectedWorkItemId] = useState('');

    const {
        data: plans = [],
        isLoading,
        isError,
        error,
    } = usePatientClinicalPlans(patientId, { enabled: !!patientId });

    const createPlanMutation = useCreatePatientClinicalPlan();
    const addPhaseMutation = useAddPatientClinicalPlanPhase();
    const addPlanItemMutation = useAddPatientClinicalPlanItem();
    const removePlanItemMutation = useRemovePatientClinicalPlanItem();

    const {
        data: candidates = [],
        isLoading: isCandidatesLoading,
    } = usePatientClinicalPlanCandidates(patientId, procedureModal.planId, {
        enabled: !!patientId && !!procedureModal.planId && procedureModal.open,
    });

    // Determine available candidates for the active phase
    const activePlan = plans.find((p) => p.id === procedureModal.planId);
    const activePhase = activePlan?.phases?.find((ph) => ph.id === procedureModal.phaseId);
    const attachedWorkItemIds = new Set((activePhase?.items || []).map((it) => it.work_item_id));
    const availableCandidates = candidates.filter((c) => !attachedWorkItemIds.has(c.id));

    const isPlanExpanded = (planId) => expandedPlans[planId] ?? true;

    const togglePlanExpanded = (planId) => {
        setExpandedPlans((prev) => ({
            ...prev,
            [planId]: !(prev[planId] ?? true),
        }));
    };

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

    const handleAddPhase = async (plan) => {
        const nextNumber = (plan.phases?.length || 0) + 1;
        const defaultName = t('clinical_plans.phase_n', 'Phase {{n}}', { n: nextNumber });
        try {
            await addPhaseMutation.mutateAsync({
                patientId,
                planId: plan.id,
                data: { name: defaultName },
            });
            toast.success(t('clinical_plans.alerts.add_phase_success', 'Phase added successfully'));
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.add_phase_error', 'Failed to add phase')
            );
        }
    };

    const handleOpenAddProcedure = (planId, phaseId, phaseName) => {
        setSelectedWorkItemId('');
        setProcedureModal({
            open: true,
            planId,
            phaseId,
            phaseName,
        });
    };

    const handleCloseAddProcedure = () => {
        if (addPlanItemMutation.isPending) return;
        setProcedureModal({ open: false, planId: null, phaseId: null, phaseName: '' });
        setSelectedWorkItemId('');
    };

    const handleSubmitAddProcedure = async (e) => {
        e.preventDefault();
        if (!selectedWorkItemId) return;

        try {
            await addPlanItemMutation.mutateAsync({
                patientId,
                planId: procedureModal.planId,
                phaseId: procedureModal.phaseId,
                data: { work_item_id: Number(selectedWorkItemId) },
            });
            toast.success(t('clinical_plans.alerts.add_item_success', 'Procedure added to phase successfully'));
            handleCloseAddProcedure();
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.add_item_error', 'Failed to add procedure to phase')
            );
        }
    };

    const handleRemoveItem = async (planId, phaseId, itemId) => {
        try {
            await removePlanItemMutation.mutateAsync({
                patientId,
                planId,
                phaseId,
                itemId,
            });
            toast.success(t('clinical_plans.alerts.remove_item_success', 'Procedure removed from phase'));
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.remove_item_error', 'Failed to remove procedure from phase')
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
                                const phasesCount = plan.phases?.length || 0;
                                const isExpanded = isPlanExpanded(plan.id);
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
                                                            {phasesCount}{' '}
                                                            {phasesCount === 1
                                                                ? t('clinical_plans.phases_count', 'Phase')
                                                                : t('clinical_plans.phases_count_plural', 'Phases')}
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

                                            <div className="flex items-center gap-2">
                                                <button
                                                    type="button"
                                                    data-testid={`add-phase-button-${plan.id}`}
                                                    onClick={() => handleAddPhase(plan)}
                                                    disabled={addPhaseMutation.isPending}
                                                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                                                >
                                                    {addPhaseMutation.isPending ? (
                                                        <Loader2 size={13} className="animate-spin" />
                                                    ) : (
                                                        <Plus size={13} />
                                                    )}
                                                    <span>{t('clinical_plans.add_phase', 'Add Phase')}</span>
                                                </button>

                                                <button
                                                    type="button"
                                                    data-testid={`toggle-plan-accordion-${plan.id}`}
                                                    onClick={() => togglePlanExpanded(plan.id)}
                                                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
                                                    aria-label={isExpanded ? t('clinical_plans.collapse', 'Collapse') : t('clinical_plans.expand', 'Expand')}
                                                >
                                                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                                </button>
                                            </div>
                                        </div>

                                        {/* Phases Accordion Content */}
                                        {isExpanded && (
                                            <div
                                                data-testid={`plan-phases-accordion-${plan.id}`}
                                                className="mt-4 space-y-3 border-t border-slate-100 pt-3 dark:border-slate-800/70"
                                            >
                                                {(plan.phases || []).map((phase) => (
                                                    <div
                                                        key={phase.id}
                                                        data-testid={`clinical-phase-item-${phase.id}`}
                                                        className="rounded-xl border border-slate-200/80 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-900/40"
                                                    >
                                                        {/* Phase Header */}
                                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                                            <div className="flex items-center gap-2">
                                                                <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-100 text-xs font-bold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                                                                    {phase.phase_order + 1}
                                                                </span>
                                                                <h5 className="font-semibold text-slate-800 dark:text-slate-100">
                                                                    {phase.name}
                                                                </h5>
                                                                <span
                                                                    data-testid={`phase-status-${phase.id}`}
                                                                    className="inline-flex items-center rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                                                >
                                                                    {t(`clinical_plans.status.${phase.status}`, phase.status)}
                                                                </span>
                                                            </div>

                                                            <button
                                                                type="button"
                                                                data-testid={`add-procedure-button-${phase.id}`}
                                                                onClick={() => handleOpenAddProcedure(plan.id, phase.id, phase.name)}
                                                                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                                                            >
                                                                <Plus size={13} />
                                                                <span>{t('clinical_plans.add_procedure', 'Add Procedure')}</span>
                                                            </button>
                                                        </div>

                                                        {/* Phase Items */}
                                                        <div className="mt-3 space-y-1.5">
                                                            {!phase.items || phase.items.length === 0 ? (
                                                                <div
                                                                    data-testid={`phase-empty-${phase.id}`}
                                                                    className="py-2.5 text-center text-xs text-slate-400 dark:text-slate-500"
                                                                >
                                                                    {t(
                                                                        'clinical_plans.no_procedures_in_phase',
                                                                        'No procedures attached to this phase yet.'
                                                                    )}
                                                                </div>
                                                            ) : (
                                                                phase.items.map((item) => {
                                                                    const targetsDesc = (item.work_item?.targets || [])
                                                                        .map((tg) =>
                                                                            tg.tooth_key
                                                                                ? `${tg.tooth_key}${tg.surface ? ` (${tg.surface})` : ''}`
                                                                                : ''
                                                                        )
                                                                        .filter(Boolean)
                                                                        .join(', ');

                                                                    return (
                                                                        <div
                                                                            key={item.id}
                                                                            data-testid={`phase-item-${item.id}`}
                                                                            className="flex items-center justify-between rounded-lg border border-slate-200/70 bg-white px-3 py-2 text-xs shadow-xs dark:border-slate-800 dark:bg-slate-950/70"
                                                                        >
                                                                            <div className="flex min-w-0 flex-wrap items-center gap-2">
                                                                                <span className="font-semibold text-slate-800 dark:text-slate-200">
                                                                                    {item.work_item?.display_name ||
                                                                                        item.work_item?.procedure_code ||
                                                                                        `Item #${item.id}`}
                                                                                </span>
                                                                                {targetsDesc && (
                                                                                    <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                                                                                        {targetsDesc}
                                                                                    </span>
                                                                                )}
                                                                                {item.work_item?.status && (
                                                                                    <span className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
                                                                                        {t(
                                                                                            `clinical_plans.status.${item.work_item.status}`,
                                                                                            item.work_item.status
                                                                                        )}
                                                                                    </span>
                                                                                )}
                                                                            </div>

                                                                            <button
                                                                                type="button"
                                                                                data-testid={`remove-phase-item-${item.id}`}
                                                                                onClick={() => handleRemoveItem(plan.id, phase.id, item.id)}
                                                                                disabled={removePlanItemMutation.isPending}
                                                                                title={t('clinical_plans.remove_procedure', 'Remove procedure from phase')}
                                                                                aria-label={t('clinical_plans.remove_procedure', 'Remove procedure from phase')}
                                                                                className="inline-flex h-6 w-6 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                                                                            >
                                                                                <Trash2 size={13} />
                                                                            </button>
                                                                        </div>
                                                                    );
                                                                })
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* Create Plan Dialog */}
            <DentixDialog
                open={isCreateOpen}
                onOpenChange={(open) => {
                    if (!open) handleCloseCreate();
                }}
                title={t('clinical_plans.dialog.title', 'Create Treatment Plan')}
                size="md"
                closeLabel={t('common.close', 'Close')}
                closeOnOutside={!createPlanMutation.isPending}
            >
                <form
                    data-testid="create-clinical-plan-dialog"
                    onSubmit={handleSubmitCreate}
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
            </DentixDialog>

            {/* Add Procedure Dialog */}
            <DentixDialog
                open={procedureModal.open}
                onOpenChange={(open) => {
                    if (!open) handleCloseAddProcedure();
                }}
                title={`${t('clinical_plans.add_procedure_dialog.title', 'Add Procedure to Phase')} — ${procedureModal.phaseName}`}
                size="md"
                closeLabel={t('common.close', 'Close')}
                closeOnOutside={!addPlanItemMutation.isPending}
            >
                <form
                    data-testid="add-procedure-dialog"
                    onSubmit={handleSubmitAddProcedure}
                    className="space-y-4"
                    dir={isRtl ? 'rtl' : 'ltr'}
                >
                    {isCandidatesLoading ? (
                        <div
                            data-testid="candidates-loading"
                            className="flex items-center justify-center py-6 text-sm text-slate-500"
                        >
                            <Loader2 size={18} className="animate-spin ltr:mr-2 rtl:ml-2" />
                            <span>{t('common.loading', 'Loading...')}</span>
                        </div>
                    ) : availableCandidates.length === 0 ? (
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
                                onChange={(e) => setSelectedWorkItemId(e.target.value)}
                                className="mt-1.5 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                            >
                                <option value="">
                                    {t('clinical_plans.add_procedure_dialog.choose_placeholder', '-- Select a procedure --')}
                                </option>
                                {availableCandidates.map((candidate) => {
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
                            onClick={handleCloseAddProcedure}
                            disabled={addPlanItemMutation.isPending}
                            className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-bold text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                            {t('clinical_plans.dialog.cancel', 'Cancel')}
                        </button>
                        <button
                            type="submit"
                            data-testid="submit-add-procedure"
                            disabled={!selectedWorkItemId || addPlanItemMutation.isPending || availableCandidates.length === 0}
                            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-60"
                        >
                            {addPlanItemMutation.isPending && (
                                <Loader2 size={14} className="animate-spin" />
                            )}
                            <span>
                                {addPlanItemMutation.isPending
                                    ? t('clinical_plans.add_procedure_dialog.submitting', 'Attaching...')
                                    : t('clinical_plans.add_procedure_dialog.submit', 'Attach Procedure')}
                            </span>
                        </button>
                    </div>
                </form>
            </DentixDialog>
        </section>
    );
});

TreatmentPlansCard.displayName = 'TreatmentPlansCard';

TreatmentPlansCard.propTypes = {
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
};

export default TreatmentPlansCard;
