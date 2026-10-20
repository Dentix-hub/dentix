import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import {
    Calendar,
    CheckCircle2,
    ChevronDown,
    ChevronUp,
    FileText,
    Layers,
    Loader2,
    Plus,
    Send,
    XCircle,
} from 'lucide-react';
import { formatCurrency } from '@/utils/formatters';
import PlanPhaseCard from './PlanPhaseCard';

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

export default function PlanCard({
    plan,
    isExpanded,
    onToggleExpand,
    canModifyPlan,
    activeOverlayPlanId,
    activeOverlayPhaseId,
    onToggleOverlay,
    onTransitionPlan,
    isTransitionPending,
    onAddPhase,
    isAddPhasePending,
    onMovePhaseUp,
    onMovePhaseDown,
    onOpenEditPhase,
    onDeletePhase,
    onOpenAddProcedure,
    onRemoveItem,
    isReorderPending,
    isRemoveItemPending,
    isNativeWritesEnabled = false,
    onPerformItem,
}) {
    const { t, i18n } = useTranslation();
    const phasesCount = plan.phases?.length || 0;
    const allPlanItems = (plan.phases || []).flatMap((p) => p.items || []);
    const planCompletedItems = allPlanItems.filter(
        (it) => (it.work_item?.status || it.status) === 'completed'
    ).length;
    const planTotalItems = allPlanItems.length;
    const formattedDate = plan.created_at
        ? new Date(plan.created_at).toLocaleDateString(i18n.language, {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
          })
        : '';

    return (
        <div
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
                        {planTotalItems > 0 && (
                            <span
                                data-testid={`plan-progress-${plan.id}`}
                                className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                            >
                                {t('clinical_plans.progress_done', '{{completed}} of {{total}} done', {
                                    completed: planCompletedItems,
                                    total: planTotalItems,
                                })}
                            </span>
                        )}
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
                                onClick={() => onTransitionPlan(plan, 'proposed')}
                                disabled={isTransitionPending}
                                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-xs font-semibold text-blue-700 shadow-sm transition-colors hover:bg-blue-100 disabled:opacity-50 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300 dark:hover:bg-blue-900/50"
                            >
                                <Send size={13} />
                                <span>{t('clinical_plans.actions.propose', 'Propose')}</span>
                            </button>
                            <button
                                type="button"
                                data-testid={`plan-transition-cancelled-${plan.id}`}
                                onClick={() => onTransitionPlan(plan, 'cancelled')}
                                disabled={isTransitionPending}
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
                                onClick={() => onTransitionPlan(plan, 'accepted')}
                                disabled={isTransitionPending}
                                className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-semibold text-emerald-700 shadow-sm transition-colors hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 dark:hover:bg-emerald-900/50"
                            >
                                <CheckCircle2 size={13} />
                                <span>{t('clinical_plans.actions.accept', 'Accept')}</span>
                            </button>
                            <button
                                type="button"
                                data-testid={`plan-transition-cancelled-${plan.id}`}
                                onClick={() => onTransitionPlan(plan, 'cancelled')}
                                disabled={isTransitionPending}
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
                                onClick={() => onTransitionPlan(plan, 'completed')}
                                disabled={isTransitionPending}
                                className="inline-flex items-center gap-1 rounded-lg border border-purple-200 bg-purple-50 px-2.5 py-1.5 text-xs font-semibold text-purple-700 shadow-sm transition-colors hover:bg-purple-100 disabled:opacity-50 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-300 dark:hover:bg-purple-900/50"
                            >
                                <CheckCircle2 size={13} />
                                <span>{t('clinical_plans.actions.complete', 'Complete')}</span>
                            </button>
                            <button
                                type="button"
                                data-testid={`plan-transition-cancelled-${plan.id}`}
                                onClick={() => onTransitionPlan(plan, 'cancelled')}
                                disabled={isTransitionPending}
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
                            onClick={() => onAddPhase(plan)}
                            disabled={isAddPhasePending}
                            className="inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition-colors hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                        >
                            {isAddPhasePending ? (
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
                        onClick={onToggleExpand}
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
                        <PlanPhaseCard
                            key={phase.id}
                            plan={plan}
                            phase={phase}
                            idx={idx}
                            canModifyPlan={canModifyPlan}
                            activeOverlayPlanId={activeOverlayPlanId}
                            activeOverlayPhaseId={activeOverlayPhaseId}
                            onToggleOverlay={onToggleOverlay}
                            onMovePhaseUp={onMovePhaseUp}
                            onMovePhaseDown={onMovePhaseDown}
                            onOpenEditPhase={onOpenEditPhase}
                            onDeletePhase={onDeletePhase}
                            onOpenAddProcedure={onOpenAddProcedure}
                            onRemoveItem={onRemoveItem}
                            isReorderPending={isReorderPending}
                            isRemoveItemPending={isRemoveItemPending}
                            isNativeWritesEnabled={isNativeWritesEnabled}
                            onPerformItem={onPerformItem}
                        />
                    ))}
                </div>
            )}
        </div>
    );
}

PlanCard.propTypes = {
    plan: PropTypes.shape({
        id: PropTypes.number.isRequired,
        title: PropTypes.string.isRequired,
        status: PropTypes.string.isRequired,
        plan_estimated_total: PropTypes.number,
        unpriced_items_count: PropTypes.number,
        created_at: PropTypes.string,
        notes: PropTypes.string,
        phases: PropTypes.array,
    }).isRequired,
    isExpanded: PropTypes.bool.isRequired,
    onToggleExpand: PropTypes.func.isRequired,
    canModifyPlan: PropTypes.bool,
    activeOverlayPlanId: PropTypes.number,
    activeOverlayPhaseId: PropTypes.number,
    onToggleOverlay: PropTypes.func,
    onTransitionPlan: PropTypes.func.isRequired,
    isTransitionPending: PropTypes.bool,
    onAddPhase: PropTypes.func.isRequired,
    isAddPhasePending: PropTypes.bool,
    onMovePhaseUp: PropTypes.func.isRequired,
    onMovePhaseDown: PropTypes.func.isRequired,
    onOpenEditPhase: PropTypes.func.isRequired,
    onDeletePhase: PropTypes.func.isRequired,
    onOpenAddProcedure: PropTypes.func.isRequired,
    onRemoveItem: PropTypes.func.isRequired,
    isReorderPending: PropTypes.bool,
    isRemoveItemPending: PropTypes.bool,
    isNativeWritesEnabled: PropTypes.bool,
    onPerformItem: PropTypes.func,
};
