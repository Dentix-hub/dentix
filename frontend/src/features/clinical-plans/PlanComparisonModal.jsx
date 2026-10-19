import { memo, useState, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import {
    CheckCircle2,
    ArrowLeftRight,
    AlertCircle,
} from 'lucide-react';
import { DentixDialog } from '@/shared/ui';
import { formatCurrency } from '@/utils/formatters';

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

const extractTargetTeeth = (plan) => {
    const teeth = new Set();
    (plan?.phases || []).forEach((phase) => {
        (phase.items || []).forEach((item) => {
            (item.work_item?.targets || []).forEach((target) => {
                if (target.tooth_key !== null && target.tooth_key !== undefined) {
                    teeth.add(String(target.tooth_key));
                }
            });
        });
    });
    return Array.from(teeth).sort((a, b) => {
        const numA = parseInt(a, 10);
        const numB = parseInt(b, 10);
        return isNaN(numA) || isNaN(numB) ? a.localeCompare(b) : numA - numB;
    });
};

const PlanComparisonModal = memo(({
    open,
    onClose,
    plans = [],
    onAcceptPlan,
    isTransitionPending = false,
}) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar' || document.documentElement.dir === 'rtl';

    const [selectedPlanAId, setSelectedPlanAId] = useState(null);
    const [selectedPlanBId, setSelectedPlanBId] = useState(null);

    // Synchronize initial selections when modal opens or plans change
    useEffect(() => {
        if (!open || plans.length === 0) return;
        setSelectedPlanAId((prev) => {
            if (prev && plans.some((p) => p.id === prev)) return prev;
            return plans[0]?.id ?? null;
        });
        setSelectedPlanBId((prev) => {
            if (prev && plans.some((p) => p.id === prev)) return prev;
            return plans[1]?.id ?? plans[0]?.id ?? null;
        });
    }, [open, plans]);

    const planA = useMemo(() => {
        return plans.find((p) => p.id === selectedPlanAId) || plans[0] || null;
    }, [plans, selectedPlanAId]);

    const planB = useMemo(() => {
        return plans.find((p) => p.id === selectedPlanBId) || plans[1] || plans[0] || null;
    }, [plans, selectedPlanBId]);

    const teethA = useMemo(() => extractTargetTeeth(planA), [planA]);
    const teethB = useMemo(() => extractTargetTeeth(planB), [planB]);

    const itemsA = useMemo(() => {
        return (planA?.phases || []).flatMap((ph) => ph.items || []);
    }, [planA]);

    const itemsB = useMemo(() => {
        return (planB?.phases || []).flatMap((ph) => ph.items || []);
    }, [planB]);

    const workItemIdsA = useMemo(() => {
        return new Set(itemsA.map((it) => it.work_item_id).filter(Boolean));
    }, [itemsA]);

    const workItemIdsB = useMemo(() => {
        return new Set(itemsB.map((it) => it.work_item_id).filter(Boolean));
    }, [itemsB]);

    const sharedWorkItemIds = useMemo(() => {
        return new Set([...workItemIdsA].filter((id) => workItemIdsB.has(id)));
    }, [workItemIdsA, workItemIdsB]);

    const sharedCount = sharedWorkItemIds.size;
    const uniqueCountA = workItemIdsA.size - sharedCount;
    const uniqueCountB = workItemIdsB.size - sharedCount;

    const costDiff = useMemo(() => {
        if (!planA || !planB) return 0;
        return Math.abs((planA.plan_estimated_total ?? 0) - (planB.plan_estimated_total ?? 0));
    }, [planA, planB]);

    const isIdenticalPlanSelected = planA?.id && planB?.id && planA.id === planB.id;

    if (!open) return null;

    const renderPlanColumn = (plan, teeth, columnKey, testIdPrefix) => {
        if (!plan) return null;

        const isProposed = plan.status === 'proposed';
        const isAccepted = plan.status === 'accepted';
        const phases = plan.phases || [];

        return (
            <div
                data-testid={testIdPrefix}
                className="flex flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-slate-800 dark:bg-slate-900 sm:p-5"
            >
                {/* Column Header */}
                <div className="border-b border-slate-100 pb-4 dark:border-slate-800">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <h4 className="text-base font-bold text-slate-800 dark:text-white">
                            {plan.title}
                        </h4>
                        <span
                            data-testid={`comparison-plan-status-${plan.id}`}
                            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${getStatusBadgeClass(
                                plan.status
                            )}`}
                        >
                            {t(`clinical_plans.status.${plan.status}`, plan.status)}
                        </span>
                    </div>

                    {plan.notes && (
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                            {plan.notes}
                        </p>
                    )}

                    {/* Quick Metrics Bar */}
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 dark:border-slate-800 dark:bg-slate-800/40">
                            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                                {t('clinical_plans.estimate', 'Estimate')}
                            </span>
                            <div
                                data-testid={`comparison-plan-estimate-${plan.id}`}
                                className="mt-0.5 font-bold text-emerald-700 dark:text-emerald-400"
                            >
                                {t('clinical_plans.estimate', 'Estimate')}: {formatCurrency(plan.plan_estimated_total ?? 0, 'EGP', i18n.language)}
                                {plan.unpriced_items_count > 0 && (
                                    <span
                                        data-testid={`comparison-plan-unpriced-${plan.id}`}
                                        className="ltr:ml-1 rtl:mr-1 text-amber-600 dark:text-amber-400 font-bold"
                                        title={t('clinical_plans.contains_unpriced', 'Contains unpriced procedures')}
                                    >
                                        *
                                    </span>
                                )}
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-2.5 dark:border-slate-800 dark:bg-slate-800/40">
                            <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                                {t('clinical_plans.comparison.phases', 'Phases')}
                            </span>
                            <div
                                data-testid={`comparison-plan-phase-count-${plan.id}`}
                                className="mt-0.5 font-bold text-slate-800 dark:text-white"
                            >
                                {phases.length}{' '}
                                {phases.length === 1
                                    ? t('clinical_plans.phases_count', 'Phase')
                                    : t('clinical_plans.phases_count_plural', 'Phases')}
                            </div>
                        </div>
                    </div>

                    {/* Target Teeth */}
                    <div className="mt-2.5 flex items-baseline gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                        <span className="shrink-0 font-medium text-slate-500 dark:text-slate-400">
                            {t('clinical_plans.comparison.target_teeth', 'Target Teeth')}:
                        </span>
                        <span
                            data-testid={`comparison-plan-teeth-${plan.id}`}
                            className="font-semibold text-slate-800 dark:text-white"
                        >
                            {teeth.length > 0 ? teeth.join(', ') : t('clinical_plans.comparison.none', 'None')}
                        </span>
                    </div>

                    {/* Action: Direct Accept Button */}
                    <div className="mt-4">
                        {isProposed && (
                            <button
                                type="button"
                                data-testid={`comparison-accept-plan-${plan.id}`}
                                disabled={isTransitionPending}
                                onClick={() => onAcceptPlan?.(plan)}
                                className="inline-flex w-full min-h-10 items-center justify-center gap-1.5 rounded-xl bg-emerald-600 px-3.5 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 disabled:opacity-50"
                            >
                                <CheckCircle2 size={16} aria-hidden="true" />
                                <span>{t('clinical_plans.actions.accept', 'Accept Plan')}</span>
                            </button>
                        )}
                        {isAccepted && (
                            <div
                                data-testid={`comparison-accepted-status-${plan.id}`}
                                className="inline-flex w-full min-h-10 items-center justify-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50/70 px-3.5 py-2 text-xs font-bold text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                            >
                                <CheckCircle2 size={16} aria-hidden="true" />
                                <span>{t('clinical_plans.comparison.currently_accepted', 'Currently Accepted')}</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Phases and Procedures */}
                <div className="mt-4 flex-1 space-y-3 overflow-y-auto max-h-[420px] ltr:pr-1 rtl:pl-1">
                    {phases.length === 0 ? (
                        <p className="py-4 text-center text-xs text-slate-400 dark:text-slate-500">
                            {t('clinical_plans.comparison.no_procedures', 'No procedures attached to this plan.')}
                        </p>
                    ) : (
                        phases.map((phase) => (
                            <div
                                key={phase.id}
                                className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 dark:border-slate-800/80 dark:bg-slate-800/30"
                            >
                                <div className="flex items-center justify-between gap-2 border-b border-slate-200/50 pb-2 dark:border-slate-700/50">
                                    <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                                        {phase.name}
                                    </span>
                                    <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                                        {formatCurrency(phase.phase_estimated_total ?? 0, 'EGP', i18n.language)}
                                    </span>
                                </div>

                                <div className="mt-2 space-y-2">
                                    {(phase.items || []).length === 0 ? (
                                        <p className="text-[11px] text-slate-400 dark:text-slate-500">
                                            {t('clinical_plans.no_procedures_in_phase', 'No procedures attached to this phase yet.')}
                                        </p>
                                    ) : (
                                        (phase.items || []).map((item) => {
                                            const isShared = sharedWorkItemIds.has(item.work_item_id);
                                            const targets = item.work_item?.targets || [];
                                            const toothLabels = targets
                                                .map((t) => (t.surface ? `${t.tooth_key} (${t.surface})` : t.tooth_key))
                                                .filter(Boolean)
                                                .join(', ');

                                            return (
                                                <div
                                                    key={item.id}
                                                    className="flex flex-col gap-1 rounded-lg border border-slate-200/60 bg-white p-2 text-xs shadow-2xs dark:border-slate-700/60 dark:bg-slate-900/60"
                                                >
                                                    <div className="flex items-start justify-between gap-2">
                                                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                                                            {item.work_item?.display_name || item.work_item?.procedure_code || `#${item.work_item_id}`}
                                                        </span>
                                                        {isShared ? (
                                                            <span
                                                                data-testid={`procedure-shared-badge-${item.id}`}
                                                                className="shrink-0 inline-flex items-center rounded-md border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-300"
                                                            >
                                                                {t('clinical_plans.comparison.shared', 'Shared')}
                                                            </span>
                                                        ) : (
                                                            <span
                                                                data-testid={`procedure-unique-badge-${item.id}`}
                                                                className="shrink-0 inline-flex items-center rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                                                            >
                                                                {t('clinical_plans.comparison.unique', 'Unique')}
                                                            </span>
                                                        )}
                                                    </div>

                                                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                                                        <span>{toothLabels ? `${t('clinical_plans.add_procedure_dialog.teeth', 'Teeth')}: ${toothLabels}` : ''}</span>
                                                        <span className="font-medium text-slate-700 dark:text-slate-300">
                                                            {item.unpriced
                                                                ? t('clinical_plans.unpriced', 'Unpriced')
                                                                : formatCurrency(item.estimated_fee ?? 0, 'EGP', i18n.language)}
                                                        </span>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        );
    };

    return (
        <DentixDialog
            open={open}
            onOpenChange={(nextOpen) => {
                if (!nextOpen) onClose?.();
            }}
            title={t('clinical_plans.comparison.title', 'Compare Treatment Plans')}
            size="4xl"
            closeLabel={t('common.close', 'Close')}
        >
            <div
                data-testid="compare-clinical-plans-dialog"
                className="space-y-4"
                dir={isRtl ? 'rtl' : 'ltr'}
            >
                <p className="text-xs text-slate-500 dark:text-slate-400">
                    {t(
                        'clinical_plans.comparison.subtitle',
                        'Side-by-side comparison of treatment options, phases, and dynamic estimates'
                    )}
                </p>

                {/* Plan Selectors when there are > 2 plans */}
                {plans.length > 2 && (
                    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                        <div className="min-w-[180px] flex-1">
                            <label
                                htmlFor="compare-plan-a-select"
                                className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1"
                            >
                                {t('clinical_plans.comparison.select_plan_a', 'First Plan')}
                            </label>
                            <select
                                id="compare-plan-a-select"
                                data-testid="compare-plan-a-select"
                                value={planA?.id ?? ''}
                                onChange={(e) => setSelectedPlanAId(Number(e.target.value))}
                                className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                            >
                                {plans.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.title} ({t(`clinical_plans.status.${p.status}`, p.status)})
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="hidden md:flex items-center justify-center pt-5 text-slate-400">
                            <ArrowLeftRight size={18} />
                        </div>

                        <div className="min-w-[180px] flex-1">
                            <label
                                htmlFor="compare-plan-b-select"
                                className="block text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1"
                            >
                                {t('clinical_plans.comparison.select_plan_b', 'Second Plan')}
                            </label>
                            <select
                                id="compare-plan-b-select"
                                data-testid="compare-plan-b-select"
                                value={planB?.id ?? ''}
                                onChange={(e) => setSelectedPlanBId(Number(e.target.value))}
                                className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                            >
                                {plans.map((p) => (
                                    <option key={p.id} value={p.id}>
                                        {p.title} ({t(`clinical_plans.status.${p.status}`, p.status)})
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                )}

                {/* Warning if identical plan selected in both dropdowns */}
                {isIdenticalPlanSelected && (
                    <div
                        data-testid="comparison-identical-warning"
                        className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-400"
                    >
                        <AlertCircle size={16} className="shrink-0" />
                        <span>
                            {t(
                                'clinical_plans.comparison.identical_plans_warning',
                                'Please select two different plans to compare.'
                            )}
                        </span>
                    </div>
                )}

                {/* Summary Comparison Metrics Banner */}
                <div
                    data-testid="comparison-summary-banner"
                    className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 rounded-xl border border-slate-200/80 bg-slate-50/50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/20"
                >
                    <div className="text-center">
                        <span className="block text-[11px] text-slate-500 dark:text-slate-400">
                            {t('clinical_plans.comparison.shared_procedures', 'Shared Procedures')}
                        </span>
                        <span
                            data-testid="comparison-shared-count"
                            className="mt-0.5 inline-block text-sm font-bold text-sky-700 dark:text-sky-400"
                        >
                            {sharedCount}
                        </span>
                    </div>

                    <div className="text-center">
                        <span className="block text-[11px] text-slate-500 dark:text-slate-400">
                            {planA?.title || t('clinical_plans.comparison.select_plan_a', 'Plan A')} ({t('clinical_plans.comparison.unique', 'Unique')})
                        </span>
                        <span
                            data-testid="comparison-unique-count-a"
                            className="mt-0.5 inline-block text-sm font-bold text-amber-700 dark:text-amber-400"
                        >
                            {uniqueCountA}
                        </span>
                    </div>

                    <div className="text-center">
                        <span className="block text-[11px] text-slate-500 dark:text-slate-400">
                            {planB?.title || t('clinical_plans.comparison.select_plan_b', 'Plan B')} ({t('clinical_plans.comparison.unique', 'Unique')})
                        </span>
                        <span
                            data-testid="comparison-unique-count-b"
                            className="mt-0.5 inline-block text-sm font-bold text-amber-700 dark:text-amber-400"
                        >
                            {uniqueCountB}
                        </span>
                    </div>

                    <div className="text-center">
                        <span className="block text-[11px] text-slate-500 dark:text-slate-400">
                            {t('clinical_plans.comparison.cost_difference', 'Cost Difference')}
                        </span>
                        <span
                            data-testid="comparison-cost-diff"
                            className="mt-0.5 inline-block text-sm font-bold text-emerald-700 dark:text-emerald-400"
                        >
                            {formatCurrency(costDiff, 'EGP', i18n.language)}
                        </span>
                    </div>
                </div>

                {/* Side-by-Side Columns */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {renderPlanColumn(planA, teethA, 'planA', 'comparison-column-plan-a')}
                    {renderPlanColumn(planB, teethB, 'planB', 'comparison-column-plan-b')}
                </div>
            </div>
        </DentixDialog>
    );
});

PlanComparisonModal.displayName = 'PlanComparisonModal';

PlanComparisonModal.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    plans: PropTypes.arrayOf(PropTypes.object),
    onAcceptPlan: PropTypes.func,
    isTransitionPending: PropTypes.bool,
};

export default PlanComparisonModal;
