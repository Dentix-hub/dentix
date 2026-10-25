import PropTypes from 'prop-types';
import { useAuth } from '@/auth/useAuth';
import { useAuthStore } from '@/store/auth.store';
import {
    formatClinicalWarning,
    getRealClinicalWarnings,
    getInformationalClinicalWarnings,
} from '../utils/clinicalWarningFormatter';

export default function ClinicalWorkspaceStatusBanner({ adaptedChart, t }) {
    let user = null;
    try {
        const auth = useAuth();
        user = auth?.user;
    } catch {
        user = useAuthStore.getState?.()?.user || null;
    }
    const isSuperAdmin = user?.role === 'super_admin';

    if (!adaptedChart) return null;

    const rawWarnings = Array.isArray(adaptedChart.warnings) ? adaptedChart.warnings : [];
    const realWarnings = getRealClinicalWarnings(rawWarnings);
    const informationalWarnings = getInformationalClinicalWarnings(rawWarnings);
    const hasRealWarnings = realWarnings.length > 0;
    const hasInformationalWarnings = informationalWarnings.length > 0;

    // Non-super_admin: hide coverage chips, fallback notice, status notes, technical details, and empty banner.
    // If there are real warnings, show ONE short Arabic line with the count. Nothing if zero.
    if (!isSuperAdmin) {
        if (!hasRealWarnings) {
            return null;
        }

        return (
            <div className="space-y-2" data-testid="clinical-workspace-status">
                <div
                    data-testid="clinical-workspace-warnings"
                    className="rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300 font-medium"
                >
                    {t(
                        'clinical.legacy_review_needed',
                        '{{count}} سجلات قديمة تحتاج مراجعة',
                        { count: realWarnings.length }
                    )}
                </div>
            </div>
        );
    }

    // Super Admin view:
    return (
        <div className="space-y-2" data-testid="clinical-workspace-status">
            <div
                data-testid="clinical-workspace-coverage"
                className="flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-400"
            >
                <span className="font-semibold">{t('clinical.coverage', 'التغطية السريرية')}:</span>
                {Object.entries(adaptedChart.coverage || {}).map(([domain, status]) => {
                    const statusKey = String(status).toLowerCase();
                    const translatedStatus = t(`clinical.coverage_status.${statusKey}`, status);
                    const translatedDomain = t(`clinical.domain.${domain}`, domain);

                    return (
                        <span
                            key={domain}
                            data-testid={`coverage-chip-${domain}`}
                            data-domain={domain}
                            data-status={status}
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${
                                status === 'COMPLETE'
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                                    : status === 'PARTIAL'
                                    ? 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
                                    : 'bg-slate-100 text-slate-600 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
                            }`}
                        >
                            <span>{translatedDomain}:</span>
                            <span className="font-bold">{translatedStatus}</span>
                        </span>
                    );
                })}
            </div>

            {adaptedChart.isFallback && (
                <div
                    data-testid="clinical-workspace-fallback-banner"
                    className="rounded-lg border border-blue-200 bg-blue-50/70 p-2.5 text-xs text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300"
                >
                    <span className="font-semibold">{t('clinical.fallback_notice', 'ملاحظة')}: </span>
                    {t('clinical.fallback_desc', 'عرض السجلات السريرية بمساهمة السجلات القديمة.')}
                </div>
            )}

            {hasRealWarnings && (
                <div
                    data-testid="clinical-workspace-warnings"
                    className="rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300"
                >
                    <div className="font-medium">
                        {t(
                            'clinical.legacy_review_needed',
                            '{{count}} سجلات قديمة تحتاج مراجعة',
                            { count: realWarnings.length }
                        )}
                    </div>
                    <ul className="mt-1.5 space-y-1">
                        {realWarnings.map((w, idx) => {
                            const formatted = formatClinicalWarning(w, t);
                            return (
                                <li
                                    key={idx}
                                    data-testid={`clinical-warning-friendly-${idx}`}
                                    className="text-xs text-amber-900 dark:text-amber-200 font-normal"
                                >
                                    {formatted.friendlyMessage}
                                </li>
                            );
                        })}
                    </ul>
                    <details
                        data-testid="clinical-workspace-technical-details"
                        className="mt-2 text-xs"
                    >
                        <summary className="cursor-pointer font-medium text-amber-900 dark:text-amber-200 hover:underline">
                            {t('clinical.technical_details', 'تفاصيل فنية')}
                        </summary>
                        <ul className="mt-1 list-inside list-disc space-y-0.5">
                            {rawWarnings.map((w, idx) => {
                                const formatted = formatClinicalWarning(w, t);
                                return (
                                    <li key={idx} data-code={w?.code || 'GENERIC_UNKNOWN_WARNING'}>
                                        {formatted.friendlyMessage}
                                    </li>
                                );
                            })}
                        </ul>
                    </details>
                </div>
            )}

            {hasInformationalWarnings && (
                <div
                    data-testid="clinical-workspace-status-notes"
                    className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-900/40 dark:text-slate-300"
                >
                    <div className="font-medium text-slate-800 dark:text-slate-200">
                        {t('clinical.status_notes', 'ملاحظات حالة النظام السريري')}
                    </div>
                    <ul className="mt-1.5 space-y-1">
                        {informationalWarnings.map((w, idx) => {
                            const formatted = formatClinicalWarning(w, t);
                            return (
                                <li
                                    key={idx}
                                    data-testid={`clinical-status-note-${idx}`}
                                    className="text-xs text-slate-600 dark:text-slate-400 font-normal"
                                >
                                    {formatted.friendlyMessage}
                                </li>
                            );
                        })}
                    </ul>
                    {!hasRealWarnings && (
                        <details
                            data-testid="clinical-workspace-technical-details"
                            className="mt-2 text-xs"
                        >
                            <summary className="cursor-pointer font-medium text-slate-700 dark:text-slate-300 hover:underline">
                                {t('clinical.technical_details', 'تفاصيل فنية')}
                            </summary>
                            <ul className="mt-1 list-inside list-disc space-y-0.5">
                                {rawWarnings.map((w, idx) => {
                                    const formatted = formatClinicalWarning(w, t);
                                    return (
                                        <li key={idx} data-code={w?.code || 'GENERIC_UNKNOWN_WARNING'}>
                                            {formatted.friendlyMessage}
                                        </li>
                                    );
                                })}
                            </ul>
                        </details>
                    )}
                </div>
            )}

            {adaptedChart.isEmpty && (
                <div
                    data-testid="clinical-workspace-empty"
                    className="rounded-lg border border-slate-200 bg-slate-50/50 p-2 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400"
                >
                    {t('clinical.empty_workspace', 'لم يتم تسجيل أي إجراءات أو ملاحظات سريرية لهذا المريض حتى الآن.')}
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
