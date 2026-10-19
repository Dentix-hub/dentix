import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import {
    ChevronDown,
    ChevronUp,
    Layers,
    Pencil,
    Plus,
    Trash2,
} from 'lucide-react';
import { formatCurrency } from '@/utils/formatters';
import PlanItemRow from './PlanItemRow';

export default function PlanPhaseCard({
    plan,
    phase,
    idx,
    canModifyPlan,
    activeOverlayPlanId,
    activeOverlayPhaseId,
    onToggleOverlay,
    onMovePhaseUp,
    onMovePhaseDown,
    onOpenEditPhase,
    onDeletePhase,
    onOpenAddProcedure,
    onRemoveItem,
    isReorderPending,
    isRemoveItemPending,
}) {
    const { t, i18n } = useTranslation();

    return (
        <div
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
                                disabled={idx === 0 || isReorderPending}
                                onClick={() => onMovePhaseUp(plan, idx)}
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
                                disabled={idx === (plan.phases || []).length - 1 || isReorderPending}
                                onClick={() => onMovePhaseDown(plan, idx)}
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
                                onClick={() => onOpenEditPhase(plan.id, phase)}
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
                                onClick={() => onDeletePhase({ planId: plan.id, phaseId: phase.id, name: phase.name })}
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
                            onClick={() => onOpenAddProcedure(plan.id, phase.id, phase.name)}
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
                    phase.items.map((item) => (
                        <PlanItemRow
                            key={item.id}
                            item={item}
                            canModifyPlan={canModifyPlan}
                            onRemoveItem={() => onRemoveItem(plan.id, phase.id, item.id)}
                            isRemovePending={isRemoveItemPending}
                        />
                    ))
                )}
            </div>
        </div>
    );
}

PlanPhaseCard.propTypes = {
    plan: PropTypes.shape({
        id: PropTypes.number.isRequired,
        phases: PropTypes.array,
    }).isRequired,
    phase: PropTypes.shape({
        id: PropTypes.number.isRequired,
        phase_order: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        status: PropTypes.string,
        notes: PropTypes.string,
        phase_estimated_total: PropTypes.number,
        unpriced_items_count: PropTypes.number,
        items: PropTypes.array,
    }).isRequired,
    idx: PropTypes.number.isRequired,
    canModifyPlan: PropTypes.bool,
    activeOverlayPlanId: PropTypes.number,
    activeOverlayPhaseId: PropTypes.number,
    onToggleOverlay: PropTypes.func,
    onMovePhaseUp: PropTypes.func.isRequired,
    onMovePhaseDown: PropTypes.func.isRequired,
    onOpenEditPhase: PropTypes.func.isRequired,
    onDeletePhase: PropTypes.func.isRequired,
    onOpenAddProcedure: PropTypes.func.isRequired,
    onRemoveItem: PropTypes.func.isRequired,
    isReorderPending: PropTypes.bool,
    isRemoveItemPending: PropTypes.bool,
};
