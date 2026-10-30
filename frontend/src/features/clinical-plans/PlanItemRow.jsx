import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { Play, Trash2 } from 'lucide-react';
import { formatCurrency } from '@/utils/formatters';

export default function PlanItemRow({
    item,
    plan,
    canModifyPlan,
    onRemoveItem,
    isRemovePending,
    isNativeWritesEnabled = false,
    onPerformItem,
}) {
    const { t, i18n } = useTranslation();

    const targets = item.work_item?.targets || [];
    const toothKeys = Array.from(new Set(targets.map((tg) => tg.tooth_key).filter(Boolean)));
    const isSingleTooth = toothKeys.length === 1;
    const surfaces = targets.map((tg) => tg.surface || tg.surface_code).filter(Boolean);

    const isProcedure = (item.work_item?.kind || 'procedure') === 'procedure';
    const isOpenStatus = ['open', 'proposed', 'planned', 'active', 'scheduled', 'in_progress'].includes(item.work_item?.status);
    const isPlanAccepted = plan?.status === 'accepted';
    const canPerformNow = !isNativeWritesEnabled && isPlanAccepted && isProcedure && isOpenStatus && isSingleTooth;

    const targetsDesc = targets
        .map((tg) =>
            tg.tooth_key
                ? `${tg.tooth_key}${tg.surface || tg.surface_code ? ` (${tg.surface || tg.surface_code})` : ''}`
                : ''
        )
        .filter(Boolean)
        .join(', ');

    return (
        <div
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

            <div className="flex items-center gap-1.5">
                {/* Perform now button (U2.3): when native writes OFF, accepted plan, open procedure, single tooth */}
                {canPerformNow && (
                    <button
                        type="button"
                        data-testid={`perform-plan-item-${item.id}`}
                        onClick={() => onPerformItem?.({ item, plan, toothKey: toothKeys[0], surfaces })}
                        title={t('clinical_plans.perform_now', 'Perform now')}
                        aria-label={t('clinical_plans.perform_now', 'Perform now')}
                        className="inline-flex min-h-7 items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/50 dark:text-emerald-300 dark:hover:bg-emerald-900/60 transition-colors"
                    >
                        <Play size={11} className="fill-current" />
                        <span>{t('clinical_plans.perform_now', 'Perform now')}</span>
                    </button>
                )}

                {/* Remove Procedure button - only visible if plan is draft or proposed (Decision 4) */}
                {canModifyPlan && (
                    <button
                        type="button"
                        data-testid={`remove-phase-item-${item.id}`}
                        onClick={onRemoveItem}
                        disabled={isRemovePending}
                        title={t('clinical_plans.remove_procedure', 'Remove procedure from phase')}
                        aria-label={t('clinical_plans.remove_procedure', 'Remove procedure from phase')}
                        className="inline-flex h-6 w-6 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30 dark:hover:text-red-400"
                    >
                        <Trash2 size={13} />
                    </button>
                )}
            </div>
        </div>
    );
}

PlanItemRow.propTypes = {
    item: PropTypes.shape({
        id: PropTypes.number.isRequired,
        unpriced: PropTypes.bool,
        estimated_fee: PropTypes.number,
        work_item: PropTypes.shape({
            id: PropTypes.number,
            kind: PropTypes.string,
            display_name: PropTypes.string,
            procedure_code: PropTypes.string,
            code: PropTypes.string,
            status: PropTypes.string,
            targets: PropTypes.arrayOf(
                PropTypes.shape({
                    tooth_key: PropTypes.string,
                    surface: PropTypes.string,
                    surface_code: PropTypes.string,
                })
            ),
        }),
    }).isRequired,
    plan: PropTypes.shape({
        id: PropTypes.number,
        status: PropTypes.string,
    }),
    canModifyPlan: PropTypes.bool,
    onRemoveItem: PropTypes.func.isRequired,
    isRemovePending: PropTypes.bool,
    isNativeWritesEnabled: PropTypes.bool,
    onPerformItem: PropTypes.func,
};
