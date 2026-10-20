import PropTypes from 'prop-types';
import { Activity, Clock, Flag, CheckCircle2, Calendar } from 'lucide-react';

/**
 * CareSessionActiveBanner (Slice S20 & S22 / G11-M01).
 * Prominent chairside active session indicator banner rendered on the patient chart.
 */
export default function CareSessionActiveBanner({
    session,
    onOpenWorkflow,
    onOpenFinishSheet,
    t = (k, f) => f || k,
}) {
    if (!session || session.status !== 'in_progress') {
        return null;
    }

    const steps = session.steps || [];
    const completedCount = steps.filter(
        (s) => s.status === 'completed' || s.status === 'partial'
    ).length;

    const formatStartTime = (isoString) => {
        if (!isoString) return '';
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return '';
        }
    };

    return (
        <aside
            aria-label="Active Care Session"
            data-testid="care-session-active-banner"
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50/40 p-4 shadow-sm dark:border-blue-900/40 dark:from-blue-950/40 dark:to-indigo-950/20"
        >
            <div className="flex items-center gap-3">
                <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
                    <Activity className="h-5 w-5" aria-hidden="true" />
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
                    </span>
                </div>

                <div>
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                            {t('care_session.active_banner_title', 'Active Care Session')} #{session.id}
                        </span>
                        {session.appointment_id && (
                            <span
                                data-testid="linked-appointment-badge"
                                className="inline-flex items-center gap-1 rounded-md bg-indigo-100 px-2 py-0.5 text-xs font-bold text-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-300"
                            >
                                <Calendar className="h-3 w-3" aria-hidden="true" />
                                <span>Appt #{session.appointment_id}</span>
                            </span>
                        )}
                        {session.started_at && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                                <Clock className="h-3 w-3" />
                                {formatStartTime(session.started_at)}
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                        <span>
                            {steps.length > 0
                                ? `${completedCount} of ${steps.length} steps addressed`
                                : t('care_session.session_in_progress', 'Chairside treatment in progress')}
                        </span>
                        {session.observations?.length > 0 && (
                            <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 dark:text-emerald-400">
                                <CheckCircle2 className="h-3 w-3" />
                                {session.observations.length} observations
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <button
                    type="button"
                    onClick={onOpenWorkflow}
                    data-testid="btn-open-active-workflow"
                    className="inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-blue-600 bg-blue-600 px-3.5 py-2 text-xs font-bold text-white shadow-sm transition-colors hover:bg-blue-700"
                >
                    <Activity className="h-4 w-4" aria-hidden="true" />
                    <span>{t('care_session.view_workflow', 'RCT Workflow & Measurements')}</span>
                </button>
                <button
                    type="button"
                    onClick={onOpenFinishSheet}
                    data-testid="btn-banner-finish-session"
                    className="inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                    <Flag className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                    <span>{t('care_session.finish_session_btn', 'Finish Session')}</span>
                </button>
            </div>
        </aside>
    );
}

CareSessionActiveBanner.propTypes = {
    session: PropTypes.object,
    onOpenWorkflow: PropTypes.func.isRequired,
    onOpenFinishSheet: PropTypes.func.isRequired,
    t: PropTypes.func,
};
