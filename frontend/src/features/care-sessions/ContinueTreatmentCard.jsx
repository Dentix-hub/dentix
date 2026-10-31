import { useState } from 'react';
import PropTypes from 'prop-types';
import { Play, RotateCcw, ChevronDown, ChevronUp, Clock, Activity, FileText, Layers } from 'lucide-react';

/**
 * ContinueTreatmentCard (Slice S21 / G10-M13).
 * Renders at the top of the clinical chart to display unfinished treatment progress,
 * recorded canal working lengths, and a 1-click resume trigger without reading old notes.
 * Supports multi-procedure resumption (Defect 3).
 */
export default function ContinueTreatmentCard({
    resumableContext,
    onResumeTreatment,
    isResuming = false,
    t = (k, fallback, params = {}) => {
        let text = fallback || k;
        if (params && typeof text === 'string') {
            Object.entries(params).forEach(([key, val]) => {
                text = text.replace(new RegExp(`{{${key}}}`, 'g'), String(val));
            });
        }
        return text;
    },
}) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [selectedIdx, setSelectedIdx] = useState(0);

    if (!resumableContext?.has_resumable) {
        return null;
    }

    const { paused_session, items = [] } = resumableContext;

    // Multi-procedure support (Defect 3 fix): allow selecting between items
    const activeIndex = Math.min(selectedIdx, Math.max(0, items.length - 1));
    const currentItem = items[activeIndex] || items[0] || null;
    const isPaused = Boolean(paused_session);

    const toothKey = currentItem?.tooth_key || paused_session?.steps?.[0]?.work_item?.targets?.[0]?.tooth_key || paused_session?.observations?.[0]?.tooth_key || null;
    const procedureCode = currentItem?.procedure_code || 'ENDO_RCT';
    const totalSteps = currentItem?.total_steps || paused_session?.steps?.length || 0;
    const completedCount = currentItem?.completed_steps_count || paused_session?.steps?.filter((s) => s.status === 'completed').length || 0;
    const progressPercent = totalSteps > 0 ? Math.round((completedCount / totalSteps) * 100) : 0;
    const nextStepTitle = currentItem?.next_step_title || paused_session?.steps?.find((s) => s.status !== 'completed')?.title || null;

    // G10-M10 Canal observations
    const observations = currentItem?.observations || paused_session?.observations || [];
    const canalMeasurements = observations.filter(
        (o) =>
            o.observation_code === 'working_length' ||
            o.observation_code === 'canal_measurement' ||
            o.structured_value?.length_mm != null ||
            o.structured_value?.canal_id != null
    );

    const lastNotes = currentItem?.last_notes || paused_session?.notes;
    const lastSessionAt = currentItem?.last_session_at || paused_session?.started_at;

    const handleResume = (resumeAll = false) => {
        if (onResumeTreatment) {
            const allWorkItemIds = items.map((i) => i.work_item_id).filter(Boolean);
            onResumeTreatment({
                workItemId: currentItem?.work_item_id || null,
                workItemIds: resumeAll ? allWorkItemIds : (currentItem?.work_item_id ? [currentItem.work_item_id] : allWorkItemIds),
                sessionId: paused_session?.id || null,
                isPaused,
                procedureCode,
                toothKey,
                resumeAll,
            });
        }
    };

    return (
        <section
            data-testid="continue-treatment-card"
            aria-label={t('care_sessions.continue_treatment', 'Continue Treatment')}
            className="rounded-xl border border-amber-300 bg-amber-50/80 p-3.5 shadow-sm transition-all dark:border-amber-700/60 dark:bg-amber-950/30"
        >
            {/* Multi-Procedure Selector Tabs (Defect 3 fix) */}
            {items.length > 1 && (
                <div
                    data-testid="multi-procedure-selector"
                    className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-amber-200/80 pb-2.5 dark:border-amber-800/50"
                >
                    <div className="flex flex-wrap items-center gap-1.5">
                        <span className="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-amber-900 dark:text-amber-200">
                            <Layers className="h-3.5 w-3.5" />
                            {t('care_sessions.resumable_procedures', 'Resumable Procedures ({{count}}):', { count: items.length })}
                        </span>
                        {items.map((item, idx) => {
                            const isSel = idx === activeIndex;
                            return (
                                <button
                                    key={item.work_item_id || idx}
                                    type="button"
                                    onClick={() => setSelectedIdx(idx)}
                                    data-testid={`select-procedure-${idx}`}
                                    className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-bold transition-all ${
                                        isSel
                                            ? 'bg-amber-600 text-white shadow-xs dark:bg-amber-500'
                                            : 'bg-white/80 text-amber-900 hover:bg-white dark:bg-slate-800 dark:text-amber-200'
                                    }`}
                                >
                                    {item.tooth_key && <span>Tooth {item.tooth_key}:</span>}
                                    <span>{item.procedure_code === 'ENDO_RCT' ? 'RCT' : item.procedure_code}</span>
                                    <span className="rounded bg-black/10 px-1 py-0.2 text-[10px] font-semibold dark:bg-white/10">
                                        {item.completed_steps_count || 0}/{item.total_steps || 0}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                    <button
                        type="button"
                        data-testid="resume-all-procedures-btn"
                        onClick={() => handleResume(true)}
                        disabled={isResuming}
                        className="inline-flex items-center gap-1 rounded-lg bg-amber-700 px-3 py-1 text-xs font-bold text-white shadow-xs transition-colors hover:bg-amber-800 disabled:opacity-50 dark:bg-amber-600 dark:hover:bg-amber-500"
                    >
                        <Play className="h-3.5 w-3.5" />
                        <span>{t('care_sessions.resume_all', 'Resume All ({{count}})', { count: items.length })}</span>
                    </button>
                </div>
            )}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-2.5">
                    <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500 text-white shadow-sm dark:bg-amber-600">
                        {isPaused ? <Clock className="h-4 w-4" /> : <Activity className="h-4 w-4" />}
                    </div>
                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            {toothKey && (
                                <span
                                    data-testid="continue-card-tooth-badge"
                                    className="inline-flex items-center rounded-md bg-amber-200/80 px-2 py-0.5 text-xs font-bold text-amber-900 dark:bg-amber-900/60 dark:text-amber-200"
                                >
                                    {t('care_sessions.tooth', 'Tooth')} {toothKey}
                                </span>
                            )}
                            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                                {procedureCode === 'ENDO_RCT'
                                    ? t('care_sessions.rct_title', 'Root Canal Treatment (RCT)')
                                    : procedureCode}
                            </h4>
                            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
                                {isPaused
                                    ? t('care_sessions.status_paused', 'Paused Session')
                                    : t('care_sessions.status_in_progress', 'In Progress')}
                            </span>
                        </div>

                        <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                            {completedCount > 0 ? (
                                <span>
                                    {t('care_sessions.steps_progress', '{{completed}} of {{total}} steps completed ({{percent}}%)', {
                                        completed: completedCount,
                                        total: totalSteps,
                                        percent: progressPercent,
                                    })}
                                    {nextStepTitle && (
                                        <span className="mx-1 font-semibold text-amber-800 dark:text-amber-300">
                                            &bull; {t('care_sessions.next_step', 'Next: {{step}}', { step: nextStepTitle })}
                                        </span>
                                    )}
                                </span>
                            ) : (
                                <span>{t('care_sessions.ready_to_resume', 'Treatment ready to be resumed chairside')}</span>
                            )}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-auto">
                    {canalMeasurements.length > 0 && (
                        <button
                            type="button"
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="inline-flex items-center gap-1 rounded-lg border border-amber-300 bg-white/80 px-2.5 py-1.5 text-xs font-semibold text-amber-800 transition-colors hover:bg-white dark:border-amber-700 dark:bg-slate-800 dark:text-amber-200"
                        >
                            <span>{t('care_sessions.canals', 'Canals')} ({canalMeasurements.length})</span>
                            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                        </button>
                    )}
                    <button
                        type="button"
                        data-testid="resume-treatment-btn"
                        onClick={() => handleResume(false)}
                        disabled={isResuming}
                        className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg bg-amber-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm transition-colors hover:bg-amber-700 disabled:opacity-50 dark:bg-amber-600 dark:hover:bg-amber-500"
                    >
                        {isResuming ? (
                            <Clock className="h-4 w-4 animate-spin" />
                        ) : isPaused ? (
                            <Play className="h-4 w-4" />
                        ) : (
                            <RotateCcw className="h-4 w-4" />
                        )}
                        <span>
                            {isPaused
                                ? t('care_sessions.resume_session', 'Resume Session')
                                : t('care_sessions.resume_treatment', 'Resume Treatment')}
                        </span>
                    </button>
                </div>
            </div>

            {/* Quick canal working length preview pill strip */}
            {canalMeasurements.length > 0 && (
                <div data-testid="canal-measurements-preview" className="mt-2.5 flex flex-wrap items-center gap-1.5 border-t border-amber-200/80 pt-2 text-xs dark:border-amber-800/50">
                    <span className="font-semibold text-amber-900 dark:text-amber-200">
                        {t('care_sessions.canal_lengths', 'Recorded Canals:')}
                    </span>
                    {canalMeasurements.map((obs, idx) => {
                        const sv = obs.structured_value || {};
                        const canalName = obs.canal_id || sv.canal_id || obs.root_id || sv.root_id || `Canal ${idx + 1}`;
                        const len = sv.length_mm != null ? `${sv.length_mm}mm` : null;
                        const maf = sv.maf ? `MAF #${sv.maf}` : null;
                        return (
                            <span
                                key={obs.id || idx}
                                className="inline-flex items-center gap-1 rounded-md bg-white/90 px-2 py-0.5 font-mono text-xs font-semibold text-slate-800 shadow-xs dark:bg-slate-800 dark:text-slate-200"
                            >
                                <span className="text-amber-700 dark:text-amber-400">{canalName}</span>
                                {len && <span>: {len}</span>}
                                {maf && <span className="text-slate-600 dark:text-slate-300">({maf})</span>}
                            </span>
                        );
                    })}
                </div>
            )}

            {/* Expandable details with previous notes and full canal list */}
            {isExpanded && (
                <div className="mt-3 space-y-2 rounded-lg bg-white/70 p-3 text-xs dark:bg-slate-900/60">
                    {lastSessionAt && (
                        <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
                            <Clock className="h-3.5 w-3.5" />
                            <span>
                                {t('care_sessions.last_visit', 'Last visit:')} {new Date(lastSessionAt).toLocaleDateString()}
                            </span>
                        </div>
                    )}
                    {lastNotes && (
                        <div className="flex items-start gap-1.5 text-slate-700 dark:text-slate-300">
                            <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-600 dark:text-slate-400" />
                            <p className="italic">{lastNotes}</p>
                        </div>
                    )}
                    <div className="space-y-1">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">
                            {t('care_sessions.measurements_detail', 'Canal Observations & Measurements:')}
                        </div>
                        <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 md:grid-cols-3">
                            {canalMeasurements.map((m, idx) => {
                                const sv = m.structured_value || {};
                                return (
                                    <div
                                        key={m.id || idx}
                                        className="rounded-md border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-800"
                                    >
                                        <div className="font-bold text-amber-700 dark:text-amber-400">
                                            {m.canal_id || sv.canal_id || m.root_id || sv.root_id || `Canal ${idx + 1}`}
                                        </div>
                                        <div className="text-slate-600 dark:text-slate-300">
                                            {sv.length_mm != null && <span>Length: {sv.length_mm} mm</span>}
                                            {sv.reference_point && <span className="ml-1 text-slate-600">({sv.reference_point})</span>}
                                        </div>
                                        {sv.maf && <div className="text-slate-600 dark:text-slate-300">MAF: #{sv.maf}</div>}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}
        </section>
    );
}

ContinueTreatmentCard.propTypes = {
    resumableContext: PropTypes.shape({
        has_resumable: PropTypes.bool,
        paused_session: PropTypes.object,
        items: PropTypes.arrayOf(PropTypes.object),
    }),
    onResumeTreatment: PropTypes.func.isRequired,
    isResuming: PropTypes.bool,
    t: PropTypes.func,
};
