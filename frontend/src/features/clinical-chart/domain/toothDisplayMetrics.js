import { DENTAL_ANATOMY_REGISTRY } from './dentalAnatomyRegistry';

const PERMANENT_ROOT_SCALE = Object.freeze({
    incisor: Object.freeze({
        1: Object.freeze({ x: 0.95, y: 0.92 }),
        2: Object.freeze({ x: 0.84, y: 0.82 }),
    }),
    canine: Object.freeze({ x: 0.96, y: 0.96 }),
    premolar: Object.freeze({ x: 0.94, y: 0.9 }),
    molar: Object.freeze({ x: 0.9, y: 0.84 }),
});

const PRIMARY_ROOT_SCALE = Object.freeze({
    incisor: Object.freeze({
        1: Object.freeze({ x: 0.92, y: 0.86 }),
        2: Object.freeze({ x: 0.84, y: 0.8 }),
    }),
    canine: Object.freeze({ x: 0.92, y: 0.88 }),
    molar: Object.freeze({ x: 0.88, y: 0.86 }),
});

const getRootScale = (anatomy, position) => {
    if (
        anatomy.dentition === 'permanent'
        && anatomy.arch === 'maxillary'
        && anatomy.toothType === 'incisor'
        && position === 1
    ) {
        return Object.freeze({ x: 0.97, y: 0.96 });
    }

    const scaleRegistry = anatomy.dentition === 'primary' ? PRIMARY_ROOT_SCALE : PERMANENT_ROOT_SCALE;
    const scale = scaleRegistry[anatomy.toothType];
    return anatomy.toothType === 'incisor' ? scale[position] : scale;
};

const createDisplayMetrics = (anatomy) => {
    const position = Number(anatomy.toothKey[1]);

    return Object.freeze({
        toothKey: anatomy.toothKey,
        rootScale: getRootScale(anatomy, position),
    });
};

export const TOOTH_DISPLAY_METRICS = Object.freeze(Object.fromEntries(
    Object.values(DENTAL_ANATOMY_REGISTRY).map((anatomy) => [
        anatomy.toothKey,
        createDisplayMetrics(anatomy),
    ]),
));

export const getToothDisplayMetrics = (toothKey) => TOOTH_DISPLAY_METRICS[String(toothKey)] ?? null;
