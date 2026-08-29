import { describe, expect, it } from 'vitest';
import { getOrganicToothType } from '@/features/dental/v3/assets/dentalPaths';
import { PERMANENT_TOOTH_KEYS, PRIMARY_TOOTH_KEYS } from '../domain/dentalAnatomyRegistry';
import { fdiToUniversal, getCrownGeometry } from '../rendering/crownGeometry';

describe('normalized crown geometry access', () => {
    it('resolves every registered tooth through a single FDI lookup', () => {
        [...PERMANENT_TOOTH_KEYS, ...PRIMARY_TOOTH_KEYS].forEach((toothKey) => {
            const geometry = getCrownGeometry(toothKey);
            expect(geometry?.toothKey).toBe(toothKey);
            expect(Object.values(geometry.paths).every(Boolean)).toBe(true);
        });
    });

    it.each([
        ['18', 1], ['11', 8], ['21', 9], ['28', 16],
        ['38', 17], ['31', 24], ['41', 25], ['48', 32],
    ])('maps FDI %s to current Universal geometry %i', (fdi, universal) => {
        expect(fdiToUniversal(fdi)).toBe(universal);
    });

    it('preserves current permanent crown paths and style tokens unchanged', () => {
        const currentSource = getOrganicToothType(3);
        const normalized = getCrownGeometry('16');

        expect(normalized.paths).toEqual(currentSource.CrownBox);
        expect(normalized.style).toEqual({ fill: '#ffffff', stroke: '#cbd5e1', strokeWidth: 1 });
    });
});

