import { DENTAL_ANATOMY_REGISTRY, getDentalAnatomy } from '../domain/dentalAnatomyRegistry';

export const SURFACE_CODES = Object.freeze({
    MESIAL: 'M',
    DISTAL: 'D',
    OCCLUSAL: 'O',
    INCISAL: 'I',
    BUCCAL: 'B',
    LINGUAL: 'L',
    PALATAL: 'P',
});

export const SURFACE_LABELS = Object.freeze({
    M: 'Mesial',
    D: 'Distal',
    O: 'Occlusal',
    I: 'Incisal',
    B: 'Buccal',
    L: 'Lingual',
    P: 'Palatal',
});

const POSTERIOR_PATHS = Object.freeze({
    west: 'M8,12 L17,17 L15,33 L10,42 Q5,27 8,12 Z',
    east: 'M42,12 Q45,27 40,42 L35,33 L33,17 Z',
    outer: 'M12,8 Q25,2 38,8 L33,17 L17,17 Z',
    inner: 'M15,33 L35,33 L38,42 Q25,49 12,42 Z',
    center: 'M17,17 L33,17 L35,33 L15,33 Z',
});

const ANTERIOR_INCISOR_PATHS = Object.freeze({
    west: 'M10,11 L17,18 L18,34 L15,43 Q8,31 10,11 Z',
    east: 'M40,11 Q42,31 35,43 L32,34 L33,18 Z',
    incisal: 'M11,10 Q25,6 39,10 L33,18 L17,18 Z',
    inner: 'M18,34 L32,34 L35,43 Q25,49 15,43 Z',
    center: 'M17,18 L33,18 L32,34 L18,34 Z',
});

const ANTERIOR_CANINE_PATHS = Object.freeze({
    west: 'M15,11 L20,18 L19,34 L17,39 Q11,25 15,11 Z',
    east: 'M35,11 Q39,25 33,39 L31,34 L30,18 Z',
    incisal: 'M19,34 L31,34 L33,39 L25,48 L17,39 Z',
    inner: 'M16,11 Q25,5 34,11 L30,18 L20,18 Z',
    center: 'M20,18 L30,18 L31,34 L19,34 Z',
});

const createSurface = (surfaceCode, path, region) => Object.freeze({
    surfaceCode,
    label: SURFACE_LABELS[surfaceCode],
    path,
    region,
});

const createSurfaceGeometry = (anatomy) => {
    const isPosterior = anatomy.surfaceMap.model === 'posterior';
    const isCanine = anatomy.toothType === 'canine';
    const paths = isPosterior
        ? POSTERIOR_PATHS
        : (isCanine ? ANTERIOR_CANINE_PATHS : ANTERIOR_INCISOR_PATHS);
    const centerCode = isPosterior ? SURFACE_CODES.OCCLUSAL : SURFACE_CODES.INCISAL;
    const innerCode = anatomy.arch === 'maxillary' ? SURFACE_CODES.PALATAL : SURFACE_CODES.LINGUAL;
    const westCode = anatomy.side === 'right' ? SURFACE_CODES.MESIAL : SURFACE_CODES.DISTAL;
    const eastCode = anatomy.side === 'right' ? SURFACE_CODES.DISTAL : SURFACE_CODES.MESIAL;

    const surfaces = isPosterior
        ? [
            createSurface(westCode, paths.west, 'west'),
            createSurface(eastCode, paths.east, 'east'),
            createSurface(SURFACE_CODES.BUCCAL, paths.outer, 'outer'),
            createSurface(innerCode, paths.inner, 'inner'),
            createSurface(centerCode, paths.center, 'center'),
        ]
        : [
            createSurface(westCode, paths.west, 'west'),
            createSurface(eastCode, paths.east, 'east'),
            createSurface(centerCode, paths.incisal, 'incisal'),
            createSurface(innerCode, paths.inner, 'inner'),
            createSurface(SURFACE_CODES.BUCCAL, paths.center, 'center'),
        ];

    return Object.freeze({
        toothKey: anatomy.toothKey,
        geometryRef: anatomy.surfaceMap.geometryRef,
        model: anatomy.surfaceMap.model,
        family: isPosterior ? anatomy.toothType : (isCanine ? 'canine' : 'incisor'),
        surfaces: Object.freeze(surfaces),
    });
};

const surfaceGeometryEntries = Object.values(DENTAL_ANATOMY_REGISTRY).map((anatomy) => {
    const geometry = createSurfaceGeometry(anatomy);
    return [geometry.geometryRef, geometry];
});

export const SURFACE_GEOMETRY_REGISTRY = Object.freeze(Object.fromEntries(surfaceGeometryEntries));

export const getSurfaceGeometry = (toothKey) => {
    const anatomy = getDentalAnatomy(toothKey);
    if (!anatomy) return null;
    return SURFACE_GEOMETRY_REGISTRY[anatomy.surfaceMap.geometryRef] ?? null;
};
