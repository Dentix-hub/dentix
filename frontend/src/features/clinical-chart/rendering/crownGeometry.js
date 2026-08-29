import { getOrganicToothType } from '@/features/dental/v3/assets/dentalPaths';
import { DENTITIONS, getDentalAnatomy } from '../domain/dentalAnatomyRegistry';

export const CROWN_STYLE_TOKENS = Object.freeze({
    permanent: Object.freeze({ fill: '#ffffff', stroke: '#cbd5e1', strokeWidth: 1 }),
    primary: Object.freeze({ fill: '#ffffff', stroke: '#94a3b8', strokeWidth: 2 }),
});

const PRIMARY_CROWN_PATHS = Object.freeze({
    maxillaryMolar: 'M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35',
    maxillaryCanine: 'M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z',
    maxillaryIncisor: 'M10,10 C15,8 35,8 40,10 C42,20 40,40 35,45 C30,48 20,48 15,45 C10,40 8,20 10,10 Z',
    mandibularMolar: 'M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35',
    mandibularCanine: 'M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z',
    mandibularIncisor: 'M15,12 C18,10 32,10 35,12 C36,20 35,35 32,40 C28,42 22,42 18,40 C15,35 14,20 15,12 Z',
});

export const fdiToUniversal = (toothKey) => {
    const key = String(toothKey);
    const quadrant = Number(key[0]);
    const position = Number(key[1]);

    if (quadrant === 1) return 9 - position;
    if (quadrant === 2) return 8 + position;
    if (quadrant === 3) return 25 - position;
    if (quadrant === 4) return 24 + position;
    return null;
};

const getPrimaryCrownPath = ({ arch, toothType }) => {
    const prefix = arch === 'maxillary' ? 'maxillary' : 'mandibular';
    const family = toothType === 'molar'
        ? 'Molar'
        : toothType === 'canine' ? 'Canine' : 'Incisor';
    return PRIMARY_CROWN_PATHS[`${prefix}${family}`];
};

/**
 * Resolves current Dentix crown geometry by stable FDI anatomy key.
 * The adapter preserves source path data and styling; it adds no clinical state.
 */
export const getCrownGeometry = (toothKey) => {
    const anatomy = getDentalAnatomy(toothKey);
    if (!anatomy) return null;

    if (anatomy.dentition === DENTITIONS.PERMANENT) {
        const universalNumber = fdiToUniversal(toothKey);
        const sourceGeometry = getOrganicToothType(universalNumber);

        return Object.freeze({
            toothKey: anatomy.toothKey,
            source: 'dental-v3-organic',
            sourceKey: universalNumber,
            viewBox: '0 0 100 160',
            geometryKind: 'surface-map',
            isMirror: Boolean(sourceGeometry.isMirror),
            paths: Object.freeze({ ...sourceGeometry.CrownBox }),
            style: CROWN_STYLE_TOKENS.permanent,
        });
    }

    return Object.freeze({
        toothKey: anatomy.toothKey,
        source: 'dental-chart-svg-primary-family',
        sourceKey: `${anatomy.arch}:${anatomy.toothType}`,
        viewBox: '0 0 50 60',
        geometryKind: 'outline',
        isMirror: anatomy.side === 'left',
        paths: Object.freeze({ outline: getPrimaryCrownPath(anatomy) }),
        style: CROWN_STYLE_TOKENS.primary,
    });
};

