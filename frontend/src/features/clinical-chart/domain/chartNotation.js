import { toothToNumber, universalToPalmer } from '@/utils/toothUtils';
import { getDentalAnatomy } from './dentalAnatomyRegistry';

export const CHART_NOTATION_MODES = Object.freeze({
    PALMER: 'palmer',
    FDI: 'fdi',
    UNIVERSAL: 'universal',
});

export const DEFAULT_CHART_NOTATION_MODE = CHART_NOTATION_MODES.PALMER;

const UNIVERSAL_SOURCE_IDS = Object.freeze([
    ...Array.from({ length: 32 }, (_, index) => index + 1),
    ...'ABCDEFGHIJKLMNOPQRST',
]);
const UNIVERSAL_LABEL_BY_FDI = Object.freeze(Object.fromEntries(
    UNIVERSAL_SOURCE_IDS.map((sourceToothId) => [
        String(toothToNumber(sourceToothId)),
        sourceToothId,
    ]),
));

export const CHART_NOTATION_CONFIG = Object.freeze({
    [CHART_NOTATION_MODES.PALMER]: Object.freeze({
        mode: CHART_NOTATION_MODES.PALMER,
        displayName: 'Palmer Notation',
        formatLabel: ({ toothKey }) => {
            const sourceToothId = UNIVERSAL_LABEL_BY_FDI[toothKey];
            return universalToPalmer(sourceToothId, typeof sourceToothId === 'string');
        },
    }),
    [CHART_NOTATION_MODES.FDI]: Object.freeze({
        mode: CHART_NOTATION_MODES.FDI,
        displayName: 'FDI Notation',
        formatLabel: ({ toothKey }) => toothKey,
    }),
    [CHART_NOTATION_MODES.UNIVERSAL]: Object.freeze({
        mode: CHART_NOTATION_MODES.UNIVERSAL,
        displayName: 'Universal Notation',
        formatLabel: ({ toothKey }) => String(UNIVERSAL_LABEL_BY_FDI[toothKey]),
    }),
});

export const getChartNotationConfig = (notationMode = DEFAULT_CHART_NOTATION_MODE) => {
    if (typeof notationMode !== 'string'
        || !Object.hasOwn(CHART_NOTATION_CONFIG, notationMode)) {
        throw new TypeError(`notationMode must be one of: ${Object.values(CHART_NOTATION_MODES).join(', ')}`);
    }
    return CHART_NOTATION_CONFIG[notationMode];
};

/**
 * Resolves presentation-only notation without changing the canonical FDI tooth
 * identity used by anatomy, projection, visual rules, or interaction intents.
 */
export const resolveToothNotation = ({
    toothKey,
    notationMode = DEFAULT_CHART_NOTATION_MODE,
}) => {
    const anatomy = getDentalAnatomy(toothKey);
    if (!anatomy) {
        throw new RangeError(`Unknown tooth key: ${String(toothKey)}`);
    }
    const config = getChartNotationConfig(notationMode);

    return Object.freeze({
        toothKey: anatomy.toothKey,
        mode: config.mode,
        label: config.formatLabel({ toothKey: anatomy.toothKey }),
    });
};
