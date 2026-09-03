import { useCallback, useMemo, useState } from 'react';
import ClinicalChartRenderer from './components/ClinicalChartRenderer';
import DualChartCompareWorkspace from './components/DualChartCompareWorkspace';
import { DENTAL_ANATOMY_REGISTRY, DENTITIONS } from './domain/dentalAnatomyRegistry';
import { VISUAL_RULE_DEMO_PROJECTION } from './fixtures/visualRuleDemoProjection';
import {
    CHART_INTERACTION_MODES,
    CHART_INTENT_TYPES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from './rendering/ClinicalChartRendererAdapter';

/**
 * Isolated entry point for the Dentix-native clinical chart.
 *
 * Supports both single-chart focused editing and dual-chart history comparison.
 */
export default function ClinicalChartWorkspace({ initialViewMode = 'single' }) {
    const [viewMode, setViewMode] = useState(initialViewMode);
    const [selection, setSelection] = useState(null);

    const handleIntent = useCallback((intent) => {
        if (intent.type !== CHART_INTENT_TYPES.SURFACE_SELECTED) return;

        setSelection((current) => (
            current?.kind === 'surface'
            && current.toothKey === intent.target.toothKey
            && current.surfaceCode === intent.target.surfaceCode
                ? null
                : intent.target
        ));
    }, []);

    const rendererInput = useMemo(() => createClinicalChartRendererInput({
        chartId: 'odontogram-demo',
        anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
        dentition: DENTITIONS.PERMANENT,
        visualState: {
            ...VISUAL_RULE_DEMO_PROJECTION,
            selection,
        },
        notationMode: CHART_NOTATION_MODES.PALMER,
        interactionMode: CHART_INTERACTION_MODES.EDIT,
        layers: {
            roots: true,
            surfaces: true,
        },
        callbacks: {
            onIntent: handleIntent,
        },
    }), [handleIntent, selection]);

    return (
        <main className="min-h-screen bg-background p-4 sm:p-6" data-testid="clinical-chart-workspace">
            <div className="mx-auto max-w-7xl">
                <div className="mb-6 flex items-center justify-between border-b border-slate-200 pb-3" role="tablist">
                    <div className="flex gap-2">
                        <div
                            aria-selected={viewMode === 'single'}
                            className={`cursor-pointer rounded-lg px-4 py-2 text-sm font-bold transition ${viewMode === 'single' ? 'bg-primary text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                            data-testid="tab-single-chart"
                            onClick={() => setViewMode('single')}
                            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setViewMode('single')}
                            role="tab"
                            tabIndex={0}
                        >
                            المخطط الفردي (Single Chart)
                        </div>
                        <div
                            aria-selected={viewMode === 'dual'}
                            className={`cursor-pointer rounded-lg px-4 py-2 text-sm font-bold transition ${viewMode === 'dual' ? 'bg-primary text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                            data-testid="tab-dual-chart"
                            onClick={() => setViewMode('dual')}
                            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setViewMode('dual')}
                            role="tab"
                            tabIndex={0}
                        >
                            مقارنة السجل والتاريخ (Dual History Compare)
                        </div>
                    </div>
                </div>

                {viewMode === 'single' ? (
                    <ClinicalChartRenderer input={rendererInput} />
                ) : (
                    <DualChartCompareWorkspace />
                )}
            </div>
        </main>
    );
}
