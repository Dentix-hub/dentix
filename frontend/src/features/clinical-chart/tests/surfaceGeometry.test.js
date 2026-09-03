import { describe, expect, it } from 'vitest';
import { DENTAL_ANATOMY_REGISTRY } from '../domain/dentalAnatomyRegistry';
import {
    SURFACE_CODES,
    SURFACE_GEOMETRY_REGISTRY,
    getSurfaceGeometry,
} from '../rendering/surfaceGeometry';

const getCodes = (toothKey) => getSurfaceGeometry(toothKey).surfaces.map((surface) => surface.surfaceCode);

describe('surface geometry foundation', () => {
    it('exports the required clinical surface codes', () => {
        expect(SURFACE_CODES).toEqual({
            MESIAL: 'M',
            DISTAL: 'D',
            OCCLUSAL: 'O',
            INCISAL: 'I',
            BUCCAL: 'B',
            LINGUAL: 'L',
            PALATAL: 'P',
        });
    });

    it('resolves five closed clickable regions for all 52 FDI teeth', () => {
        expect(Object.keys(SURFACE_GEOMETRY_REGISTRY)).toHaveLength(52);

        Object.values(DENTAL_ANATOMY_REGISTRY).forEach((anatomy) => {
            const geometry = getSurfaceGeometry(anatomy.toothKey);
            expect(geometry.geometryRef).toBe(anatomy.surfaceMap.geometryRef);
            expect(geometry.surfaces).toHaveLength(5);
            expect(new Set(geometry.surfaces.map((surface) => surface.surfaceCode)).size).toBe(5);
            geometry.surfaces.forEach((surface) => {
                expect(surface.path).toMatch(/^M.* Z$/);
                expect(surface.path).not.toMatch(/NaN|undefined|Infinity/);
            });
        });
    });

    it('uses incisal anterior and occlusal posterior center regions', () => {
        expect(getCodes('11')).toEqual(expect.arrayContaining(['M', 'D', 'I', 'B', 'P']));
        expect(getCodes('31')).toEqual(expect.arrayContaining(['M', 'D', 'I', 'B', 'L']));
        expect(getCodes('16')).toEqual(expect.arrayContaining(['M', 'D', 'O', 'B', 'P']));
        expect(getCodes('36')).toEqual(expect.arrayContaining(['M', 'D', 'O', 'B', 'L']));
    });

    it('mirrors mesial and distal regions across right and left quadrants', () => {
        const rightMesial = getSurfaceGeometry('11').surfaces.find((surface) => surface.surfaceCode === 'M');
        const leftMesial = getSurfaceGeometry('21').surfaces.find((surface) => surface.surfaceCode === 'M');
        const rightDistal = getSurfaceGeometry('11').surfaces.find((surface) => surface.surfaceCode === 'D');

        expect(rightMesial.region).toBe('west');
        expect(leftMesial.region).toBe('east');
        expect(rightMesial.path).not.toBe(rightDistal.path);
    });

    it('supports primary anterior and posterior geometry through the same lookup', () => {
        expect(getSurfaceGeometry('51')).toMatchObject({ model: 'anterior', family: 'incisor' });
        expect(getSurfaceGeometry('53')).toMatchObject({ model: 'anterior', family: 'canine' });
        expect(getSurfaceGeometry('55')).toMatchObject({ model: 'posterior', family: 'molar' });
    });
});
