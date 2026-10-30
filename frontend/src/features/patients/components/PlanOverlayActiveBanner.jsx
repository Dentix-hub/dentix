import PropTypes from 'prop-types';

export default function PlanOverlayActiveBanner({ planOverlay, onToggleOverlay, t }) {
    if (!planOverlay) return null;

    return (
        <div
            data-testid="plan-overlay-active-banner"
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-blue-200 bg-blue-50/80 p-3 shadow-sm dark:border-blue-900/60 dark:bg-blue-950/40"
        >
            <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                    <span className="flex h-2.5 w-2.5 rounded-full bg-blue-600 animate-pulse" />
                    <span className="text-xs font-bold text-blue-900 dark:text-blue-200">
                        {t('clinical_plans.overlay.active_banner', 'Plan Overlay Active')}:
                    </span>
                    <span className="text-xs font-extrabold text-blue-700 dark:text-blue-300">
                        {planOverlay.planTitle}
                        {planOverlay.phaseId && ` (${planOverlay.phases.find((p) => p.id === planOverlay.phaseId)?.name || ''})`}
                    </span>
                </div>
                <div className="flex flex-wrap items-center gap-2 border-s border-blue-200 ps-3 dark:border-blue-800">
                    {planOverlay.phases.map((ph, idx) => (
                        <span
                            key={ph.id}
                            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold"
                            style={{
                                backgroundColor: ph.colorConfig.bg,
                                color: ph.colorConfig.text,
                                border: `1px solid ${ph.colorConfig.border}`,
                            }}
                        >
                            <span
                                className="inline-block h-1.5 w-1.5 rounded-full"
                                style={{ backgroundColor: ph.colorConfig.badgeBg }}
                            />
                            {ph.name} (P{idx + 1})
                        </span>
                    ))}
                </div>
            </div>
            <button
                type="button"
                onClick={() => onToggleOverlay(planOverlay.planId, planOverlay.phaseId)}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-blue-300 bg-white px-3 py-1.5 text-xs font-bold text-blue-700 hover:bg-blue-50 dark:border-blue-800 dark:bg-slate-900 dark:text-blue-300 dark:hover:bg-slate-800"
                data-testid="clear-plan-overlay-button"
            >
                {t('clinical_plans.overlay.clear_overlay', 'Clear Overlay')}
            </button>
        </div>
    );
}

PlanOverlayActiveBanner.propTypes = {
    planOverlay: PropTypes.shape({
        planId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        planTitle: PropTypes.string,
        phaseId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        phases: PropTypes.arrayOf(
            PropTypes.shape({
                id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
                name: PropTypes.string,
                colorConfig: PropTypes.object,
            })
        ),
    }),
    onToggleOverlay: PropTypes.func.isRequired,
    t: PropTypes.func.isRequired,
};
