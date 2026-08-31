import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ClinicalChartRenderer from '../components/ClinicalChartRenderer';
import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
} from '../domain/dentalAnatomyRegistry';
import {
    CHART_INTERACTION_MODES,
    CHART_INTENT_TYPES,
    CHART_NOTATION_MODES,
    createClinicalChartRendererAdapter,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';

const createInput = (overrides = {}) => createClinicalChartRendererInput({
    chartId: 'adapter-test',
    anatomyDefinition: DENTAL_ANATOMY_REGISTRY,
    dentition: DENTITIONS.PERMANENT,
    visualState: {
        teeth: {},
        selection: null,
    },
    notationMode: CHART_NOTATION_MODES.PALMER,
    interactionMode: CHART_INTERACTION_MODES.EDIT,
    layers: {
        roots: true,
        surfaces: true,
    },
    callbacks: {},
    ...overrides,
});

describe('ClinicalChartRendererAdapter contract', () => {
    it('normalizes the documented renderer inputs and maps visual state to chart props', () => {
        const selection = { kind: 'surface', toothKey: '46', surfaceCode: 'O' };
        const teeth = { 46: { condition: 'Filled' } };
        const input = createInput({
            visualState: { teeth, selection },
            notationMode: CHART_NOTATION_MODES.FDI,
        });
        const adapter = createClinicalChartRendererAdapter(input);

        expect(Object.keys(adapter.input.anatomyDefinition)).toHaveLength(52);
        expect(adapter.chartProps).toMatchObject({
            teethStatus: teeth,
            isPediatric: false,
            showRoots: true,
            enableSurfaceSelection: true,
            selectedSurface: selection,
            readOnly: false,
            notationMode: CHART_NOTATION_MODES.FDI,
        });
    });

    it('emits neutral tooth, surface, root, and multi-select intents through callbacks', () => {
        const onIntent = vi.fn();
        const onToothSelected = vi.fn();
        const onSurfaceSelected = vi.fn();
        const onRootSelected = vi.fn();
        const onMultiSelectChanged = vi.fn();
        const adapter = createClinicalChartRendererAdapter(createInput({
            callbacks: {
                onIntent,
                onToothSelected,
                onSurfaceSelected,
                onRootSelected,
                onMultiSelectChanged,
            },
        }));

        const toothIntent = adapter.intents.toothSelected(8);
        const surfaceIntent = adapter.intents.surfaceSelected({ toothKey: '46', surfaceCode: 'O' });
        const rootIntent = adapter.intents.rootSelected({ toothKey: '16', rootId: 'palatal' });
        const targets = [toothIntent.target, surfaceIntent.target];
        const multiIntent = adapter.intents.multiSelectChanged(targets);

        expect(toothIntent).toEqual({
            type: CHART_INTENT_TYPES.TOOTH_SELECTED,
            chartId: 'adapter-test',
            target: { kind: 'tooth', toothKey: '11' },
        });
        expect(surfaceIntent).toEqual({
            type: CHART_INTENT_TYPES.SURFACE_SELECTED,
            chartId: 'adapter-test',
            target: { kind: 'surface', toothKey: '46', surfaceCode: 'O' },
        });
        expect(rootIntent).toEqual({
            type: CHART_INTENT_TYPES.ROOT_SELECTED,
            chartId: 'adapter-test',
            target: { kind: 'root', toothKey: '16', rootId: 'palatal' },
        });
        expect(multiIntent).toEqual({
            type: CHART_INTENT_TYPES.MULTI_SELECT_CHANGED,
            chartId: 'adapter-test',
            targets,
        });
        expect(onIntent).toHaveBeenCalledTimes(4);
        expect(onToothSelected).toHaveBeenCalledWith(toothIntent);
        expect(onSurfaceSelected).toHaveBeenCalledWith(surfaceIntent);
        expect(onRootSelected).toHaveBeenCalledWith(rootIntent);
        expect(onMultiSelectChanged).toHaveBeenCalledWith(multiIntent);
    });

    it('uses the supplied anatomy definition as the interaction boundary', () => {
        const adapter = createClinicalChartRendererAdapter(createInput({
            anatomyDefinition: { 11: DENTAL_ANATOMY_REGISTRY[11] },
        }));

        expect(() => adapter.intents.toothSelected(8)).not.toThrow();
        expect(() => adapter.intents.surfaceSelected({ toothKey: '46', surfaceCode: 'O' }))
            .toThrow('Unknown tooth key: 46');
    });

    it.each([
        ['dentition', 'mixed'],
        ['notationMode', 'iso-unknown'],
        ['interactionMode', 'disabled'],
    ])('rejects unsupported %s values', (field, value) => {
        expect(() => createInput({ [field]: value })).toThrow(TypeError);
    });

    it.each([
        ['lifecycle', { lifecycle: 'UNKNOWN' }, 'Unknown lifecycle code: UNKNOWN'],
        ['finding', { findings: [{ code: 'UNKNOWN', targets: [] }] }, 'Unknown finding code: UNKNOWN'],
        ['procedure', { procedures: [{ code: 'UNKNOWN', targets: [] }] }, 'Unknown procedure code: UNKNOWN'],
    ])('rejects raw visual-state %s codes at the public adapter boundary', (_kind, toothState, message) => {
        const input = createInput({
            visualState: {
                teeth: { 11: toothState },
                selection: null,
            },
        });

        expect(() => createClinicalChartRendererAdapter(input)).toThrow(message);
    });

    it('renders through the adapter and forwards pointer interaction as a neutral intent', () => {
        const onSurfaceSelected = vi.fn();
        const input = createInput({ callbacks: { onSurfaceSelected } });
        const { container } = render(<ClinicalChartRenderer input={input} />);

        expect(container.firstChild).toHaveAttribute('data-notation-mode', 'palmer');
        expect(container.firstChild).toHaveAttribute('data-interaction-mode', 'edit');
        expect(container.querySelectorAll('[data-layer="roots"]')).toHaveLength(32);
        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(32);

        fireEvent.click(screen.getByRole('button', { name: 'Tooth UR1 — Mesial (M)' }));
        expect(onSurfaceSelected).toHaveBeenCalledWith({
            type: CHART_INTENT_TYPES.SURFACE_SELECTED,
            chartId: 'adapter-test',
            target: { kind: 'surface', toothKey: '11', surfaceCode: 'M' },
        });
    });

    it('renders read-only mode without exposing tooth or surface controls', () => {
        const input = createInput({
            interactionMode: CHART_INTERACTION_MODES.READ_ONLY,
            notationMode: CHART_NOTATION_MODES.FDI,
        });
        const { container } = render(<ClinicalChartRenderer input={input} />);

        expect(container.firstChild).toHaveAttribute('data-notation-mode', 'fdi');
        expect(container.firstChild).toHaveAttribute('data-interaction-mode', 'read-only');
        expect(screen.queryAllByRole('button')).toHaveLength(0);
        expect(container.querySelectorAll('[data-layer="surfaces"]')).toHaveLength(0);
        expect(container.querySelectorAll('[data-layer="roots"]')).toHaveLength(32);
    });
});
