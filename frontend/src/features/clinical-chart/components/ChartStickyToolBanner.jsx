import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { X, MousePointerClick } from 'lucide-react';

export default function ChartStickyToolBanner({
    activeTool,
    appliedCount = 0,
    onExit,
    onSurfaceToggle,
}) {
    const { t, i18n } = useTranslation();
    const isRtl = i18n?.language?.startsWith('ar');

    if (!activeTool || !activeTool.item) return null;

    const { item, targetKind, surfaces = [] } = activeTool;
    const isFinding = item.kind === 'finding';
    const displayName = isRtl ? item.nameAr || item.name : item.name;
    const isSurfaceCapable = item.allowed_target_kinds?.includes('surface');

    return (
        <div
            data-testid="chart-sticky-tool-banner"
            role="region"
            aria-live="polite"
            className="flex flex-col gap-3 rounded-2xl border-2 border-blue-500 bg-blue-50/95 p-3.5 shadow-sm dark:border-blue-400 dark:bg-blue-950/80 sm:flex-row sm:items-center sm:justify-between"
        >
            <div className="flex flex-wrap items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
                    <MousePointerClick className="h-5 w-5" aria-hidden="true" />
                </div>

                <div className="space-y-0.5">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-300">
                            {t('patient_details.chart.sticky_tool_active', 'Sticky Tool Active')}:
                        </span>
                        <span className="text-sm font-bold text-slate-900 dark:text-white">
                            {displayName}
                        </span>
                        <span
                            className={`rounded px-1.5 py-0.2 text-[10px] font-semibold ${
                                isFinding
                                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                                    : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
                            }`}
                        >
                            {isFinding
                                ? t('patient_details.chart.finding_badge', 'Finding')
                                : t('patient_details.chart.procedure_badge', 'Procedure')}
                        </span>
                        {appliedCount > 0 && (
                            <span
                                data-testid="sticky-applied-count"
                                className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-bold text-white shadow-sm"
                            >
                                {t('patient_details.chart.sticky_applied', {
                                    count: appliedCount,
                                    defaultValue: `Applied: ${appliedCount}`,
                                })}
                            </span>
                        )}
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300">
                        {t(
                            'patient_details.chart.sticky_instructions',
                            'Click teeth on the chart to apply. Press Esc or click Exit when done.'
                        )}
                    </p>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
                {isSurfaceCapable && targetKind === 'surface' && onSurfaceToggle && (
                    <div className="flex items-center gap-1 rounded-xl border border-blue-200 bg-white/80 p-1 dark:border-blue-800 dark:bg-slate-900/80">
                        <span className="px-1 text-[11px] font-bold text-slate-500">
                            {t('patient_details.chart.surfaces', 'Surfaces')}:
                        </span>
                        {['M', 'D', 'O', 'I', 'B', 'L', 'P'].map((surf) => {
                            const isSelected = surfaces.includes(surf);
                            return (
                                <button
                                    key={surf}
                                    type="button"
                                    onClick={() => onSurfaceToggle(surf)}
                                    aria-pressed={isSelected}
                                    data-testid={`sticky-surface-pill-${surf}`}
                                    className={`min-h-11 min-w-11 rounded-lg px-2.5 py-1 text-xs font-bold transition-all ${
                                        isSelected
                                            ? 'bg-blue-600 text-white shadow-sm'
                                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                                    }`}
                                >
                                    {surf}
                                </button>
                            );
                        })}
                    </div>
                )}

                <button
                    type="button"
                    onClick={onExit}
                    data-testid="exit-sticky-mode-button"
                    className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-blue-300 bg-white px-3.5 py-2 text-xs font-bold text-blue-900 shadow-sm transition-colors hover:bg-blue-50 dark:border-blue-700 dark:bg-slate-900 dark:text-blue-200 dark:hover:bg-slate-800"
                >
                    <X className="h-4 w-4" aria-hidden="true" />
                    <span>{t('patient_details.chart.exit_sticky', 'Exit Sticky Mode')}</span>
                    <kbd className="ms-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        Esc
                    </kbd>
                </button>
            </div>
        </div>
    );
}

ChartStickyToolBanner.propTypes = {
    activeTool: PropTypes.shape({
        item: PropTypes.object.isRequired,
        targetKind: PropTypes.string,
        surfaces: PropTypes.arrayOf(PropTypes.string),
    }),
    appliedCount: PropTypes.number,
    onExit: PropTypes.func.isRequired,
    onSurfaceToggle: PropTypes.func,
};
