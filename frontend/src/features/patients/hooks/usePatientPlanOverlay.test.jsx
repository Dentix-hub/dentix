import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { usePatientPlanOverlay } from './usePatientPlanOverlay';

// Shaped exactly like the API (ClinicalTreatmentPlanRead): the tooth lives in
// item.work_item.targets[].tooth_key — plan items have no tooth_number.
const plans = [
    {
        id: 7,
        title: 'Plan A',
        phases: [
            {
                id: 11,
                name: 'Phase One',
                phase_order: 0,
                items: [
                    { id: 1, work_item_id: 5, work_item: { id: 5, code: 'REST_COMPOSITE', targets: [{ tooth_key: '16' }] } },
                    { id: 2, work_item_id: 6, work_item: { id: 6, code: 'SCALING', targets: [{ tooth_key: '16' }, { tooth_key: '17' }] } },
                ],
            },
            {
                id: 12,
                name: 'Phase Two',
                phase_order: 1,
                items: [{ id: 3, work_item_id: 7, work_item: { id: 7, code: 'CROWN', targets: [{ tooth_key: '26' }] } }],
            },
        ],
    },
];

const run = (overrides = {}) =>
    renderHook(() =>
        usePatientPlanOverlay({ activeOverlayPlanId: 7, activeOverlayPhaseId: null, treatmentPlans: plans, ...overrides })
    ).result.current;

describe('usePatientPlanOverlay (contract read by DentalChartSVG / PlanOverlayActiveBanner)', () => {
    it('returns null without an active plan, without plans, or for an unknown plan', () => {
        expect(run({ activeOverlayPlanId: null })).toBeNull();
        expect(run({ treatmentPlans: [] })).toBeNull();
        expect(run({ treatmentPlans: undefined })).toBeNull();
        expect(run({ activeOverlayPlanId: 999 })).toBeNull();
    });

    it('maps work-item targets to per-tooth entries with the fields the chart reads', () => {
        const overlay = run();
        expect(Object.keys(overlay.teeth).sort()).toEqual(['16', '17', '26']);
        expect(overlay.teeth['16']).toMatchObject({
            phaseId: 11,
            phaseName: 'Phase One',
            phaseIndex: 0,
            badge: 'P1',
            color: '#2563eb',
            borderColor: '#3b82f6',
            bgColor: '#eff6ff',
        });
        expect(overlay.teeth['16'].procedureCodes).toEqual(['REST_COMPOSITE', 'SCALING']);
        expect(overlay.teeth['26']).toMatchObject({ badge: 'P2', phaseIndex: 1, color: '#059669' });
    });

    it('exposes planId/planTitle/phaseId and phase chips with text and badgeBg colors for the banner', () => {
        const overlay = run();
        expect(overlay.planId).toBe(7);
        expect(overlay.planTitle).toBe('Plan A');
        expect(overlay.phaseId).toBeNull();
        expect(overlay.phases).toHaveLength(2);
        expect(overlay.phases[0].colorConfig).toMatchObject({ border: '#3b82f6', bg: '#eff6ff', text: '#1d4ed8', badgeBg: '#2563eb' });
    });

    it('restricts teeth to the selected phase and reports it as phaseId', () => {
        const overlay = run({ activeOverlayPhaseId: 12 });
        expect(overlay.phaseId).toBe(12);
        expect(Object.keys(overlay.teeth)).toEqual(['26']);
        expect(overlay.phases).toHaveLength(2);
    });
});
