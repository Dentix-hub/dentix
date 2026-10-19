import PropTypes from 'prop-types';

export default function ClinicalWorkspaceStatusBanner({ adaptedChart, t }) {
    if (!adaptedChart) return null;

    return (
        <div className="space-y-2" data-testid="clinical-workspace-status">
            <div
                data-testid="clinical-workspace-coverage"
                className="flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-400"
            >
                <span className="font-semibold">{t('clinical.coverage', 'Coverage')}:</span>
                {Object.entries(adaptedChart.coverage || {}).map(([domain, status]) => (
                    <span
                        key={domain}
                        className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${
                            status === 'COMPLETE'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                                : status === 'PARTIAL'
                                ? 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
                                : 'bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
                        }`}
                    >
                        <span>{domain}:</span>
                        <span className="font-bold">{status}</span>
                    </span>
                ))}
            </div>

            {adaptedChart.isFallback && (
                <div
                    data-testid="clinical-workspace-fallback-banner"
                    className="rounded-lg border border-blue-200 bg-blue-50/70 p-2.5 text-xs text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300"
                >
                    <span className="font-semibold">{t('clinical.fallback_notice', 'Notice')}: </span>
                    {t('clinical.fallback_desc', 'Displaying clinical records with legacy fallback contribution.')}
                </div>
            )}

            {adaptedChart.warnings && adaptedChart.warnings.length > 0 && (
                <div
                    data-testid="clinical-workspace-warnings"
                    className="rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300"
                >
                    <span className="font-semibold">{t('clinical.warnings', 'Warnings')}: </span>
                    <ul className="mt-1 list-inside list-disc space-y-0.5">
                        {adaptedChart.warnings.map((w, idx) => (
                            <li key={idx}>
                                <span className="font-medium">[{w.code}]</span> {w.message}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {adaptedChart.isEmpty && (
                <div
                    data-testid="clinical-workspace-empty"
                    className="rounded-lg border border-slate-200 bg-slate-50/50 p-2 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400"
                >
                    {t('clinical.empty_workspace', 'No clinical events or work items recorded for this patient yet.')}
                </div>
            )}
        </div>
    );
}

ClinicalWorkspaceStatusBanner.propTypes = {
    adaptedChart: PropTypes.shape({
        coverage: PropTypes.object,
        isFallback: PropTypes.bool,
        warnings: PropTypes.array,
        isEmpty: PropTypes.bool,
    }),
    t: PropTypes.func.isRequired,
};
