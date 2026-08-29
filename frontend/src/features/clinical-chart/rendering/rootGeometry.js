import { DENTAL_ANATOMY_REGISTRY, getDentalAnatomy } from '../domain/dentalAnatomyRegistry';

export const ROOT_STYLE_TOKENS = Object.freeze({
    fill: '#ffffff',
    stroke: '#94a3b8',
    strokeWidth: 1.5,
});

export const ROOT_VIEW_BOX = '0 0 50 48';

const round = (value) => Number(value.toFixed(2));

/**
 * Builds a smooth tapered root from a cervical span to a rounded apex.
 * All teeth use the same local coordinate system: cervical line at y=0 and
 * apex direction toward y=48. Maxillary roots are flipped only by the chart
 * renderer so the geometry and its hit/overlay anchors remain stable.
 */
const createTaperedRootPath = ({ neckLeft, neckRight, apexX, apexY, bend = 0 }) => {
    const neckWidth = neckRight - neckLeft;
    const leftMidX = apexX - (neckWidth * 0.28) + bend;
    const rightMidX = apexX + (neckWidth * 0.28) + bend;

    return [
        `M${round(neckLeft)},0`,
        `C${round(neckLeft + (neckWidth * 0.08))},${round(apexY * 0.24)}`,
        `${round(leftMidX)},${round(apexY * 0.72)}`,
        `${round(apexX - 1.15)},${round(apexY - 1.8)}`,
        `Q${round(apexX)},${round(apexY + 0.7)}`,
        `${round(apexX + 1.15)},${round(apexY - 1.8)}`,
        `C${round(rightMidX)},${round(apexY * 0.72)}`,
        `${round(neckRight - (neckWidth * 0.08))},${round(apexY * 0.24)}`,
        `${round(neckRight)},0`,
        'Z',
    ].join(' ');
};

const mirrorX = (x) => 50 - x;

const mirrorRootSpec = (spec) => ({
    ...spec,
    neckLeft: mirrorX(spec.neckRight),
    neckRight: mirrorX(spec.neckLeft),
    apexX: mirrorX(spec.apexX),
    bend: -(spec.bend ?? 0),
});

const SINGLE_ROOT_PROFILE = Object.freeze({
    incisor: Object.freeze({
        1: Object.freeze({ neckLeft: 17, neckRight: 33, apexX: 24.4, apexY: 41.5, bend: -0.2 }),
        2: Object.freeze({ neckLeft: 18, neckRight: 32, apexX: 25.8, apexY: 39, bend: 0.45 }),
    }),
    canine: Object.freeze({
        3: Object.freeze({ neckLeft: 16, neckRight: 34, apexX: 26.2, apexY: 46, bend: 0.55 }),
    }),
    premolar: Object.freeze({
        4: Object.freeze({ neckLeft: 15.5, neckRight: 34.5, apexX: 24.1, apexY: 42.5, bend: -0.25 }),
        5: Object.freeze({ neckLeft: 15.5, neckRight: 34.5, apexX: 25.7, apexY: 40.5, bend: 0.35 }),
    }),
});

const PRIMARY_SINGLE_ROOT_PROFILE = Object.freeze({
    1: Object.freeze({ neckLeft: 18.5, neckRight: 31.5, apexX: 24.6, apexY: 34.5, bend: -0.15 }),
    2: Object.freeze({ neckLeft: 19, neckRight: 31, apexX: 25.5, apexY: 33, bend: 0.25 }),
    3: Object.freeze({ neckLeft: 17.5, neckRight: 32.5, apexX: 26, apexY: 39.5, bend: 0.45 }),
});

const MAXILLARY_PREMOLAR_ROOTS = Object.freeze({
    buccal: Object.freeze({ neckLeft: 13.5, neckRight: 27, apexX: 16.5, apexY: 40.5, bend: -0.5 }),
    palatal: Object.freeze({ neckLeft: 23, neckRight: 36.5, apexX: 33.2, apexY: 43.5, bend: 0.4 }),
});

const PERMANENT_MAXILLARY_MOLAR_ROOTS = Object.freeze({
    mesiobuccal: Object.freeze({ neckLeft: 8.5, neckRight: 23.5, apexX: 7.2, apexY: 37.5, bend: -0.8 }),
    distobuccal: Object.freeze({ neckLeft: 26.5, neckRight: 41.5, apexX: 43, apexY: 35.5, bend: 0.8 }),
    palatal: Object.freeze({ neckLeft: 18.5, neckRight: 31.5, apexX: 25.7, apexY: 46, bend: 0.25 }),
});

const PERMANENT_MANDIBULAR_MOLAR_ROOTS = Object.freeze({
    mesial: Object.freeze({ neckLeft: 9.5, neckRight: 26, apexX: 8, apexY: 43, bend: -0.8 }),
    distal: Object.freeze({ neckLeft: 24, neckRight: 40.5, apexX: 42, apexY: 41, bend: 0.75 }),
});

const PRIMARY_MAXILLARY_MOLAR_ROOTS = Object.freeze({
    mesiobuccal: Object.freeze({ neckLeft: 9, neckRight: 21.5, apexX: 3.5, apexY: 38.5, bend: -1.15 }),
    distobuccal: Object.freeze({ neckLeft: 28.5, neckRight: 41, apexX: 46.5, apexY: 37, bend: 1.15 }),
    palatal: Object.freeze({ neckLeft: 19.5, neckRight: 30.5, apexX: 25.5, apexY: 44, bend: 0.2 }),
});

const PRIMARY_MANDIBULAR_MOLAR_ROOTS = Object.freeze({
    mesial: Object.freeze({ neckLeft: 10, neckRight: 24, apexX: 4.5, apexY: 42, bend: -1.1 }),
    distal: Object.freeze({ neckLeft: 26, neckRight: 40, apexX: 45.5, apexY: 42, bend: 1.1 }),
});

const getMolarLengthAdjustment = (position) => ({ 4: 0, 5: -1, 6: 0, 7: -2, 8: -4 }[position] ?? 0);

const resolveBaseRootSpec = (anatomy, rootId) => {
    const position = Number(anatomy.toothKey[1]);

    if (anatomy.dentition === 'primary') {
        if (rootId === 'single') return PRIMARY_SINGLE_ROOT_PROFILE[position];
        if (anatomy.arch === 'maxillary') return PRIMARY_MAXILLARY_MOLAR_ROOTS[rootId];
        return PRIMARY_MANDIBULAR_MOLAR_ROOTS[rootId];
    }

    if (rootId === 'single') return SINGLE_ROOT_PROFILE[anatomy.toothType][position];
    if (anatomy.toothType === 'premolar') return MAXILLARY_PREMOLAR_ROOTS[rootId];
    if (anatomy.arch === 'maxillary') return PERMANENT_MAXILLARY_MOLAR_ROOTS[rootId];
    return PERMANENT_MANDIBULAR_MOLAR_ROOTS[rootId];
};

const resolveToothRootSpec = (anatomy, rootId) => {
    const position = Number(anatomy.toothKey[1]);
    const baseSpec = resolveBaseRootSpec(anatomy, rootId);
    const lengthAdjustment = anatomy.toothType === 'molar' ? getMolarLengthAdjustment(position) : 0;
    const adjustedSpec = { ...baseSpec, apexY: baseSpec.apexY + lengthAdjustment };

    return anatomy.side === 'left' ? mirrorRootSpec(adjustedSpec) : adjustedSpec;
};

const rootEntries = Object.values(DENTAL_ANATOMY_REGISTRY).flatMap((anatomy) =>
    anatomy.rootOutlineRefs.map(({ rootId, outlineRef }) => [
        outlineRef,
        (() => {
            const spec = resolveToothRootSpec(anatomy, rootId);
            return Object.freeze({
                outlineRef,
                toothKey: anatomy.toothKey,
                rootId,
                toothType: anatomy.toothType,
                dentition: anatomy.dentition,
                arch: anatomy.arch,
                side: anatomy.side,
                variant: 'canonical-schematic',
                viewBox: ROOT_VIEW_BOX,
                path: createTaperedRootPath(spec),
                cervicalAnchors: Object.freeze({
                    left: Object.freeze({ x: spec.neckLeft, y: 0 }),
                    right: Object.freeze({ x: spec.neckRight, y: 0 }),
                }),
                apexAnchor: Object.freeze({ x: spec.apexX, y: spec.apexY }),
                style: ROOT_STYLE_TOKENS,
            });
        })(),
    ]),
);

export const ROOT_OUTLINE_REGISTRY = Object.freeze(Object.fromEntries(rootEntries));

export const getRootGeometry = (toothKey) => {
    const anatomy = getDentalAnatomy(toothKey);
    if (!anatomy) return null;
    return Object.freeze(anatomy.rootOutlineRefs.map(({ outlineRef }) => ROOT_OUTLINE_REGISTRY[outlineRef]));
};
