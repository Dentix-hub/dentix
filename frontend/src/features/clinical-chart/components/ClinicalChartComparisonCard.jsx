import { useMemo, useRef, useState } from 'react';
import ClinicalChartRenderer from './ClinicalChartRenderer';
import ClinicalChartInspector from './ClinicalChartInspector';
import { DENTAL_ANATOMY_REGISTRY } from '../domain/dentalAnatomyRegistry';
import {
    CHART_INTERACTION_MODES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';

const FOCUS_OPTIONS = Object.freeze([
    Object.freeze({ value: '', labelKey: 'none', selection: null }),
    Object.freeze({
        value: '46:D',
        labelKey: 'tooth46Distal',
        selection: Object.freeze({ kind: 'surface', toothKey: '46', surfaceCode: 'D' }),
    }),
    Object.freeze({
        value: '36:O',
        labelKey: 'tooth36Occlusal',
        selection: Object.freeze({ kind: 'surface', toothKey: '36', surfaceCode: 'O' }),
    }),
]);

const QUADRANT_TARGETS = Object.freeze([
    Object.freeze({ key: 'upperRight', shortLabel: 'UR', toothKey: '14' }),
    Object.freeze({ key: 'upperLeft', shortLabel: 'UL', toothKey: '24' }),
    Object.freeze({ key: 'lowerRight', shortLabel: 'LR', toothKey: '44' }),
    Object.freeze({ key: 'lowerLeft', shortLabel: 'LL', toothKey: '34' }),
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
    copy,
    initialSelection = null,
}) {
    const chartFrameRef = useRef(null);
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

    const focusQuadrant = (toothKey) => {
        const selector = '[data-layer="crown"][data-tooth-key="' + toothKey + '"]';
        const target = chartFrameRef.current?.querySelector(selector);
        target?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    };

    return (
        <section
            aria-labelledby={chartId + '-title'}
            className="min-w-0 rounded-3xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4"
            data-chart-instance={chartId}
            data-selected-focus={focusValueFor(selection)}
            data-testid="clinical-chart-instance"
        >
            <header className="mb-3 flex flex-col gap-3 border-b border-slate-100 pb-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <h2 id={chartId + '-title'} className="text-base font-bold text-slate-900 sm:text-lg">
                        {title}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
                </div>

                <div className="flex flex-wrap items-end gap-3 text-sm">
                    <label className="flex min-w-48 flex-col gap-1 font-medium text-slate-700">
                        {copy.previewFocus}
                        <select
                            aria-label={copy.previewFocus + ' - ' + title}
                            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                            onChange={handleFocusChange}
                            value={focusValueFor(selection)}
                        >
                            {FOCUS_OPTIONS.map(({ value, labelKey }) => (
                                <option key={value || 'none'} value={value}>{copy.focusOptions[labelKey]}</option>
                            ))}
                        </select>
                    </label>

                    <label className="flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-slate-700">
                        <input
                            aria-label={copy.showRoots + ' - ' + title}
                            checked={showRoots}
                            className="h-4 w-4 rounded outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                            onChange={(event) => setShowRoots(event.target.checked)}
                            type="checkbox"
                        />
                        {copy.roots}
                    </label>

                    <label className="flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-slate-700">
                        <input
                            aria-label={copy.showClinicalLayers + ' - ' + title}
                            checked={showClinicalLayers}
                            className="h-4 w-4 rounded outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                            onChange={(event) => setShowClinicalLayers(event.target.checked)}
                            type="checkbox"
                        />
                        {copy.clinicalLayers}
                    </label>
                </div>
            </header>

            <nav aria-label={copy.mobileQuadrants} className="mb-3 grid grid-cols-4 gap-2 sm:hidden" data-mobile-quadrant-nav>
                {QUADRANT_TARGETS.map(({ key, shortLabel, toothKey }) => (
                    <button
                        aria-label={copy.quadrants[key]}
                        className="min-h-11 rounded-xl border border-slate-300 bg-slate-50 px-2 text-xs font-bold text-slate-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
                        key={key}
                        onClick={() => focusQuadrant(toothKey)}
                        type="button"
                    >
                        {shortLabel}
                    </button>
                ))}
            </nav>

            <div className="min-w-0" ref={chartFrameRef}>
                <ClinicalChartRenderer input={rendererInput} />
            </div>
            <ClinicalChartInspector
                copy={copy}
                selection={selection}
                title={title}
                toothState={projection.teeth[selection?.toothKey]}
            />
        </section>
    );
}
