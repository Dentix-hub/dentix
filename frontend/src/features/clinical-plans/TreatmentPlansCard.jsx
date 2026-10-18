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
    CheckCircle2,
    XCircle,
    Send,
    Pencil,
} from 'lucide-react';
import { toast, DentixDialog } from '@/shared/ui';
import { formatCurrency } from '@/utils/formatters';
import {
    usePatientClinicalPlans,
    useCreatePatientClinicalPlan,
    usePatientClinicalPlanCandidates,
    useAddPatientClinicalPlanPhase,
    useUpdatePatientClinicalPlanPhase,
    useReorderPatientClinicalPlanPhases,
    useDeletePatientClinicalPlanPhase,
    useAddPatientClinicalPlanItem,
    useRemovePatientClinicalPlanItem,
    useTransitionPatientClinicalPlan,
} from '@/hooks/usePatientDetails';

const getStatusBadgeClass = (status) => {
    switch (status) {
        case 'proposed':
            return 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300';
        case 'accepted':
            return 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300';
        case 'completed':
            return 'border-purple-200 bg-purple-50 text-purple-800 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-300';
        case 'cancelled':
            return 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300';
        case 'draft':
        default:
            return 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300';
    }
};

const TreatmentPlansCard = memo(({
    patientId,
    activeOverlayPlanId = null,
    activeOverlayPhaseId = null,
    onToggleOverlay,
}) => {
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

    // Phase Edit and Delete states
    const [editingPhase, setEditingPhase] = useState(null); // { planId, phaseId, name, notes }
    const [deletingPhase, setDeletingPhase] = useState(null); // { planId, phaseId, name }

    const {
        data: plans = [],
        isLoading,
        isError,
        error,
    } = usePatientClinicalPlans(patientId, { enabled: !!patientId });

    const createPlanMutation = useCreatePatientClinicalPlan();
    const addPhaseMutation = useAddPatientClinicalPlanPhase();
    const updatePhaseMutation = useUpdatePatientClinicalPlanPhase();
    const reorderPhasesMutation = useReorderPatientClinicalPlanPhases();
    const deletePhaseMutation = useDeletePatientClinicalPlanPhase();
    const addPlanItemMutation = useAddPatientClinicalPlanItem();
    const removePlanItemMutation = useRemovePatientClinicalPlanItem();
    const transitionPlanMutation = useTransitionPatientClinicalPlan();

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

    const handleTransitionPlan = async (plan, toStatus) => {
        try {
            await transitionPlanMutation.mutateAsync({
                patientId,
                planId: plan.id,
                data: { to_status: toStatus },
            });
            toast.success(t('clinical_plans.alerts.transition_success', 'Treatment plan status updated successfully'));
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.transition_error', 'Failed to update treatment plan status')
            );
        }
    };

    const handleMovePhaseUp = async (plan, phaseIndex) => {
        if (phaseIndex <= 0 || reorderPhasesMutation.isPending) return;
        const phases = [...(plan.phases || [])].sort((a, b) => a.phase_order - b.phase_order);
        const temp = phases[phaseIndex];
        phases[phaseIndex] = phases[phaseIndex - 1];
        phases[phaseIndex - 1] = temp;
        const phaseIds = phases.map((p) => p.id);

        try {
            await reorderPhasesMutation.mutateAsync({
                patientId,
                planId: plan.id,
                phaseIds,
            });
            toast.success(t('clinical_plans.alerts.reorder_success', 'Phases reordered successfully'));
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.reorder_error', 'Failed to reorder phases')
            );
        }
    };

    const handleMovePhaseDown = async (plan, phaseIndex) => {
        const phases = [...(plan.phases || [])].sort((a, b) => a.phase_order - b.phase_order);
        if (phaseIndex >= phases.length - 1 || reorderPhasesMutation.isPending) return;
        const temp = phases[phaseIndex];
        phases[phaseIndex] = phases[phaseIndex + 1];
        phases[phaseIndex + 1] = temp;
        const phaseIds = phases.map((p) => p.id);

        try {
            await reorderPhasesMutation.mutateAsync({
                patientId,
                planId: plan.id,
                phaseIds,
            });
            toast.success(t('clinical_plans.alerts.reorder_success', 'Phases reordered successfully'));
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.reorder_error', 'Failed to reorder phases')
            );
        }
    };

    const handleOpenEditPhase = (planId, phase) => {
        setEditingPhase({
            planId,
            phaseId: phase.id,
            name: phase.name,
            notes: phase.notes || '',
        });
    };

    const handleCloseEditPhase = () => {
        if (updatePhaseMutation.isPending) return;
        setEditingPhase(null);
    };

    const handleSubmitEditPhase = async (e) => {
        e.preventDefault();
        if (!editingPhase) return;
        const trimmedName = editingPhase.name.trim();
        if (!trimmedName) {
            toast.error(t('clinical_plans.alerts.phase_name_required', 'Phase name is required'));
            return;
        }

        try {
            await updatePhaseMutation.mutateAsync({
                patientId,
                planId: editingPhase.planId,
                phaseId: editingPhase.phaseId,
                data: {
                    name: trimmedName,
                    notes: editingPhase.notes?.trim() || null,
                },
            });
            toast.success(t('clinical_plans.alerts.update_phase_success', 'Phase updated successfully'));
            handleCloseEditPhase();
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.update_phase_error', 'Failed to update phase')
            );
        }
    };

    const handleConfirmDeletePhase = async () => {
        if (!deletingPhase || deletePhaseMutation.isPending) return;
        try {
            await deletePhaseMutation.mutateAsync({
                patientId,
                planId: deletingPhase.planId,
                phaseId: deletingPhase.phaseId,
            });
            toast.success(t('clinical_plans.alerts.delete_phase_success', 'Phase deleted successfully'));
            setDeletingPhase(null);
        } catch (err) {
            toast.error(
                err?.response?.data?.detail ||
                err?.message ||
                t('clinical_plans.alerts.delete_phase_error', 'Failed to delete phase')
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
                                const canModifyPlan = plan.status === 'draft' || plan.status === 'proposed';
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
                                        <div className="flex flex-wrap items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <h4 className="font-bold text-slate-800 dark:text-white">
                                                        {plan.title}
                                                    </h4>
                                                    <span
                                                        data-testid={`clinical-plan-status-${plan.id}`}
                                                        className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold ${getStatusBadgeClass(
                                                            plan.status
                                                        )}`}
                                                    >
                                                        {t(
                                                            `clinical_plans.status.${plan.status}`,
                                                            plan.status
                                                        )}
                                                    </span>
                                                    <span
                                                        data-testid={`plan-estimate-badge-${plan.id}`}
                                                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                                                        title={
                                                            (plan.unpriced_items_count ?? 0) > 0
                                                                ? t('clinical_plans.contains_unpriced', 'Contains unpriced procedures')
                                                                : undefined
                                                        }
                                                    >
                                                        <span>
                                                            {t('clinical_plans.estimate', 'Estimate')}: {formatCurrency(plan.plan_estimated_total ?? 0, 'EGP', i18n.language)}
                                                        </span>
                                                        {(plan.unpriced_items_count ?? 0) > 0 && (
                                                            <span
                                                                data-testid={`plan-unpriced-indicator-${plan.id}`}
                                                                className="font-bold text-amber-600 dark:text-amber-400"
                                                                title={t('clinical_plans.contains_unpriced', 'Contains unpriced procedures')}
                                                            >
                                                                *
                                                            </span>
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

                                            <div className="flex flex-wrap items-center gap-2">
                                                {/* Transition buttons based on allowed transitions (Decision 1) */}
                                                {plan.status === 'draft' && (
                                                    <>
                                                        <button
                                                            type="button"
                                                            data-testid={`plan-transition-proposed-${plan.id}`}
                                                            onClick={() => handleTransitionPlan(plan, 'proposed')}
                                                            disabled={transitionPlanMutation.isPending}
                                                            className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-xs font-semibold text-blue-700 shadow-sm transition-colors hover:bg-blue-100 disabled:opacity-50 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300 dark:hover:bg-blue-900/50"
                                                        >
                                                            <Send size={13} />
                                                            <span>{t('clinical_plans.actions.propose', 'Propose')}</span>
                                                        </button>
                                                        <button
                                                            type="button"
                                                            data-testid={`plan-transition-cancelled-${plan.id}`}
                                                            onClick={() => handleTransitionPlan(plan, 'cancelled')}
                                                            disabled={transitionPlanMutation.isPending}
                                                            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-medium text-slate-500 shadow-sm transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                                                        >
                                                            <XCircle size={13} />
                                                            <span>{t('clinical_plans.actions.cancel', 'Cancel')}</span>
                                                        </button>
                                                    </>
                                                )}

                                                {plan.status === 'proposed' && (
                                                    <>
                                                        <button
                                                            type="button"
                                                            data-testid={`plan-transition-accepted-${plan.id}`}
                                                            onClick={() => handleTransitionPlan(plan, 'accepted')}
                                                            disabled={transitionPlanMutation.isPending}
                                                            className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-semibold text-emerald-700 shadow-sm transition-colors hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 dark:hover:bg-emerald-900/50"
                                                        >
                                                            <CheckCircle2 size={13} />
                                                            <span>{t('clinical_plans.actions.accept', 'Accept')}</span>
                                                        </button>
                                                        <button
                                                            type="button"
                                                            data-testid={`plan-transition-cancelled-${plan.id}`}
                                                            onClick={() => handleTransitionPlan(plan, 'cancelled')}
                                                            disabled={transitionPlanMutation.isPending}
                                                            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-medium text-slate-500 shadow-sm transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                                                        >
                                                            <XCircle size={13} />
                                                            <span>{t('clinical_plans.actions.cancel', 'Cancel')}</span>
                                                        </button>
                                                    </>
                                                )}

                                                {plan.status === 'accepted' && (
                                                    <>
                                                        <button
                                                            type="button"
                                                            data-testid={`plan-transition-completed-${plan.id}`}
                                                            onClick={() => handleTransitionPlan(plan, 'completed')}
                                                            disabled={transitionPlanMutation.isPending}
                                                            className="inline-flex items-center gap-1 rounded-lg border border-purple-200 bg-purple-50 px-2.5 py-1.5 text-xs font-semibold text-purple-700 shadow-sm transition-colors hover:bg-purple-100 disabled:opacity-50 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-300 dark:hover:bg-purple-900/50"
                                                        >
                                                            <CheckCircle2 size={13} />
                                                            <span>{t('clinical_plans.actions.complete', 'Complete')}</span>
                                                        </button>
                                                        <button
                                                            type="button"
                                                            data-testid={`plan-transition-cancelled-${plan.id}`}
                                                            onClick={() => handleTransitionPlan(plan, 'cancelled')}
                                                            disabled={transitionPlanMutation.isPending}
                                                            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-medium text-slate-500 shadow-sm transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                                                        >
                                                            <XCircle size={13} />
                                                            <span>{t('clinical_plans.actions.cancel', 'Cancel')}</span>
                                                        </button>
                                                    </>
                                                )}

                                                {/* Plan Overlay on Chart toggle (G9-M09) */}
                                                <button
                                                    type="button"
                                                    data-testid={`overlay-plan-button-${plan.id}`}
                                                    onClick={() => onToggleOverlay?.(plan.id, null)}
                                                    aria-pressed={activeOverlayPlanId === plan.id && activeOverlayPhaseId === null}
                                                    className={`inline-flex min-h-11 items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold shadow-xs transition-colors ${
                                                        activeOverlayPlanId === plan.id && activeOverlayPhaseId === null
                                                            ? 'border-blue-600 bg-blue-600 text-white dark:border-blue-500 dark:bg-blue-600'
                                                            : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
                                                    }`}
                                                    title={
                                                        activeOverlayPlanId === plan.id && activeOverlayPhaseId === null
                                                            ? t('clinical_plans.overlay.hide', 'Hide from Chart')
                                                            : t('clinical_plans.overlay.show', 'Show on Chart')
                                                    }
                                                >
                                                    <Layers size={14} />
                                                    <span>
                                                        {activeOverlayPlanId === plan.id && activeOverlayPhaseId === null
                                                            ? t('clinical_plans.overlay.hide', 'Hide from Chart')
                                                            : t('clinical_plans.overlay.show', 'Show on Chart')}
                                                    </span>
                                                </button>

                                                {/* Add Phase button - only visible if plan is draft or proposed (Decision 4) */}
                                                {canModifyPlan && (
                                                    <button
                                                        type="button"
                                                        data-testid={`add-phase-button-${plan.id}`}
                                                        onClick={() => handleAddPhase(plan)}
                                                        disabled={addPhaseMutation.isPending}
                                                        className="inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition-colors hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                                                    >
                                                        {addPhaseMutation.isPending ? (
                                                            <Loader2 size={13} className="animate-spin" />
                                                        ) : (
                                                            <Plus size={13} />
                                                        )}
                                                        <span>{t('clinical_plans.add_phase', 'Add Phase')}</span>
                                                    </button>
                                                )}

                                                <button
                                                    type="button"
                                                    data-testid={`toggle-plan-accordion-${plan.id}`}
                                                    onClick={() => togglePlanExpanded(plan.id)}
                                                    className="inline-flex min-h-11 w-11 items-center justify-center rounded-xl border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
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
                                                {(plan.phases || []).map((phase, idx) => (
                                                    <div
                                                        key={phase.id}
                                                        data-testid={`clinical-phase-item-${phase.id}`}
                                                        className="rounded-xl border border-slate-200/80 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-900/40"
                                                    >
                                                        {/* Phase Header */}
                                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                                            <div className="flex flex-wrap items-center gap-2">
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
                                                                <span
                                                                    data-testid={`phase-estimate-badge-${phase.id}`}
                                                                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                                                                    title={
                                                                        (phase.unpriced_items_count ?? 0) > 0
                                                                            ? t('clinical_plans.contains_unpriced', 'Contains unpriced procedures')
                                                                            : undefined
                                                                    }
                                                                >
                                                                    <span>
                                                                        {t('clinical_plans.estimate', 'Estimate')}: {formatCurrency(phase.phase_estimated_total ?? 0, 'EGP', i18n.language)}
                                                                    </span>
                                                                    {(phase.unpriced_items_count ?? 0) > 0 && (
                                                                        <span
                                                                            data-testid={`phase-unpriced-indicator-${phase.id}`}
                                                                            className="font-bold text-amber-600 dark:text-amber-400"
                                                                            title={t('clinical_plans.contains_unpriced', 'Contains unpriced procedures')}
                                                                        >
                                                                            *
                                                                        </span>
                                                                    )}
                                                                </span>
                                                                {phase.notes && (
                                                                    <span
                                                                        data-testid={`phase-notes-${phase.id}`}
                                                                        className="text-xs text-slate-500 italic dark:text-slate-400"
                                                                    >
                                                                        ({phase.notes})
                                                                    </span>
                                                                )}
                                                            </div>

                                                            <div className="flex flex-wrap items-center gap-1.5">
                                                                {/* Overlay Phase toggle (G9-M09) */}
                                                                <button
                                                                    type="button"
                                                                    data-testid={`overlay-phase-button-${phase.id}`}
                                                                    onClick={() => onToggleOverlay?.(plan.id, phase.id)}
                                                                    aria-pressed={activeOverlayPlanId === plan.id && activeOverlayPhaseId === phase.id}
                                                                    className={`inline-flex min-h-11 items-center gap-1 rounded-xl border px-2.5 py-1 text-xs font-medium transition-colors ${
                                                                        activeOverlayPlanId === plan.id && activeOverlayPhaseId === phase.id
                                                                            ? 'border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-950/60 dark:text-blue-300'
                                                                            : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                                                                    }`}
                                                                    title={t('clinical_plans.overlay.phase_tooltip', 'Highlight only this phase on chart')}
                                                                >
                                                                    <Layers size={13} />
                                                                    <span>{t('clinical_plans.overlay.phase_btn', 'Overlay Phase')}</span>
                                                                </button>

                                                                {canModifyPlan && (
                                                                    <>
                                                                        {/* Move Up */}
                                                                        <button
                                                                            type="button"
                                                                            data-testid={`move-up-phase-${phase.id}`}
                                                                            disabled={idx === 0 || reorderPhasesMutation.isPending}
                                                                            onClick={() => handleMovePhaseUp(plan, idx)}
                                                                            className="inline-flex min-h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                                                                            title={t('clinical_plans.actions.move_up', 'Move Up')}
                                                                            aria-label={`Move phase ${phase.name} up`}
                                                                        >
                                                                            <ChevronUp size={14} />
                                                                        </button>

                                                                        {/* Move Down */}
                                                                        <button
                                                                            type="button"
                                                                            data-testid={`move-down-phase-${phase.id}`}
                                                                            disabled={idx === (plan.phases || []).length - 1 || reorderPhasesMutation.isPending}
                                                                            onClick={() => handleMovePhaseDown(plan, idx)}
                                                                            className="inline-flex min-h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-30 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                                                                            title={t('clinical_plans.actions.move_down', 'Move Down')}
                                                                            aria-label={`Move phase ${phase.name} down`}
                                                                        >
                                                                            <ChevronDown size={14} />
                                                                        </button>

                                                                        {/* Edit / Rename */}
                                                                        <button
                                                                            type="button"
                                                                            data-testid={`edit-phase-button-${phase.id}`}
                                                                            onClick={() => handleOpenEditPhase(plan.id, phase)}
                                                                            className="inline-flex min-h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                                                                            title={t('clinical_plans.actions.edit_phase', 'Edit Phase')}
                                                                            aria-label={`Edit phase ${phase.name}`}
                                                                        >
                                                                            <Pencil size={13} />
                                                                        </button>

                                                                        {/* Delete Phase */}
                                                                        <button
                                                                            type="button"
                                                                            data-testid={`delete-phase-button-${phase.id}`}
                                                                            onClick={() => setDeletingPhase({ planId: plan.id, phaseId: phase.id, name: phase.name })}
                                                                            className="inline-flex min-h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-rose-600 hover:bg-rose-50 dark:border-slate-700 dark:bg-slate-800 dark:text-rose-400 dark:hover:bg-rose-950/30"
                                                                            title={t('clinical_plans.actions.delete_phase', 'Delete Phase')}
                                                                            aria-label={`Delete phase ${phase.name}`}
                                                                        >
                                                                            <Trash2 size={13} />
                                                                        </button>
                                                                    </>
                                                                )}

                                                                {/* Add Procedure button - only visible if plan is draft or proposed (Decision 4) */}
                                                                {canModifyPlan && (
                                                                    <button
                                                                        type="button"
                                                                        data-testid={`add-procedure-button-${phase.id}`}
                                                                        onClick={() => handleOpenAddProcedure(plan.id, phase.id, phase.name)}
                                                                        className="inline-flex min-h-11 items-center gap-1 rounded-xl border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-xs transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                                                                    >
                                                                        <Plus size={13} />
                                                                        <span>{t('clinical_plans.add_procedure', 'Add Procedure')}</span>
                                                                    </button>
                                                                )}
                                                            </div>
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
                                                                                {item.unpriced ? (
                                                                                    <span
                                                                                        data-testid={`item-unpriced-badge-${item.id}`}
                                                                                        className="rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                                                                                    >
                                                                                        {t('clinical_plans.unpriced', 'Unpriced')}
                                                                                    </span>
                                                                                ) : (
                                                                                    <span
                                                                                        data-testid={`item-estimate-${item.id}`}
                                                                                        className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                                                                                    >
                                                                                        {t('clinical_plans.estimate_abbr', 'Est')}: {formatCurrency(item.estimated_fee ?? 0, 'EGP', i18n.language)}
                                                                                    </span>
                                                                                )}
                                                                            </div>

                                                                            {/* Remove Procedure button - only visible if plan is draft or proposed (Decision 4) */}
                                                                            {canModifyPlan && (
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
                                                                            )}
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

            {/* Edit Phase Dialog */}
            <DentixDialog
                open={Boolean(editingPhase)}
                onOpenChange={(open) => {
                    if (!open) handleCloseEditPhase();
                }}
                title={t('clinical_plans.dialog.edit_phase_title', 'Edit Treatment Plan Phase')}
                size="md"
                closeLabel={t('common.close', 'Close')}
                closeOnOutside={!updatePhaseMutation.isPending}
            >
                <form
                    data-testid="edit-phase-dialog"
                    onSubmit={handleSubmitEditPhase}
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
                            onChange={(e) => setEditingPhase((prev) => ({ ...prev, name: e.target.value }))}
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
                            onChange={(e) => setEditingPhase((prev) => ({ ...prev, notes: e.target.value }))}
                            placeholder={t('clinical_plans.dialog.phase_notes_placeholder', 'Optional clinical instructions for this phase...')}
                            className="mt-1.5 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                        />
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                        <button
                            type="button"
                            onClick={handleCloseEditPhase}
                            disabled={updatePhaseMutation.isPending}
                            className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                            {t('common.cancel', 'Cancel')}
                        </button>
                        <button
                            type="submit"
                            data-testid="submit-edit-phase-button"
                            disabled={updatePhaseMutation.isPending || !editingPhase?.name?.trim()}
                            className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-600 dark:hover:bg-blue-500"
                        >
                            {updatePhaseMutation.isPending && (
                                <Loader2 size={16} className="animate-spin" />
                            )}
                            <span>{t('common.save', 'Save')}</span>
                        </button>
                    </div>
                </form>
            </DentixDialog>

            {/* Delete Phase Confirmation Dialog */}
            <DentixDialog
                open={Boolean(deletingPhase)}
                onOpenChange={(open) => {
                    if (!open && !deletePhaseMutation.isPending) setDeletingPhase(null);
                }}
                title={t('clinical_plans.dialog.delete_phase_title', 'Delete Phase')}
                size="sm"
                closeLabel={t('common.close', 'Close')}
                closeOnOutside={!deletePhaseMutation.isPending}
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
                            onClick={() => setDeletingPhase(null)}
                            disabled={deletePhaseMutation.isPending}
                            className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        >
                            {t('common.cancel', 'Cancel')}
                        </button>
                        <button
                            type="button"
                            data-testid="confirm-delete-phase-button"
                            onClick={handleConfirmDeletePhase}
                            disabled={deletePhaseMutation.isPending}
                            className="inline-flex min-h-11 items-center gap-1.5 rounded-xl bg-rose-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-rose-700 disabled:opacity-50"
                        >
                            {deletePhaseMutation.isPending && (
                                <Loader2 size={16} className="animate-spin" />
                            )}
                            <span>{t('common.delete', 'Delete')}</span>
                        </button>
                    </div>
                </div>
            </DentixDialog>
        </section>
    );
});

TreatmentPlansCard.displayName = 'TreatmentPlansCard';

TreatmentPlansCard.propTypes = {
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    activeOverlayPlanId: PropTypes.number,
    activeOverlayPhaseId: PropTypes.number,
    onToggleOverlay: PropTypes.func,
};

export default TreatmentPlansCard;
