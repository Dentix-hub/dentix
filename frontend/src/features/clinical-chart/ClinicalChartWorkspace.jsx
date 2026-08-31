import { useCallback, useMemo, useState } from 'react';
import ClinicalChartRenderer from './components/ClinicalChartRenderer';
import { DENTAL_ANATOMY_REGISTRY, DENTITIONS } from './domain/dentalAnatomyRegistry';
import { VISUAL_RULE_DEMO_PROJECTION } from './fixtures/visualRuleDemoProjection';
import {
    CHART_INTERACTION_MODES,
    CHART_INTENT_TYPES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererInput,
} from './rendering/ClinicalChartRendererAdapter';

/**
 * Isolated entry point for the Dentix-native odontogram foundation.
 *
 * Clinical data is intentionally absent during the scaffold phase. Later phases
 * inject a Projection DTO and keep persistence outside this workspace.
 */
export default function ClinicalChartWorkspace() {
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
                <ClinicalChartRenderer input={rendererInput} />
            </div>
        </main>
    );
}
