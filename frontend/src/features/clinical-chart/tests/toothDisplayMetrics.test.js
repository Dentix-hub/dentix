import { describe, expect, it } from 'vitest';
import {
    TOOTH_DISPLAY_METRICS,
    getToothDisplayMetrics,
} from '../domain/toothDisplayMetrics';

describe('tooth display metrics', () => {
    it('provides immutable display proportions for all 52 FDI teeth', () => {
        expect(Object.keys(TOOTH_DISPLAY_METRICS)).toHaveLength(52);

        Object.values(TOOTH_DISPLAY_METRICS).forEach((metrics) => {
            expect(Object.isFrozen(metrics)).toBe(true);
            expect(metrics.rootScale).toEqual(expect.objectContaining({
                x: expect.any(Number),
                y: expect.any(Number),
            }));
            expect(metrics).not.toHaveProperty('crownScale');
            expect(metrics).not.toHaveProperty('crownPivot');
        });
    });

    it('gives only permanent upper central incisors the approved subtle root increase', () => {
        expect(getToothDisplayMetrics('11').rootScale).toEqual({ x: 0.97, y: 0.96 });
        expect(getToothDisplayMetrics('21').rootScale).toEqual({ x: 0.97, y: 0.96 });
        expect(getToothDisplayMetrics('31').rootScale).toEqual({ x: 0.95, y: 0.92 });
        expect(getToothDisplayMetrics('41').rootScale).toEqual({ x: 0.95, y: 0.92 });
    });
});
