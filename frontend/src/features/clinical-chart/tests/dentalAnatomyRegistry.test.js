import { describe, expect, it } from 'vitest';
import {
    DENTAL_ANATOMY_REGISTRY,
    DENTITIONS,
    PERMANENT_TOOTH_KEYS,
    PRIMARY_TOOTH_KEYS,
    getDentalAnatomy,
} from '../domain/dentalAnatomyRegistry';

describe('dentalAnatomyRegistry foundation', () => {
    it('covers every permanent and primary FDI position without collisions', () => {
        expect(PERMANENT_TOOTH_KEYS).toHaveLength(32);
        expect(PRIMARY_TOOTH_KEYS).toHaveLength(20);
        expect(new Set([...PERMANENT_TOOTH_KEYS, ...PRIMARY_TOOTH_KEYS]).size).toBe(52);
        expect(Object.keys(DENTAL_ANATOMY_REGISTRY)).toHaveLength(52);
    });

    it.each([
        ['11', DENTITIONS.PERMANENT, 'incisor', 1],
        ['14', DENTITIONS.PERMANENT, 'premolar', 2],
        ['16', DENTITIONS.PERMANENT, 'molar', 3],
        ['36', DENTITIONS.PERMANENT, 'molar', 2],
        ['51', DENTITIONS.PRIMARY, 'incisor', 1],
        ['65', DENTITIONS.PRIMARY, 'molar', 3],
        ['85', DENTITIONS.PRIMARY, 'molar', 2],
    ])('defines the required anatomy shape for FDI %s', (key, dentition, toothType, rootCount) => {
        const anatomy = getDentalAnatomy(key);

        expect(anatomy).toMatchObject({
            toothKey: key,
            dentition,
            toothType,
            rootCount,
        });
        expect(anatomy.crownOutlineRef).toBeTruthy();
        expect(anatomy.surfaceMap.geometryRef).toBeTruthy();
        expect(anatomy.rootOutlineRefs).toHaveLength(rootCount);
        expect(anatomy.canalAnchorPlaceholders).toHaveLength(rootCount);
        expect(anatomy.labelAnchor).toEqual(expect.objectContaining({ x: expect.any(Number), y: expect.any(Number) }));
        expect(anatomy.overlayAnchors).toEqual(expect.objectContaining({
            center: expect.any(Object),
            crown: expect.any(Object),
            root: expect.any(Object),
        }));
    });

    it('returns null for an unknown tooth key', () => {
        expect(getDentalAnatomy('99')).toBeNull();
    });
});
