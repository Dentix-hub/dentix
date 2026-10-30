import { memo, useState } from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import {
    ChevronDown,
    ChevronUp,
    ClipboardList,
    Plus,
    Loader2,
    GitCompare,
} from 'lucide-react';
import { toast } from '@/shared/ui';
import PlanComparisonModal from './PlanComparisonModal';
import PlanCreateModal from './PlanCreateModal';
import AddProcedureModal from './AddProcedureModal';
import EditPhaseModal from './EditPhaseModal';
import DeletePhaseConfirm from './DeletePhaseConfirm';
import PlanCard from './PlanCard';
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

const TreatmentPlansCard = memo(({
    patientId,
    activeOverlayPlanId = null,
    activeOverlayPhaseId = null,
    onToggleOverlay,
    onPerformItem,
    isNativeWritesEnabled = false,
}) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar' || document.documentElement.dir === 'rtl';

    const [isCollapsed, setIsCollapsed] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [isCompareOpen, setIsCompareOpen] = useState(false);
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

    const nonCancelledPlans = plans.filter((p) => p.status !== 'cancelled');
    const canComparePlans = nonCancelledPlans.length >= 2;

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
                    {canComparePlans && (
                        <button
                            type="button"
                            data-testid="compare-clinical-plans-button"
                            onClick={() => setIsCompareOpen(true)}
                            className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                        >
                            <GitCompare size={16} aria-hidden="true" />
                            <span>{t('clinical_plans.compare_plans', 'Compare Plans')}</span>
                        </button>
                    )}

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
                            {plans.map((plan) => (
                                <PlanCard
                                    key={plan.id}
                                    plan={plan}
                                    isExpanded={isPlanExpanded(plan.id)}
                                    onToggleExpand={() => togglePlanExpanded(plan.id)}
                                    canModifyPlan={plan.status === 'draft' || plan.status === 'proposed'}
                                    activeOverlayPlanId={activeOverlayPlanId}
                                    activeOverlayPhaseId={activeOverlayPhaseId}
                                    onToggleOverlay={onToggleOverlay}
                                    onTransitionPlan={handleTransitionPlan}
                                    isTransitionPending={transitionPlanMutation.isPending}
                                    onAddPhase={handleAddPhase}
                                    isAddPhasePending={addPhaseMutation.isPending}
                                    onMovePhaseUp={handleMovePhaseUp}
                                    onMovePhaseDown={handleMovePhaseDown}
                                    onOpenEditPhase={handleOpenEditPhase}
                                    onDeletePhase={setDeletingPhase}
                                    onOpenAddProcedure={handleOpenAddProcedure}
                                    onRemoveItem={handleRemoveItem}
                                    isReorderPending={reorderPhasesMutation.isPending}
                                    isRemoveItemPending={removePlanItemMutation.isPending}
                                    isNativeWritesEnabled={isNativeWritesEnabled}
                                    onPerformItem={onPerformItem}
                                />
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Create Plan Dialog */}
            <PlanCreateModal
                open={isCreateOpen}
                onClose={handleCloseCreate}
                onSubmit={handleSubmitCreate}
                title={title}
                setTitle={setTitle}
                notes={notes}
                setNotes={setNotes}
                isPending={createPlanMutation.isPending}
                isRtl={isRtl}
            />

            {/* Add Procedure Dialog */}
            <AddProcedureModal
                open={procedureModal.open}
                phaseName={procedureModal.phaseName}
                onClose={handleCloseAddProcedure}
                onSubmit={handleSubmitAddProcedure}
                isLoading={isCandidatesLoading}
                candidates={availableCandidates}
                selectedWorkItemId={selectedWorkItemId}
                onSelectWorkItemId={setSelectedWorkItemId}
                isPending={addPlanItemMutation.isPending}
                isRtl={isRtl}
            />

            {/* Edit Phase Dialog */}
            <EditPhaseModal
                editingPhase={editingPhase}
                onClose={handleCloseEditPhase}
                onSubmit={handleSubmitEditPhase}
                onChangeName={(name) => setEditingPhase((prev) => ({ ...prev, name }))}
                onChangeNotes={(notesVal) => setEditingPhase((prev) => ({ ...prev, notes: notesVal }))}
                isPending={updatePhaseMutation.isPending}
                isRtl={isRtl}
            />

            {/* Delete Phase Confirmation Dialog */}
            <DeletePhaseConfirm
                deletingPhase={deletingPhase}
                onClose={() => setDeletingPhase(null)}
                onConfirm={handleConfirmDeletePhase}
                isPending={deletePhaseMutation.isPending}
                isRtl={isRtl}
            />

            {/* Plan Comparison Modal */}
            <PlanComparisonModal
                open={isCompareOpen}
                onClose={() => setIsCompareOpen(false)}
                plans={nonCancelledPlans}
                onAcceptPlan={(plan) => handleTransitionPlan(plan, 'accepted')}
                isTransitionPending={transitionPlanMutation.isPending}
            />
        </section>
    );
});

TreatmentPlansCard.displayName = 'TreatmentPlansCard';

TreatmentPlansCard.propTypes = {
    patientId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    activeOverlayPlanId: PropTypes.number,
    activeOverlayPhaseId: PropTypes.number,
    onToggleOverlay: PropTypes.func,
    onPerformItem: PropTypes.func,
    isNativeWritesEnabled: PropTypes.bool,
};

export default TreatmentPlansCard;
