import anatomyReference from './assets/approved-tooth-anatomy-reference.png';
import procedureReference from './assets/procedure-effects-approval-v1.png';

export const APPROVED_ARTWORK = Object.freeze({
    anatomy: Object.freeze({ src: anatomyReference, width: 1400, height: 752 }),
    procedures: Object.freeze({ src: procedureReference, width: 1536, height: 1024 }),
});

const UNIVERSAL_TO_FDI = Object.freeze({
    1: 18, 2: 17, 3: 16, 4: 15, 5: 14, 6: 13, 7: 12, 8: 11,
    9: 21, 10: 22, 11: 23, 12: 24, 13: 25, 14: 26, 15: 27, 16: 28,
    17: 38, 18: 37, 19: 36, 20: 35, 21: 34, 22: 33, 23: 32, 24: 31,
    25: 41, 26: 42, 27: 43, 28: 44, 29: 45, 30: 46, 31: 47, 32: 48,
});

const UPPER_CROPS = [
    [128, 128, 94, 164], [222, 128, 88, 164], [310, 128, 87, 164], [397, 128, 79, 164],
    [476, 128, 62, 164], [538, 128, 60, 164], [598, 128, 58, 164], [656, 128, 58, 164],
    [714, 128, 58, 164], [772, 128, 57, 164], [829, 128, 60, 164], [889, 128, 61, 164],
    [950, 128, 70, 164], [1020, 128, 85, 164], [1105, 128, 95, 164], [1200, 128, 98, 164],
];

const LOWER_CROPS = [
    [1200, 378, 98, 146], [1105, 378, 95, 146], [1020, 378, 85, 146], [950, 378, 70, 146],
    [889, 378, 61, 146], [829, 378, 60, 146], [772, 378, 57, 146], [714, 378, 58, 146],
    [656, 378, 58, 146], [598, 378, 58, 146], [538, 378, 60, 146], [476, 378, 62, 146],
    [397, 378, 79, 146], [310, 378, 87, 146], [222, 378, 88, 146], [128, 378, 94, 146],
];

const toothSprites = {};
UPPER_CROPS.forEach((crop, index) => {
    const universal = index + 1;
    toothSprites[UNIVERSAL_TO_FDI[universal]] = Object.freeze({ crop, universal, arch: 'maxillary' });
});
LOWER_CROPS.forEach((crop, index) => {
    const universal = index + 17;
    toothSprites[UNIVERSAL_TO_FDI[universal]] = Object.freeze({ crop, universal, arch: 'mandibular' });
});

export const APPROVED_TOOTH_SPRITES = Object.freeze(toothSprites);

export const APPROVED_PROCEDURE_SPRITES = Object.freeze({
    caries: Object.freeze({ crop: [145, 0, 255, 260], color: '#c43a35' }),
    composite: Object.freeze({ crop: [642, 0, 260, 260], color: '#2f6fd1' }),
    amalgam: Object.freeze({ crop: [1137, 0, 260, 260], color: '#68737d' }),
    rct: Object.freeze({ crop: [140, 316, 270, 270], color: '#7b4fb4' }),
    crown: Object.freeze({ crop: [638, 316, 270, 270], color: '#c78b13' }),
    implant: Object.freeze({ crop: [1135, 316, 270, 270], color: '#239796' }),
    bridge: Object.freeze({ crop: [70, 640, 440, 270], color: '#b85e08' }),
    missing: Object.freeze({ crop: [638, 640, 270, 270], color: '#687585' }),
    planned: Object.freeze({ crop: [1134, 640, 270, 270], color: '#f08a16' }),
});

export const ADULT_FDI_ROWS = Object.freeze({
    maxillary: Object.freeze([18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]),
    mandibular: Object.freeze([48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]),
});
