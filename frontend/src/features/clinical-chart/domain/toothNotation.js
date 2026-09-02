import { DENTAL_ANATOMY_REGISTRY } from './dentalAnatomyRegistry';
import { toothToNumber, universalToPalmer, fdiToPalmer } from '@/utils/toothUtils';

export const CHART_NOTATION_MODES = Object.freeze({
    PALMER: 'palmer',
    FDI: 'fdi',
    UNIVERSAL: 'universal',
});

export const NOTATION_MODE_LABELS = Object.freeze({
    [CHART_NOTATION_MODES.PALMER]: 'Palmer Notation',
    [CHART_NOTATION_MODES.FDI]: 'FDI World Dental Federation Notation',
    [CHART_NOTATION_MODES.UNIVERSAL]: 'Universal Numbering System',
});

const FDI_TO_UNIVERSAL = Object.freeze({
    // Upper Right (18 -> 1, 11 -> 8)
    '18': '1', '17': '2', '16': '3', '15': '4', '14': '5', '13': '6', '12': '7', '11': '8',
    // Upper Left (21 -> 9, 28 -> 16)
    '21': '9', '22': '10', '23': '11', '24': '12', '25': '13', '26': '14', '27': '15', '28': '16',
    // Lower Left (38 -> 17, 31 -> 24)
    '38': '17', '37': '18', '36': '19', '35': '20', '34': '21', '33': '22', '32': '23', '31': '24',
    // Lower Right (41 -> 25, 48 -> 32)
    '41': '25', '42': '26', '43': '27', '44': '28', '45': '29', '46': '30', '47': '31', '48': '32',
    // Primary Upper Right (55 -> A, 51 -> E)
    '55': 'A', '54': 'B', '53': 'C', '52': 'D', '51': 'E',
    // Primary Upper Left (61 -> F, 65 -> J)
    '61': 'F', '62': 'G', '63': 'H', '64': 'I', '65': 'J',
    // Primary Lower Left (75 -> K, 71 -> O)
    '75': 'K', '74': 'L', '73': 'M', '72': 'N', '71': 'O',
    // Primary Lower Right (81 -> P, 85 -> T)
    '81': 'P', '82': 'Q', '83': 'R', '84': 'S', '85': 'T',
});

/**
 * Converts an FDI tooth key to Universal notation (1-32 or A-T).
 *
 * @param {string|number} fdiKey
 * @returns {string}
 */
export const fdiToUniversal = (fdiKey) => (
    FDI_TO_UNIVERSAL[String(fdiKey)] ?? String(fdiKey)
);

/**
 * Formats a tooth label based on the requested notation mode (Palmer, FDI, Universal).
 * Accepts either an FDI key ('11', '46', '55') or a Universal identifier (8, 30, 'A').
 *
 * @param {string|number} toothId Universal or FDI identifier
 * @param {object} [options]
 * @param {'palmer'|'fdi'|'universal'} [options.notationMode='palmer']
 * @param {boolean} [options.isPediatric=false]
 * @returns {string}
 */
export const formatToothLabel = (toothId, { notationMode = CHART_NOTATION_MODES.PALMER, isPediatric = false } = {}) => {
    const rawKey = String(toothId);
    const isFdi = Boolean(DENTAL_ANATOMY_REGISTRY[rawKey]);
    const fdiNumber = isFdi ? Number(rawKey) : toothToNumber(toothId);
    const fdiKey = String(fdiNumber);

    switch (notationMode) {
        case CHART_NOTATION_MODES.FDI:
            return fdiKey;

        case CHART_NOTATION_MODES.UNIVERSAL:
            return FDI_TO_UNIVERSAL[fdiKey] ?? String(toothId);

        case CHART_NOTATION_MODES.PALMER:
        default:
            return fdiToPalmer(fdiNumber) || universalToPalmer(toothId, isPediatric) || fdiKey;
    }
};
