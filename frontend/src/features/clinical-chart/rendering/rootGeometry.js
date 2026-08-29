import { DENTAL_ANATOMY_REGISTRY, getDentalAnatomy } from '../domain/dentalAnatomyRegistry';

export const ROOT_STYLE_TOKENS = Object.freeze({
    fill: '#f8fafc',
    stroke: '#94a3b8',
    strokeWidth: 1.5,
});

const SINGLE_ROOT_PATHS = Object.freeze({
    maxillary: 'M36,92 C36,67 38,22 50,3 C62,22 64,67 64,92 Z',
    mandibular: 'M36,52 C36,83 39,137 50,157 C61,137 64,83 64,52 Z',
});

const ROOT_PATH_BY_ID = Object.freeze({
    maxillary: Object.freeze({
        buccal: 'M27,92 C24,64 19,22 36,5 C45,30 47,63 46,92 Z',
        palatal: 'M54,92 C53,63 56,25 70,8 C78,36 72,69 70,92 Z',
        mesiobuccal: 'M18,92 C17,62 10,23 27,7 C38,33 40,66 40,92 Z',
        distobuccal: 'M60,92 C62,63 70,26 83,11 C88,39 79,72 74,92 Z',
    }),
    mandibular: Object.freeze({
        mesial: 'M20,52 C17,84 15,129 28,154 C41,128 43,86 42,52 Z',
        distal: 'M58,52 C57,86 60,130 72,154 C84,129 82,84 78,52 Z',
    }),
});

const PRIMARY_ROOT_PATH_BY_ID = Object.freeze({
    maxillary: Object.freeze({
        single: 'M38,91 C37,65 40,29 50,12 C60,29 63,65 62,91 Z',
        mesiobuccal: 'M19,91 C15,63 8,31 22,17 C35,39 38,67 39,91 Z',
        distobuccal: 'M61,91 C63,65 72,34 84,20 C88,48 78,73 74,91 Z',
        palatal: 'M42,91 C40,58 43,22 50,9 C59,28 62,62 58,91 Z',
    }),
    mandibular: Object.freeze({
        single: 'M38,52 C38,79 41,124 50,143 C59,124 62,79 62,52 Z',
        mesial: 'M21,52 C16,82 13,118 25,143 C39,119 42,84 42,52 Z',
        distal: 'M58,52 C58,84 62,119 75,143 C87,116 83,80 78,52 Z',
    }),
});

const resolveRootPath = (anatomy, rootId) => {
    if (anatomy.dentition === 'primary') {
        return PRIMARY_ROOT_PATH_BY_ID[anatomy.arch][rootId];
    }
    if (rootId === 'single') return SINGLE_ROOT_PATHS[anatomy.arch];
    return ROOT_PATH_BY_ID[anatomy.arch][rootId];
};

const rootEntries = Object.values(DENTAL_ANATOMY_REGISTRY).flatMap((anatomy) =>
    anatomy.rootOutlineRefs.map(({ rootId, outlineRef }) => [
        outlineRef,
        Object.freeze({
            outlineRef,
            rootId,
            toothType: anatomy.toothType,
            dentition: anatomy.dentition,
            arch: anatomy.arch,
            viewBox: '0 0 100 160',
            path: resolveRootPath(anatomy, rootId),
            style: ROOT_STYLE_TOKENS,
        }),
    ]),
);

export const ROOT_OUTLINE_REGISTRY = Object.freeze(Object.fromEntries(rootEntries));

export const getRootGeometry = (toothKey) => {
    const anatomy = getDentalAnatomy(toothKey);
    if (!anatomy) return null;
    return Object.freeze(anatomy.rootOutlineRefs.map(({ outlineRef }) => ROOT_OUTLINE_REGISTRY[outlineRef]));
};

