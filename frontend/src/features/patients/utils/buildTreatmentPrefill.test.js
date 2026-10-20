import { describe, it, expect } from 'vitest';
import { buildTreatmentPrefill } from './buildTreatmentPrefill';

describe('buildTreatmentPrefill utility (U3.2)', () => {
    const baseTreatment = {
        patient_id: 101,
        doctor_id: 5,
        diagnosis: 'Decay',
        cost: 0,
        discount: 0,
        status: 'Done',
        notes: '',
        consumedMaterials: [],
    };

    it('builds prefill for quick launcher handoff with toothKey and procedure', () => {
        const result = buildTreatmentPrefill({
            baseTreatment,
            source: 'quick_launcher',
            toothKey: '16',
            surfaces: ['O'],
            procedureName: 'Composite Class I',
            defaultPriceListId: 10,
        });

        expect(result.prefill_source).toBe('quick_launcher');
        expect(result.tooth_number).toBe('UR6');
        expect(result.procedure).toBe('Composite Class I');
        expect(result.surface).toBe('O');
        expect(result.surfaces).toEqual(['O']);
        expect(result.target_kind).toBe('surface');
        expect(result.default_price_list_id).toBe(10);
        expect(result.diagnosis).toBe('Decay');
    });

    it('builds prefill for plan item execution with clinicalWorkItemId and plan title', () => {
        const result = buildTreatmentPrefill({
            baseTreatment,
            source: 'plan_item',
            toothKey: 21,
            surfaces: ['M', 'O'],
            procedureName: 'Direct Composite Veneer',
            clinicalWorkItemId: 402,
            planTitle: 'Phase 1 - Esthetics',
            planId: 12,
            workItemCode: 'REST_COMP',
            defaultPriceListId: null,
        });

        expect(result.prefill_source).toBe('plan_item');
        expect(result.tooth_number).toBe('UL1');
        expect(result.procedure).toBe('Direct Composite Veneer');
        expect(result.surface).toBe('MO');
        expect(result.surfaces).toEqual(['M', 'O']);
        expect(result.target_kind).toBe('surface');
        expect(result.clinical_work_item_id).toBe(402);
        expect(result.plan_title).toBe('Phase 1 - Esthetics');
        expect(result.plan_id).toBe(12);
        expect(result.work_item_code).toBe('REST_COMP');
    });

    it('supports pre-formatted Palmer tooth prefix without re-conversion', () => {
        const result = buildTreatmentPrefill({
            baseTreatment,
            source: 'tooth_picker',
            palmerTooth: 'LR5',
            surfaces: [],
            targetKind: 'tooth',
        });

        expect(result.tooth_number).toBe('LR5');
        expect(result.target_kind).toBe('tooth');
        expect(result.surface).toBe('');
        expect(result.surfaces).toEqual([]);
        expect(result.prefill_source).toBe('tooth_picker');
    });

    it('normalizes surface string to array and upper case', () => {
        const result = buildTreatmentPrefill({
            baseTreatment,
            source: 'chart_selection',
            toothKey: '36',
            surface: 'mod',
        });

        expect(result.tooth_number).toBe('LL6');
        expect(result.surface).toBe('MOD');
        expect(result.surfaces).toEqual(['M', 'O', 'D']);
        expect(result.target_kind).toBe('surface');
    });

    it('does not mutate baseTreatment input', () => {
        const originalBase = { ...baseTreatment };
        const result = buildTreatmentPrefill({
            baseTreatment: originalBase,
            source: 'quick_launcher',
            toothKey: '11',
        });

        expect(result).not.toBe(originalBase);
        expect(originalBase.tooth_number).toBeUndefined();
        expect(originalBase.prefill_source).toBeUndefined();
    });
});
