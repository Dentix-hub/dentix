import { describe, expect, it } from 'vitest';
import { createToothVisualState } from '../domain/clinicalChartProjection';
import {
    FINDING_CODES,
    PROCEDURE_CODES,
    TOOTH_LIFECYCLE_CODES,
    VISUAL_LAYER_ROLES,
    VISUAL_LAYER_SEQUENCE,
    VISUAL_RULE_REGISTRY,
    getVisualRule,
    resolveClinicalChartVisuals,
    resolveToothVisualInstructions,
} from '../domain/visualRuleRegistry';
import { VISUAL_RULE_DEMO_PROJECTION } from '../fixtures/visualRuleDemoProjection';

describe('clinical chart visual rule registry', () => {
    it('defines the stable six-layer rendering sequence', () => {
        expect(VISUAL_LAYER_SEQUENCE).toEqual([
            'base-anatomy',
            'lifecycle',
            'findings',
            'existing-completed-work',
            'planned-active-work',
            'selection-focus',
        ]);
        expect(new Set(VISUAL_LAYER_SEQUENCE).size).toBe(6);
        expect(Object.isFrozen(VISUAL_LAYER_SEQUENCE)).toBe(true);
    });

    it('registers every required lifecycle, finding, and procedure rule', () => {
        expect(Object.keys(VISUAL_RULE_REGISTRY.lifecycle).sort())
            .toEqual(Object.values(TOOTH_LIFECYCLE_CODES).sort());
        expect(Object.keys(VISUAL_RULE_REGISTRY.finding).sort())
            .toEqual(Object.values(FINDING_CODES).sort());
        expect(Object.keys(VISUAL_RULE_REGISTRY.procedure).sort())
            .toEqual(Object.values(PROCEDURE_CODES).sort());

        expect(getVisualRule('finding', 'caries')).toMatchObject({
            effect: 'surface-caries',
            layerRole: VISUAL_LAYER_ROLES.FINDINGS,
        });
        expect(getVisualRule('procedure', 'rest_composite').presentation.fill)
            .toBe('#2563eb');
        expect(getVisualRule('procedure', 'unknown')).toBeNull();
    });

    it('maps planned/active and existing/completed procedures to separate layers', () => {
        const state = createToothVisualState({
            toothKey: '46',
            procedures: [
                { code: 'REST_COMPOSITE', phase: 'existing', targets: [{ kind: 'surface', toothKey: '46', surfaceCode: 'M' }] },
                { code: 'REST_COMPOSITE', phase: 'completed', targets: [{ kind: 'surface', toothKey: '46', surfaceCode: 'D' }] },
                { code: 'REST_COMPOSITE', phase: 'planned', targets: [{ kind: 'surface', toothKey: '46', surfaceCode: 'O' }] },
                { code: 'ENDO_RCT', phase: 'active', targets: [{ kind: 'root', toothKey: '46', rootId: 'mesial' }] },
            ],
        });
        const visual = resolveToothVisualInstructions(state);

        expect(visual.byLayer[VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK]).toHaveLength(2);
        expect(visual.byLayer[VISUAL_LAYER_ROLES.PLANNED_ACTIVE_WORK]).toHaveLength(2);
        expect(visual.byLayer[VISUAL_LAYER_ROLES.PLANNED_ACTIVE_WORK][0].presentation.strokeDasharray)
            .toBe('4 2');
        expect(visual.byLayer[VISUAL_LAYER_ROLES.PLANNED_ACTIVE_WORK][1].presentation.strokeDasharray)
            .toBe('2.5 1.5');
        expect(visual.instructions.map((instruction) => instruction.layerIndex))
            .toEqual([...visual.instructions.map((instruction) => instruction.layerIndex)].sort());
    });

    it('adds selection and disabled visuals last without mutating clinical entries', () => {
        const state = createToothVisualState({
            toothKey: '11',
            findings: [{ code: 'FRACTURE' }],
            selection: { isSelected: true, targets: [] },
            disabled: true,
        });
        const visual = resolveToothVisualInstructions(state);

        expect(visual.byLayer[VISUAL_LAYER_ROLES.SELECTION_FOCUS].map(({ effect }) => effect))
            .toEqual(['selected', 'disabled']);
        expect(visual.instructions.at(-1).layerRole).toBe(VISUAL_LAYER_ROLES.SELECTION_FOCUS);
        expect(state.findings[0]).not.toHaveProperty('effect');
    });

    it('resolves the A9 demo fixture across all required semantic codes', () => {
        const visuals = resolveClinicalChartVisuals(VISUAL_RULE_DEMO_PROJECTION);
        const instructions = Object.values(visuals).flatMap(({ instructions: toothInstructions }) => (
            toothInstructions
        ));
        const codes = new Set(instructions.map(({ code }) => code));

        Object.values(TOOTH_LIFECYCLE_CODES).forEach((code) => expect(codes).toContain(code));
        Object.values(FINDING_CODES).forEach((code) => expect(codes).toContain(code));
        Object.values(PROCEDURE_CODES).forEach((code) => expect(codes).toContain(code));
        expect(visuals[46].byLayer[VISUAL_LAYER_ROLES.FINDINGS][0].target)
            .toEqual({ kind: 'surface', toothKey: '46', surfaceCode: 'D' });
        expect(visuals[44].byLayer[VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK])
            .toHaveLength(3);
        expect(Object.isFrozen(visuals)).toBe(true);
    });

    it('keeps unknown semantic codes in the DTO but safely omits unresolved drawing instructions', () => {
        const state = createToothVisualState({
            toothKey: '11',
            findings: [{ code: 'FUTURE_FINDING' }],
            procedures: [{ code: 'FUTURE_PROCEDURE' }],
        });
        const visual = resolveToothVisualInstructions(state);

        expect(state.findings[0].code).toBe('FUTURE_FINDING');
        expect(visual.instructions.map(({ category }) => category)).toEqual(['lifecycle']);
    });
});
