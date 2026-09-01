import { useMemo, useState } from 'react';
import ClinicalChartRenderer from './ClinicalChartRenderer';
import { DENTAL_ANATOMY_REGISTRY } from '../domain/dentalAnatomyRegistry';
import {
    CHART_INTERACTION_MODES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';

const FOCUS_OPTIONS = Object.freeze([
    Object.freeze({ value: '', label: 'None', selection: null }),
    Object.freeze({
        value: '46:D',
        label: 'Tooth 46 - Distal surface (D)',
        selection: Object.freeze({ kind: 'surface', toothKey: '46', surfaceCode: 'D' }),
    }),
    Object.freeze({
        value: '36:O',
        label: 'Tooth 36 - Occlusal surface (O)',
        selection: Object.freeze({ kind: 'surface', toothKey: '36', surfaceCode: 'O' }),
    }),
]);

const focusValueFor = (selection) => (
    selection?.kind === 'surface' ? selection.toothKey + ':' + selection.surfaceCode : ''
);

/**
 * Owns presentation-only state for exactly one comparison chart. The state is
 * deliberately local so no selection or layer filter can leak to its sibling.
 */
export default function ClinicalChartComparisonCard({
    chartId,
    title,
    subtitle,
    projection,
    initialSelection = null,
}) {
    const [selection, setSelection] = useState(initialSelection);
    const [showRoots, setShowRoots] = useState(true);
    const [showClinicalLayers, setShowClinicalLayers] = useState(true);

    const visualState = useMemo(() => ({
        ...projection,
        teeth: showClinicalLayers ? projection.teeth : {},
        selection,
    }), [projection, selection, showClinicalLayers]);

    const rendererInput = useMemo(() => createClinicalChartRendererInput({
        chartId,
        anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
        dentition: projection.dentition,
        visualState,
        notationMode: CHART_NOTATION_MODES.PALMER,
        interactionMode: CHART_INTERACTION_MODES.READ_ONLY,
        layers: {
            roots: showRoots,
            surfaces: false,
        },
        callbacks: {},
    }), [chartId, projection.dentition, showRoots, visualState]);

    const handleFocusChange = (event) => {
        const option = FOCUS_OPTIONS.find(({ value }) => value === event.target.value);
        setSelection(option?.selection ?? null);
    };

    return (
        <section
            aria-labelledby={chartId + '-title'}
            className="min-w-0 rounded-3xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4"
            data-chart-instance={chartId}
            data-selected-focus={focusValueFor(selection)}
            data-testid="clinical-chart-instance"
        >
            <header className="mb-3 flex flex-col gap-3 border-b border-slate-100 pb-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                    <h2 id={chartId + '-title'} className="text-base font-bold text-slate-900 sm:text-lg">
                        {title}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
                </div>

                <div className="flex flex-wrap items-end gap-3 text-sm">
                    <label className="flex min-w-48 flex-col gap-1 font-medium text-slate-700">
                        Preview focus
                        <select
                            aria-label={'Preview focus - ' + title}
                            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                            onChange={handleFocusChange}
                            value={focusValueFor(selection)}
                        >
                            {FOCUS_OPTIONS.map(({ value, label }) => (
                                <option key={value || 'none'} value={value}>{label}</option>
                            ))}
                        </select>
                    </label>

                    <label className="flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-slate-700">
                        <input aria-label={'Show roots - ' + title} checked={showRoots} onChange={(event) => setShowRoots(event.target.checked)} type="checkbox" />
                        Roots
                    </label>

                    <label className="flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-slate-700">
                        <input aria-label={'Show conditions and procedures - ' + title} checked={showClinicalLayers} onChange={(event) => setShowClinicalLayers(event.target.checked)} type="checkbox" />
                        Conditions and procedures
                    </label>
                </div>
            </header>

            <ClinicalChartRenderer input={rendererInput} />
        </section>
    );
}
