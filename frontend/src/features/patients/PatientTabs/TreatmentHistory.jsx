import { useState } from 'react';
import PropTypes from 'prop-types';
import { useQuery } from '@tanstack/react-query';
import {
    Edit2,
    Trash2,
    ChevronDown,
    ChevronUp,
    Calendar,
    Activity,
    Clock,
    CheckCircle2,
    FileText,
    Ruler,
    History as HistoryIcon,
    AlertCircle,
    User,
    CalendarClock,
} from 'lucide-react';
import { fdiToPalmer } from '@/utils/toothUtils';
import { useTranslation } from 'react-i18next';
import ProcedureStatusControl from '@/features/clinical-chart/components/ProcedureStatusControl';
import { getPatientCareSessions } from '@/api/patients';

/**
 * Format date handling actual_visit_date or session_date (Fixes Defect 4).
 */
export function formatCareSessionDate(session) {
    if (!session) return '--';
    const dateVal = session.actual_visit_date || session.session_date || session.started_at || session.date || session.created_at;
    if (!dateVal) return '--';
    try {
        return new Date(dateVal).toLocaleDateString([], {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    } catch {
        return String(dateVal);
    }
}

/**
 * Checks if a CareSession belongs to a specific Treatment row.
 */
export function isSessionMatchingTreatment(session, item) {
    if (!session || !item) return false;

    // 1. Check if care_session_procedures table links to work_item_id or treatment.id
    const itemTargetId = item.work_item_id || item.id;
    if (session.procedures && session.procedures.length > 0) {
        const matchesProc = session.procedures.some(
            (p) => String(p.work_item_id) === String(itemTargetId) || String(p.work_item_id) === String(item.id)
        );
        if (matchesProc) return true;
    }

    // 2. Check steps work_item_id
    if (session.steps && session.steps.length > 0) {
        const matchesStep = session.steps.some(
            (s) => String(s.work_item_id) === String(itemTargetId) || String(s.work_item_id) === String(item.id)
        );
        if (matchesStep) return true;
    }

    // 3. Check observations tooth_key / work_item_id
    if (session.observations && session.observations.length > 0) {
        const matchesObs = session.observations.some(
            (o) =>
                (o.work_item_id && (String(o.work_item_id) === String(itemTargetId) || String(o.work_item_id) === String(item.id))) ||
                (item.tooth_number && String(o.tooth_key) === String(item.tooth_number))
        );
        if (matchesObs) return true;
    }

    // 4. Fallback match by tooth number if defined
    if (item.tooth_number && session.tooth_key && String(session.tooth_key) === String(item.tooth_number)) {
        return true;
    }

    return false;
}

const TreatmentHistory = ({
    history = [],
    patientId,
    careSessions: propCareSessions,
    onEdit,
    onDelete,
    onAdd,
}) => {
    const { t } = useTranslation();
    const [viewMode, setViewMode] = useState('procedures'); // 'procedures' | 'sessions'
    const [expandedRowIds, setExpandedRowIds] = useState(new Set());

    // Fetch care sessions for patient (Defect 6 fix)
    const { data: fetchedSessions = [] } = useQuery({
        queryKey: ['patient', patientId, 'care-sessions'],
        queryFn: async () => {
            if (!patientId) return [];
            const res = await getPatientCareSessions(patientId);
            return res?.data?.data || res?.data || [];
        },
        enabled: Boolean(patientId && !propCareSessions),
    });

    const careSessions = propCareSessions || fetchedSessions;

    const toggleRow = (itemId) => {
        setExpandedRowIds((prev) => {
            const next = new Set(prev);
            if (next.has(itemId)) {
                next.delete(itemId);
            } else {
                next.add(itemId);
            }
            return next;
        });
    };

    return (
        <div
            data-testid="treatment-history-container"
            className="bg-white rounded-2xl border border-slate-100 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-300 dark:bg-slate-900 dark:border-slate-800"
        >
            {/* Header with View Mode Switcher and Add Manual */}
            <div className="p-4 border-b border-slate-50 flex flex-wrap justify-between items-center gap-3 bg-slate-50/50 dark:bg-slate-800/40 dark:border-slate-800">
                <div className="flex items-center gap-3">
                    <h3 className="font-bold text-slate-700 dark:text-slate-200">
                        {t('patientDetails.treatment_history.title', 'Treatment & Visit History')}
                    </h3>
                    {careSessions.length > 0 && (
                        <div className="flex items-center rounded-lg border border-slate-200 bg-white p-0.5 text-xs font-semibold dark:border-slate-700 dark:bg-slate-800">
                            <button
                                type="button"
                                data-testid="view-procedures-tab"
                                onClick={() => setViewMode('procedures')}
                                className={`rounded-md px-2.5 py-1 transition-colors ${
                                    viewMode === 'procedures'
                                        ? 'bg-primary text-white shadow-xs'
                                        : 'text-slate-600 hover:text-slate-900 dark:text-slate-400'
                                }`}
                            >
                                {t('patientDetails.treatment_history.procedures_view', 'Procedures')} ({history.length})
                            </button>
                            <button
                                type="button"
                                data-testid="view-sessions-tab"
                                onClick={() => setViewMode('sessions')}
                                className={`rounded-md px-2.5 py-1 transition-colors ${
                                    viewMode === 'sessions'
                                        ? 'bg-primary text-white shadow-xs'
                                        : 'text-slate-600 hover:text-slate-900 dark:text-slate-400'
                                }`}
                            >
                                {t('patientDetails.treatment_history.sessions_view', 'Visits & Care Sessions')} ({careSessions.length})
                            </button>
                        </div>
                    )}
                </div>

                <div className="flex items-center gap-2">
                    {onAdd && (
                        <button
                            type="button"
                            onClick={onAdd}
                            className="text-primary text-sm font-bold hover:underline"
                        >
                            {t('patientDetails.treatment_history.add_manual', '+ Add Procedure')}
                        </button>
                    )}
                </div>
            </div>

            {/* PROCEDURES VIEW */}
            {viewMode === 'procedures' && (
                <div className="overflow-x-auto">
                    <table className="w-full text-right align-middle" data-testid="treatments-table">
                        <thead className="bg-slate-50 text-slate-600 text-xs font-bold uppercase tracking-wider dark:bg-slate-800/60 dark:text-slate-400">
                            <tr>
                                <th className="p-3.5 whitespace-nowrap">{t('patientDetails.treatment_history.date', 'Date')}</th>
                                <th className="p-3.5 whitespace-nowrap">{t('patientDetails.treatment_history.tooth', 'Tooth')}</th>
                                <th className="p-3.5 whitespace-nowrap min-w-[130px]">{t('patientDetails.treatment_history.diagnosis', 'Diagnosis')}</th>
                                <th className="p-3.5 whitespace-nowrap min-w-[150px]">{t('patientDetails.treatment_history.treatment', 'Procedure')}</th>
                                <th className="p-3.5 whitespace-nowrap">{t('patientDetails.treatment_history.status', 'Status')}</th>
                                <th className="p-3.5 whitespace-nowrap min-w-[200px]">{t('patientDetails.treatment_history.details', 'Details & Sessions')}</th>
                                <th className="p-3.5 whitespace-nowrap">{t('patientDetails.treatment_history.actions', 'Actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {history.map((item) => {
                                const matchedSessions = careSessions.filter((s) => isSessionMatchingTreatment(s, item));
                                const isExpanded = expandedRowIds.has(item.id);

                                return (
                                    <tr key={item.id} className="hover:bg-slate-50/70 transition-colors dark:hover:bg-slate-800/40">
                                        <td className="p-3.5 whitespace-nowrap text-xs text-slate-600 dark:text-slate-300">
                                            {item.date ? new Date(item.date).toLocaleDateString() : '--'}
                                        </td>
                                        <td className="p-3.5 font-mono text-xs font-bold text-slate-700 whitespace-nowrap dark:text-slate-200">
                                            {fdiToPalmer(item.tooth_number) || (item.tooth_number ? `T${item.tooth_number}` : '-')}
                                        </td>
                                        <td className="p-3.5 font-bold text-xs text-slate-800 whitespace-nowrap dark:text-slate-200">
                                            {item.diagnosis || '-'}
                                        </td>
                                        <td className="p-3.5 text-xs font-semibold text-slate-900 whitespace-nowrap dark:text-slate-100">
                                            {item.procedure}
                                        </td>
                                        {/* Defect 7 Fix: ProcedureStatusControl replaces static badge */}
                                        <td className="p-3.5 whitespace-nowrap">
                                            {patientId ? (
                                                <ProcedureStatusControl
                                                    patientId={patientId}
                                                    workItemId={item.work_item_id || item.id}
                                                    currentStatus={item.status}
                                                    compact
                                                />
                                            ) : (
                                                <span
                                                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${
                                                        item.status === 'Done'
                                                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                                                            : item.status === 'In Progress'
                                                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300'
                                                            : item.status === 'Pending'
                                                            ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                                                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                                    }`}
                                                >
                                                    {t(`patientDetails.treatment_history.statuses.${item.status || 'Done'}`, item.status || 'Done')}
                                                </span>
                                            )}
                                        </td>
                                        {/* Details & Expandable Actual Care Sessions (Defect 6 Fix) */}
                                        <td className="p-3.5 text-xs text-slate-700 dark:text-slate-300">
                                            {item.canal_count && (
                                                <div className="font-bold mb-1 text-blue-700 dark:text-blue-400">
                                                    {t('patientDetails.treatment_history.canal_count', 'Canals:')} {item.canal_count}
                                                </div>
                                            )}
                                            {(() => {
                                                try {
                                                    const canals = JSON.parse(item.canal_lengths);
                                                    if (Array.isArray(canals) && canals.length > 0) {
                                                        return (
                                                            <div className="flex flex-wrap gap-1.5 my-1">
                                                                {canals.map((c, idx) => (
                                                                    <div
                                                                        key={idx}
                                                                        className="flex items-center gap-1 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md dark:border-blue-900/60 dark:bg-blue-950/40"
                                                                    >
                                                                        <span className="font-bold text-blue-800 dark:text-blue-300">
                                                                            {c.name || t('patientDetails.treatment_history.canal_default_name', 'Canal')}:
                                                                        </span>
                                                                        <span className="font-mono text-blue-900 font-bold dark:text-blue-200">
                                                                            {c.length}
                                                                        </span>
                                                                        <span className="text-[10px] text-blue-500">
                                                                            {t('patientDetails.treatment_history.canal_unit', 'mm')}
                                                                        </span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        );
                                                    }
                                                    return item.canal_lengths ? (
                                                        <div className="font-bold text-slate-800 bg-yellow-50 p-1 rounded border border-yellow-200 dark:bg-yellow-950/30 dark:border-yellow-800/40">
                                                            {t('patientDetails.treatment_history.lengths', 'Lengths:')} {item.canal_lengths}
                                                        </div>
                                                    ) : null;
                                                } catch {
                                                    return item.canal_lengths ? (
                                                        <div className="font-bold text-slate-800 dark:text-slate-200">
                                                            {t('patientDetails.treatment_history.lengths', 'Lengths:')} {item.canal_lengths}
                                                        </div>
                                                    ) : null;
                                                }
                                            })()}
                                            {item.complications && (
                                                <div className="mt-1 text-red-600 font-bold bg-red-50 p-1 rounded-md text-xs dark:bg-red-950/30 dark:text-red-400">
                                                    ⚠ {item.complications}
                                                </div>
                                            )}
                                            {item.notes && (
                                                <div className="mt-1 text-slate-500 italic text-[11px] dark:text-slate-400">
                                                    {item.notes}
                                                </div>
                                            )}

                                            {/* Expandable Real Care Sessions Toggle (Defect 6 Fix) */}
                                            {matchedSessions.length > 0 && (
                                                <div className="mt-2">
                                                    <button
                                                        type="button"
                                                        data-testid={`toggle-sessions-${item.id}`}
                                                        onClick={() => toggleRow(item.id)}
                                                        className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50/80 px-2 py-0.5 text-xs font-bold text-indigo-700 transition-colors hover:bg-indigo-100 dark:border-indigo-900/60 dark:bg-indigo-950/40 dark:text-indigo-300"
                                                    >
                                                        <Activity className="h-3 w-3" />
                                                        <span>
                                                            {t('patientDetails.treatment_history.care_sessions_count', `Care Sessions (${matchedSessions.length})`, {
                                                                count: matchedSessions.length,
                                                            })}
                                                        </span>
                                                        {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                                                    </button>

                                                    {/* Expanded Session Cards */}
                                                    {isExpanded && (
                                                        <div
                                                            data-testid={`sessions-breakdown-${item.id}`}
                                                            className="mt-2 space-y-2 rounded-xl border border-indigo-100 bg-indigo-50/30 p-2.5 dark:border-indigo-900/30 dark:bg-indigo-950/20"
                                                        >
                                                            {matchedSessions.map((session) => (
                                                                <div
                                                                    key={session.id}
                                                                    className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-xs dark:border-slate-700 dark:bg-slate-800"
                                                                >
                                                                    <div className="flex flex-wrap items-center justify-between gap-1.5 pb-1 border-b border-slate-100 dark:border-slate-700/60">
                                                                        <div className="flex items-center gap-2">
                                                                            <span className="font-bold text-indigo-950 dark:text-indigo-300">
                                                                                Session #{session.id}
                                                                            </span>
                                                                            <span className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                                                                                <Calendar className="h-3 w-3" />
                                                                                {formatCareSessionDate(session)}
                                                                            </span>
                                                                            {session.is_historical && (
                                                                                <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[10px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                                                                                    Historical
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                        <span
                                                                            className={`rounded-full px-2 py-0.2 text-[10px] font-bold ${
                                                                                session.status === 'completed'
                                                                                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                                                                    : session.status === 'in_progress'
                                                                                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
                                                                                    : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                                                                            }`}
                                                                        >
                                                                            {session.status}
                                                                        </span>
                                                                    </div>

                                                                    {/* Steps executed in this session */}
                                                                    {session.steps && session.steps.length > 0 && (
                                                                        <div className="mt-2 space-y-1">
                                                                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                                                                Steps ({(session.steps || []).filter((s) => s.status === 'completed').length}/{(session.steps || []).length}):
                                                                            </span>
                                                                            <div className="flex flex-wrap gap-1">
                                                                                {session.steps.map((step) => (
                                                                                    <span
                                                                                        key={step.id}
                                                                                        className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium ${
                                                                                            step.status === 'completed'
                                                                                                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300'
                                                                                                : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                                                                                        }`}
                                                                                    >
                                                                                        {step.status === 'completed' && <CheckCircle2 className="h-3 w-3 text-emerald-600" />}
                                                                                        <span>{step.title}</span>
                                                                                    </span>
                                                                                ))}
                                                                            </div>
                                                                        </div>
                                                                    )}

                                                                    {/* Recorded Observations (e.g. canal lengths) */}
                                                                    {session.observations && session.observations.length > 0 && (
                                                                        <div className="mt-2 space-y-1">
                                                                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                                                                Recorded Measurements:
                                                                            </span>
                                                                            <div className="flex flex-wrap gap-1.5">
                                                                                {session.observations.map((obs) => {
                                                                                    const sv = obs.structured_value || {};
                                                                                    const canal = obs.canal_id || sv.canal_id || obs.root_id || sv.root_id || 'Measurement';
                                                                                    const len = sv.length_mm != null ? `${sv.length_mm}mm` : null;
                                                                                    const maf = sv.maf ? `MAF #${sv.maf}` : null;
                                                                                    return (
                                                                                        <span
                                                                                            key={obs.id}
                                                                                            className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-0.5 text-[11px] font-mono font-semibold text-slate-800 border border-slate-200 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-200"
                                                                                        >
                                                                                            <span className="text-indigo-600 dark:text-indigo-400">{canal}</span>
                                                                                            {len && <span>: {len}</span>}
                                                                                            {maf && <span className="text-slate-500">({maf})</span>}
                                                                                            {obs.is_superseded && (
                                                                                                <span className="text-[9px] text-amber-600 font-bold">[Amended]</span>
                                                                                            )}
                                                                                        </span>
                                                                                    );
                                                                                })}
                                                                            </div>
                                                                        </div>
                                                                    )}

                                                                    {/* Session Notes */}
                                                                    {session.notes && (
                                                                        <div className="mt-2 flex items-start gap-1 text-[11px] text-slate-600 dark:text-slate-300 italic">
                                                                            <FileText className="h-3 w-3 mt-0.5 shrink-0 text-slate-400" />
                                                                            <span>{session.notes}</span>
                                                                        </div>
                                                                    )}

                                                                    {/* Next Visit Requests */}
                                                                    {session.next_visit_requests && session.next_visit_requests.length > 0 && (
                                                                        <div className="mt-2 space-y-1">
                                                                            {session.next_visit_requests.map((nvr) => (
                                                                                <div
                                                                                    key={nvr.id}
                                                                                    className="flex items-center gap-1.5 rounded-md bg-blue-50/80 px-2 py-1 text-[11px] font-semibold text-blue-900 border border-blue-200 dark:bg-blue-950/30 dark:border-blue-900/40 dark:text-blue-300"
                                                                                >
                                                                                    <CalendarClock className="h-3.5 w-3.5 text-blue-600" />
                                                                                    <span>Follow-up: {nvr.reason} ({nvr.suggested_duration_minutes}m)</span>
                                                                                    <span className="ms-auto rounded bg-blue-200/60 px-1.5 py-0.2 text-[10px] uppercase font-bold text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                                                                        {nvr.status}
                                                                                    </span>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-3.5 whitespace-nowrap">
                                            <div className="flex gap-1.5">
                                                {onEdit && (
                                                    <button
                                                        type="button"
                                                        onClick={() => onEdit(item)}
                                                        className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg dark:hover:bg-slate-800"
                                                        title={t('common.edit', 'Edit')}
                                                    >
                                                        <Edit2 size={15} />
                                                    </button>
                                                )}
                                                {onDelete && (
                                                    <button
                                                        type="button"
                                                        onClick={() => onDelete(item.id)}
                                                        className="p-1.5 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg dark:hover:bg-slate-800"
                                                        title={t('common.delete', 'Delete')}
                                                    >
                                                        <Trash2 size={15} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* UNIFIED SESSIONS TIMELINE VIEW */}
            {viewMode === 'sessions' && (
                <div className="p-4 space-y-3" data-testid="care-sessions-timeline-view">
                    {careSessions.map((session) => (
                        <div
                            key={session.id}
                            data-testid={`timeline-session-${session.id}`}
                            className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs dark:border-slate-700 dark:bg-slate-800"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5 dark:border-slate-700">
                                <div className="flex items-center gap-2">
                                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs">
                                        #{session.id}
                                    </div>
                                    <div>
                                        <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                                            Care Session #{session.id}
                                            {session.appointment_id && (
                                                <span className="ms-2 rounded-md bg-indigo-100 px-1.5 py-0.5 text-[10px] font-bold text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300">
                                                    Appt #{session.appointment_id}
                                                </span>
                                            )}
                                        </h4>
                                        <p className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                                            <Calendar className="h-3 w-3" />
                                            <span>Visit Date: {formatCareSessionDate(session)}</span>
                                            {session.is_historical && (
                                                <span className="ms-1 rounded bg-slate-100 px-1 text-[10px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                                                    Historical Entry
                                                </span>
                                            )}
                                        </p>
                                    </div>
                                </div>
                                <span
                                    className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                                        session.status === 'completed'
                                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                            : session.status === 'in_progress'
                                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
                                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                                    }`}
                                >
                                    {session.status}
                                </span>
                            </div>

                            {/* Steps */}
                            {session.steps && session.steps.length > 0 && (
                                <div className="mt-2.5 space-y-1">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                        Workflow Steps ({(session.steps || []).filter((s) => s.status === 'completed').length}/{(session.steps || []).length}):
                                    </span>
                                    <div className="flex flex-wrap gap-1.5">
                                        {session.steps.map((st) => (
                                            <span
                                                key={st.id}
                                                className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${
                                                    st.status === 'completed'
                                                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300'
                                                        : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                                                }`}
                                            >
                                                {st.status === 'completed' && <CheckCircle2 className="h-3 w-3 text-emerald-600" />}
                                                <span>{st.title}</span>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Observations */}
                            {session.observations && session.observations.length > 0 && (
                                <div className="mt-2.5 space-y-1">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                        Chairside Observations & Measurements:
                                    </span>
                                    <div className="flex flex-wrap gap-1.5">
                                        {session.observations.map((obs) => {
                                            const sv = obs.structured_value || {};
                                            const canal = obs.canal_id || sv.canal_id || obs.root_id || sv.root_id || 'Obs';
                                            const len = sv.length_mm != null ? `${sv.length_mm}mm` : null;
                                            const maf = sv.maf ? `MAF #${sv.maf}` : null;
                                            return (
                                                <span
                                                    key={obs.id}
                                                    className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2.5 py-1 text-xs font-mono font-semibold text-slate-800 border border-slate-200 dark:bg-slate-700 dark:border-slate-600 dark:text-slate-200"
                                                >
                                                    <span className="text-indigo-600 dark:text-indigo-400">{canal}</span>
                                                    {len && <span>: {len}</span>}
                                                    {maf && <span className="text-slate-500">({maf})</span>}
                                                    {obs.is_superseded && (
                                                        <span className="text-[10px] text-amber-600 font-bold">[Amended]</span>
                                                    )}
                                                </span>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Notes */}
                            {session.notes && (
                                <div className="mt-2 flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-300 italic bg-slate-50 p-2 rounded-lg dark:bg-slate-900/50">
                                    <FileText className="h-3.5 w-3.5 mt-0.5 shrink-0 text-slate-400" />
                                    <span>{session.notes}</span>
                                </div>
                            )}

                            {/* Next Visit Requests */}
                            {session.next_visit_requests && session.next_visit_requests.length > 0 && (
                                <div className="mt-2.5 space-y-1.5">
                                    {session.next_visit_requests.map((nvr) => (
                                        <div
                                            key={nvr.id}
                                            className="flex items-center justify-between gap-2 rounded-lg bg-blue-50/80 px-2.5 py-1.5 text-xs font-semibold text-blue-900 border border-blue-200 dark:bg-blue-950/30 dark:border-blue-900/40 dark:text-blue-300"
                                        >
                                            <div className="flex items-center gap-1.5">
                                                <CalendarClock className="h-4 w-4 text-blue-600" />
                                                <span>Follow-up: {nvr.reason} ({nvr.suggested_duration_minutes}m)</span>
                                            </div>
                                            <span className="rounded bg-blue-200/80 px-2 py-0.5 text-[10px] uppercase font-bold text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                                {nvr.status}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {history.length === 0 && careSessions.length === 0 && (
                <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                    {t('patientDetails.treatment_history.empty', 'No treatment or visit history recorded yet.')}
                </div>
            )}
        </div>
    );
};

TreatmentHistory.propTypes = {
    history: PropTypes.arrayOf(PropTypes.object),
    patientId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    careSessions: PropTypes.arrayOf(PropTypes.object),
    onEdit: PropTypes.func,
    onDelete: PropTypes.func,
    onAdd: PropTypes.func,
};

export default TreatmentHistory;
