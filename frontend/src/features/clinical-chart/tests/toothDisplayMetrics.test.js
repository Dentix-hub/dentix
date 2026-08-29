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
            expect(metrics.crownScale).toBeGreaterThan(0);
            expect(metrics.rootScale).toEqual(expect.objectContaining({
                x: expect.any(Number),
                y: expect.any(Number),
            }));
        });
    });

    it.each([
        ['12', '11', 0.88],
        ['22', '21', 0.88],
        ['32', '31', 0.88],
        ['42', '41', 0.88],
        ['52', '51', 0.9],
        ['62', '61', 0.9],
        ['72', '71', 0.9],
        ['82', '81', 0.9],
    ])('keeps lateral FDI %s slightly smaller than central FDI %s', (lateralKey, centralKey, expectedScale) => {
        expect(getToothDisplayMetrics(lateralKey).crownScale).toBe(expectedScale);
        expect(getToothDisplayMetrics(lateralKey).crownScale)
            .toBeLessThan(getToothDisplayMetrics(centralKey).crownScale);
    });

    it('anchors crown scaling at the cervical edge used to join the root', () => {
        expect(getToothDisplayMetrics('12').crownPivot).toEqual({ x: 25, y: 12 });
        expect(getToothDisplayMetrics('42').crownPivot).toEqual({ x: 25, y: 42 });
    });

    it('gives only permanent upper central incisors the approved subtle root increase', () => {
        expect(getToothDisplayMetrics('11').rootScale).toEqual({ x: 0.97, y: 0.96 });
        expect(getToothDisplayMetrics('21').rootScale).toEqual({ x: 0.97, y: 0.96 });
        expect(getToothDisplayMetrics('31').rootScale).toEqual({ x: 0.95, y: 0.92 });
        expect(getToothDisplayMetrics('41').rootScale).toEqual({ x: 0.95, y: 0.92 });
    });
});
