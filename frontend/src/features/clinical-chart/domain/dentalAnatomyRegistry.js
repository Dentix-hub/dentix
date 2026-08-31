export const DENTITIONS = Object.freeze({
    PERMANENT: 'permanent',
    PRIMARY: 'primary',
});

export const TOOTH_TYPES = Object.freeze({
    INCISOR: 'incisor',
    CANINE: 'canine',
    PREMOLAR: 'premolar',
    MOLAR: 'molar',
});

const PERMANENT_QUADRANTS = Object.freeze([1, 2, 3, 4]);
const PRIMARY_QUADRANTS = Object.freeze([5, 6, 7, 8]);

export const PERMANENT_TOOTH_KEYS = Object.freeze(
    PERMANENT_QUADRANTS.flatMap((quadrant) =>
        Array.from({ length: 8 }, (_, index) => `${quadrant}${index + 1}`),
    ),
);

export const PRIMARY_TOOTH_KEYS = Object.freeze(
    PRIMARY_QUADRANTS.flatMap((quadrant) =>
        Array.from({ length: 5 }, (_, index) => `${quadrant}${index + 1}`),
    ),
);

const getToothType = (position, dentition) => {
    if (position <= 2) return TOOTH_TYPES.INCISOR;
    if (position === 3) return TOOTH_TYPES.CANINE;
    if (dentition === DENTITIONS.PERMANENT && position <= 5) return TOOTH_TYPES.PREMOLAR;
    return TOOTH_TYPES.MOLAR;
};

const getArch = (quadrant) => ([1, 2, 5, 6].includes(quadrant) ? 'maxillary' : 'mandibular');

const getSide = (quadrant) => ([1, 4, 5, 8].includes(quadrant) ? 'right' : 'left');

const getRootIds = ({ arch, dentition, position, toothType }) => {
    if (toothType === TOOTH_TYPES.MOLAR) {
        if (arch === 'maxillary') return ['mesiobuccal', 'distobuccal', 'palatal'];
        return ['mesial', 'distal'];
    }

    if (
        dentition === DENTITIONS.PERMANENT
        && arch === 'maxillary'
        && toothType === TOOTH_TYPES.PREMOLAR
        && position === 4
    ) {
        return ['buccal', 'palatal'];
    }

    return ['single'];
};

/**
 * @typedef {object} DentalAnatomyRecord
 * @property {string} toothKey Stable FDI tooth key.
 * @property {'permanent'|'primary'} dentition
 * @property {'incisor'|'canine'|'premolar'|'molar'} toothType
 * @property {'maxillary'|'mandibular'} arch
 * @property {'right'|'left'} side
 * @property {string} crownOutlineRef Reference resolved by the crown geometry adapter.
 * @property {{model: 'anterior'|'posterior', geometryRef: string}} surfaceMap
 * @property {number} rootCount
 * @property {ReadonlyArray<{rootId: string, outlineRef: string}>} rootOutlineRefs
 * @property {ReadonlyArray<{rootId: string, anchors: ReadonlyArray<object>}>} canalAnchorPlaceholders
 * @property {{x: number, y: number}} labelAnchor
 * @property {{center: object, crown: object, root: object}} overlayAnchors
 */

const createAnatomyRecord = (toothKey, dentition) => {
    const quadrant = Number(toothKey[0]);
    const position = Number(toothKey[1]);
    const toothType = getToothType(position, dentition);
    const arch = getArch(quadrant);
    const side = getSide(quadrant);
    const rootIds = getRootIds({ arch, dentition, position, toothType });
    const surfaceModel = [TOOTH_TYPES.INCISOR, TOOTH_TYPES.CANINE].includes(toothType)
        ? 'anterior'
        : 'posterior';
    const surfaceCodes = [
        'M',
        'D',
        surfaceModel === 'posterior' ? 'O' : 'I',
        'B',
        arch === 'maxillary' ? 'P' : 'L',
    ];

    return Object.freeze({
        toothKey,
        dentition,
        toothType,
        arch,
        side,
        crownOutlineRef: `crown:${dentition}:${arch}:${toothType}`,
        surfaceMap: Object.freeze({
            model: surfaceModel,
            geometryRef: `surfaces:${toothKey}`,
            surfaceCodes: Object.freeze(surfaceCodes),
        }),
        rootCount: rootIds.length,
        rootOutlineRefs: Object.freeze(rootIds.map((rootId) => Object.freeze({
            rootId,
            outlineRef: `root:${toothKey}:${rootId}`,
        }))),
        canalAnchorPlaceholders: Object.freeze(rootIds.map((rootId) => Object.freeze({
            rootId,
            anchors: Object.freeze([]),
        }))),
        labelAnchor: Object.freeze({ x: 50, y: arch === 'maxillary' ? 156 : 12 }),
        overlayAnchors: Object.freeze({
            center: Object.freeze({ x: 50, y: 80 }),
            crown: Object.freeze({ x: 50, y: arch === 'maxillary' ? 112 : 48 }),
            root: Object.freeze({ x: 50, y: arch === 'maxillary' ? 48 : 112 }),
        }),
    });
};

const permanentRecords = PERMANENT_TOOTH_KEYS.map((toothKey) => [
    toothKey,
    createAnatomyRecord(toothKey, DENTITIONS.PERMANENT),
]);

const primaryRecords = PRIMARY_TOOTH_KEYS.map((toothKey) => [
    toothKey,
    createAnatomyRecord(toothKey, DENTITIONS.PRIMARY),
]);

/** @type {Readonly<Record<string, DentalAnatomyRecord>>} */
export const DENTAL_ANATOMY_REGISTRY = Object.freeze(
    Object.fromEntries([...permanentRecords, ...primaryRecords]),
);

export const getDentalAnatomy = (toothKey) => DENTAL_ANATOMY_REGISTRY[String(toothKey)] ?? null;
