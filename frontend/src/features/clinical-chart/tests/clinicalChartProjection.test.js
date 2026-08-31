import { describe, expect, it } from 'vitest';
import {
    CLINICAL_CHART_PROJECTION_VERSION,
    PROJECTION_DENTITIONS,
    PROJECTION_TARGET_KINDS,
    PROJECTION_VISUAL_PHASES,
    createClinicalChartProjection,
    createProjectionTarget,
    createToothVisualState,
} from '../domain/clinicalChartProjection';
import {
    ADULT_BASELINE_PROJECTION,
    DEMO_PROJECTION_FIXTURES,
    TARGET_COVERAGE_PROJECTION,
} from '../fixtures/demoProjectionFixtures';
import {
    CHART_INTERACTION_MODES,
    createClinicalChartRendererInput,
} from '../rendering/ClinicalChartRendererAdapter';

describe('clinical chart demo projection DTO', () => {
    it('creates a complete serializable adult baseline fixture', () => {
        expect(ADULT_BASELINE_PROJECTION.schemaVersion)
            .toBe(CLINICAL_CHART_PROJECTION_VERSION);
        expect(ADULT_BASELINE_PROJECTION.dentition)
            .toBe(PROJECTION_DENTITIONS.PERMANENT);
        expect(ADULT_BASELINE_PROJECTION.toothOrder).toHaveLength(32);
        expect(Object.keys(ADULT_BASELINE_PROJECTION.teeth)).toHaveLength(32);
        expect(ADULT_BASELINE_PROJECTION.teeth[11]).toEqual({
            toothKey: '11',
            lifecycle: 'PRESENT',
            findings: [],
            procedures: [],
            selection: { isSelected: false, targets: [] },
            disabled: false,
            annotations: [],
        });
        expect(JSON.parse(JSON.stringify(ADULT_BASELINE_PROJECTION)))
            .toEqual(ADULT_BASELINE_PROJECTION);
        expect(Object.isFrozen(ADULT_BASELINE_PROJECTION)).toBe(true);
        expect(Object.isFrozen(ADULT_BASELINE_PROJECTION.teeth[11])).toBe(true);
    });

    it('loads fixtures that cover whole-tooth, surface, root, and canal targets', () => {
        expect(Object.keys(DEMO_PROJECTION_FIXTURES)).toEqual(['adultBaseline', 'targetCoverage']);

        const wholeToothTarget = TARGET_COVERAGE_PROJECTION.teeth[14].procedures[0].targets[0];
        const surfaceTarget = TARGET_COVERAGE_PROJECTION.teeth[46].findings[0].targets[0];
        const rootTarget = TARGET_COVERAGE_PROJECTION.teeth[11].procedures[0].targets[0];
        const canalTarget = TARGET_COVERAGE_PROJECTION.teeth[16].findings[0].targets[0];

        expect(wholeToothTarget).toEqual({ kind: 'tooth', toothKey: '14' });
        expect(surfaceTarget).toEqual({ kind: 'surface', toothKey: '46', surfaceCode: 'D' });
        expect(rootTarget).toEqual({ kind: 'root', toothKey: '11', rootId: 'single' });
        expect(canalTarget).toEqual({
            kind: 'canal',
            toothKey: '16',
            rootId: 'mesiobuccal',
            canalId: null,
        });
    });

    it('documents every tooth visual-state field in normalized output', () => {
        const state = createToothVisualState({
            toothKey: '46',
            lifecycle: 'IMPACTED',
            findings: [{ code: 'CARIES' }],
            procedures: [{
                code: 'REST_COMPOSITE',
                phase: PROJECTION_VISUAL_PHASES.PLANNED,
            }],
            selection: {
                isSelected: true,
                targets: [{ kind: PROJECTION_TARGET_KINDS.TOOTH, toothKey: '46' }],
            },
            disabled: true,
            annotations: [{ text: 'Demo note' }],
        });

        expect(state).toMatchObject({
            toothKey: '46',
            lifecycle: 'IMPACTED',
            disabled: true,
            selection: { isSelected: true },
        });
        expect(state.findings[0]).toMatchObject({
            visualId: 'finding:46:1',
            code: 'CARIES',
            phase: 'existing',
        });
        expect(state.procedures[0]).toMatchObject({
            visualId: 'procedure:46:1',
            code: 'REST_COMPOSITE',
            phase: 'planned',
        });
        expect(state.annotations[0]).toEqual({
            annotationId: 'tooth:46:annotation:1',
            text: 'Demo note',
            target: null,
        });
    });

    it('supports explicit mixed dentition while preserving stable FDI identity', () => {
        const projection = createClinicalChartProjection({
            projectionId: 'mixed-demo',
            dentition: PROJECTION_DENTITIONS.MIXED,
            toothOrder: ['11', '51', '31', '71'],
        });

        expect(projection.toothOrder).toEqual(['11', '51', '31', '71']);
        expect(Object.keys(projection.teeth)).toEqual(['11', '31', '51', '71']);
    });

    it('preserves projection metadata when passed through the renderer input boundary', () => {
        const input = createClinicalChartRendererInput({
            chartId: 'projection-adapter-test',
            visualState: TARGET_COVERAGE_PROJECTION,
            interactionMode: CHART_INTERACTION_MODES.READ_ONLY,
        });

        expect(input.visualState.schemaVersion).toBe(1);
        expect(input.visualState.projectionId).toBe('demo-target-coverage');
        expect(input.visualState.toothOrder).toHaveLength(32);
        expect(input.visualState.teeth[16].findings[0].code).toBe('PAIN');
    });

    it('rejects invalid target geometry references', () => {
        expect(() => createProjectionTarget({ kind: 'tooth', toothKey: '99' }))
            .toThrow('Unknown tooth key: 99');
        expect(() => createProjectionTarget({
            kind: 'surface',
            toothKey: '46',
            surfaceCode: 'X',
        })).toThrow('Surface code X is not valid for tooth 46');
        expect(() => createProjectionTarget({
            kind: 'surface',
            toothKey: '46',
            surfaceCode: 'I',
        })).toThrow('Surface code I is not valid for tooth 46');
        expect(() => createProjectionTarget({
            kind: 'surface',
            toothKey: '11',
            surfaceCode: 'L',
        })).toThrow('Surface code L is not valid for tooth 11');
        expect(() => createProjectionTarget({
            kind: 'root',
            toothKey: '11',
            rootId: 'palatal',
        })).toThrow('Unknown root palatal for tooth 11');
    });

    it('rejects cross-tooth state targets and projection ordering errors', () => {
        expect(() => createToothVisualState({
            toothKey: '46',
            findings: [{
                code: 'CARIES',
                targets: [{ kind: 'surface', toothKey: '36', surfaceCode: 'D' }],
            }],
        })).toThrow('finding targets must belong to tooth 46');

        expect(() => createClinicalChartProjection({
            projectionId: 'mixed-without-order',
            dentition: PROJECTION_DENTITIONS.MIXED,
        })).toThrow('mixed dentition requires an explicit toothOrder');

        expect(() => createClinicalChartProjection({
            projectionId: 'wrong-dentition',
            dentition: PROJECTION_DENTITIONS.PRIMARY,
            toothOrder: ['11'],
        })).toThrow('Tooth 11 does not belong to primary dentition');

        expect(() => createClinicalChartProjection({
            projectionId: 'hidden-state',
            toothOrder: ['11'],
            teeth: { 12: { lifecycle: 'PRESENT' } },
        })).toThrow('Tooth state 12 is not present in toothOrder');

        expect(() => createToothVisualState({
            toothKey: '46',
            disabled: 'false',
        })).toThrow('disabled must be a boolean');
        expect(() => createToothVisualState({
            toothKey: '46',
            lifecycle: 'UNKNOWN',
        })).toThrow('lifecycle must be one of');
        expect(() => createToothVisualState({
            toothKey: '46',
            findings: [{ code: 'TYPO_FINDING' }],
        })).toThrow('finding.code must be one of');
        expect(() => createToothVisualState({
            toothKey: '46',
            procedures: [{ code: 'TYPO_PROCEDURE' }],
        })).toThrow('procedure.code must be one of');
    });
});
