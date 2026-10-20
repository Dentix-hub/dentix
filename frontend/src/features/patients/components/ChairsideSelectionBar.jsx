import PropTypes from 'prop-types';
import ChartQuickActionLauncher from '@/features/clinical-chart/components/ChartQuickActionLauncher';
import ClinicalChartInspector from '@/features/clinical-chart/components/ClinicalChartInspector';
import { CLINICAL_CHART_COPY } from '@/features/clinical-chart/components/clinicalChartWorkspaceCopy';
import { fdiToPalmer } from '@/utils/toothUtils';

export default function ChairsideSelectionBar({
    selectedTeeth,
    resolvedActiveTooth,
    setActiveToothKey,
    handleRemoveToothFromSelection,
    isMultiSelectMode,
    handleClearSelection,
    handleRecordTreatmentFromSelection,
    activeSurfaces,
    handleToggleSurface,
    selectedSurfacesByTooth,
    handleQuickLauncherAction,
    setActiveStickyTool,
    setStickyAppliedCount,
    procedures,
    i18n,
    t,
    adaptedChart,
    workspaceSnapshot,
    history,
    treatmentPlans,
    payments,
    handleRemoveWorkItemOrTreatment,
    activeCareSession = null,
    onStartRctSession = null,
    onOpenRctWorkflow = null,
    patientId = null,
    attachments = [],
    attachmentLinks = null,
}) {
    if (!selectedTeeth || selectedTeeth.length === 0) {
        return null;
    }

    return (
        <div
            data-testid="chairside-selection-bar"
            className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800">
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-slate-700 dark:text-slate-300">
                        {t('patient_details.chart.selected_teeth', 'Selected Teeth')}:
                    </span>
                    <div className="flex flex-wrap items-center gap-1.5" data-testid="selected-teeth-badges">
                        {selectedTeeth.map((toothKey) => {
                            const fdi = Number.parseInt(toothKey, 10);
                            const palmer = fdiToPalmer(fdi);
                            const isActive = toothKey === resolvedActiveTooth;
                            return (
                                <button
                                    key={toothKey}
                                    type="button"
                                    onClick={() => setActiveToothKey(toothKey)}
                                    className={`inline-flex min-h-11 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-bold transition-all ${
                                        isActive
                                            ? 'bg-blue-600 text-white shadow-sm ring-2 ring-blue-500 ring-offset-1'
                                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                                    }`}
                                    data-testid={`selected-tooth-badge-${toothKey}`}
                                >
                                    <span>{toothKey} ({palmer})</span>
                                    {isMultiSelectMode && (
                                        <span
                                            role="button"
                                            tabIndex={0}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleRemoveToothFromSelection(toothKey);
                                            }}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' || e.key === ' ') {
                                                    e.stopPropagation();
                                                    handleRemoveToothFromSelection(toothKey);
                                                }
                                            }}
                                            aria-label={`Remove tooth ${toothKey}`}
                                            className="inline-flex h-4 w-4 items-center justify-center rounded-full text-xs hover:bg-black/20"
                                        >
                                            ×
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {activeCareSession ? (
                        <button
                            type="button"
                            onClick={onOpenRctWorkflow}
                            className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-blue-600 bg-blue-50 px-3.5 py-2 text-xs font-bold text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                            data-testid="chairside-active-session-button"
                        >
                            <span>{t('care_session.active_session_btn', 'RCT Steps')}</span>
                        </button>
                    ) : (
                        <button
                            type="button"
                            onClick={() => onStartRctSession?.(resolvedActiveTooth || selectedTeeth[0])}
                            className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-purple-200 bg-purple-50 px-3.5 py-2 text-xs font-bold text-purple-700 hover:bg-purple-100 dark:border-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
                            data-testid="chairside-start-rct-button"
                        >
                            <span>{t('care_session.start_rct_btn', 'Start RCT')}</span>
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={handleClearSelection}
                        className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                        data-testid="clear-selection-button"
                    >
                        {t('patient_details.chart.clear_selection', 'Clear Selection')}
                    </button>
                    <button
                        type="button"
                        onClick={handleRecordTreatmentFromSelection}
                        className="inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                        data-testid="record-treatment-button"
                        title={t('patient_details.chart.advanced_entry_tooltip', 'Open classic treatment entry modal')}
                    >
                        {t('patient_details.chart.advanced_entry', 'Advanced Entry')}
                    </button>
                </div>
            </div>

            {resolvedActiveTooth && (
                <div className="flex flex-wrap items-center gap-2 pt-1" data-testid="surface-pill-bar">
                    <span className="me-1 text-xs font-bold text-slate-500 dark:text-slate-400">
                        {t('patient_details.chart.surfaces', 'Surfaces')} ({resolvedActiveTooth}):
                    </span>
                    {['M', 'D', 'O', 'I', 'B', 'L', 'P'].map((code) => {
                        const isSelected = activeSurfaces.includes(code);
                        return (
                            <button
                                key={code}
                                type="button"
                                onClick={() => handleToggleSurface(code)}
                                aria-pressed={isSelected}
                                data-testid={`surface-pill-${code}`}
                                className={`min-h-11 rounded-xl border px-3 py-1.5 text-xs font-bold transition-all ${
                                    isSelected
                                        ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                                }`}
                            >
                                {code}
                            </button>
                        );
                    })}
                </div>
            )}

            <ChartQuickActionLauncher
                selectedTeeth={selectedTeeth}
                selectedSurfacesByTooth={selectedSurfacesByTooth}
                onAction={handleQuickLauncherAction}
                onActivateStickyTool={(tool) => {
                    setActiveStickyTool(tool);
                    setStickyAppliedCount(0);
                }}
                clinicProcedures={procedures}
                onClose={handleClearSelection}
            />

            <ClinicalChartInspector
                copy={CLINICAL_CHART_COPY[i18n?.language?.startsWith('ar') ? 'ar' : 'en'] || CLINICAL_CHART_COPY.en}
                title={t('patient_details.chart.title')}
                selection={{
                    toothKey: resolvedActiveTooth,
                    surfaceCode: activeSurfaces[0] || null,
                    surfaceCodes: activeSurfaces,
                }}
                toothState={adaptedChart?.projection?.teeth?.[resolvedActiveTooth]}
                workItems={workspaceSnapshot?.work_items || []}
                treatments={history || []}
                treatmentPlans={treatmentPlans || []}
                payments={payments || []}
                onRemoveItem={handleRemoveWorkItemOrTreatment}
                patientId={patientId}
                attachments={attachments}
                attachmentLinks={attachmentLinks}
                activeCareSession={activeCareSession}
            />
        </div>
    );
}

ChairsideSelectionBar.propTypes = {
    selectedTeeth: PropTypes.arrayOf(PropTypes.string).isRequired,
    resolvedActiveTooth: PropTypes.string,
    setActiveToothKey: PropTypes.func.isRequired,
    handleRemoveToothFromSelection: PropTypes.func.isRequired,
    isMultiSelectMode: PropTypes.bool.isRequired,
    handleClearSelection: PropTypes.func.isRequired,
    handleRecordTreatmentFromSelection: PropTypes.func.isRequired,
    activeSurfaces: PropTypes.arrayOf(PropTypes.string).isRequired,
    handleToggleSurface: PropTypes.func.isRequired,
    selectedSurfacesByTooth: PropTypes.object.isRequired,
    handleQuickLauncherAction: PropTypes.func.isRequired,
    setActiveStickyTool: PropTypes.func.isRequired,
    setStickyAppliedCount: PropTypes.func.isRequired,
    procedures: PropTypes.array,
    i18n: PropTypes.object,
    t: PropTypes.func.isRequired,
    adaptedChart: PropTypes.object,
    workspaceSnapshot: PropTypes.object,
    history: PropTypes.array,
    treatmentPlans: PropTypes.array,
    payments: PropTypes.array,
    handleRemoveWorkItemOrTreatment: PropTypes.func.isRequired,
};
