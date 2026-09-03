import { describe, expect, it } from 'vitest';
import { toothToNumber, universalToPalmer } from '@/utils/toothUtils';
import {
    DENTAL_ANATOMY_REGISTRY,
    PERMANENT_TOOTH_KEYS,
} from '../domain/dentalAnatomyRegistry';
import {
    CHART_NOTATION_CONFIG,
    CHART_NOTATION_MODES,
    DEFAULT_CHART_NOTATION_MODE,
    getChartNotationConfig,
    resolveToothNotation,
} from '../domain/chartNotation';
import { fdiToUniversal } from '../rendering/crownGeometry';

const LEGACY_ADULT_SOURCE_IDS = Array.from({ length: 32 }, (_, index) => index + 1);
const LEGACY_PRIMARY_SOURCE_IDS = [...'ABCDEFGHIJKLMNOPQRST'];

describe('A11 chart notation semantics', () => {
    it('preserves the exact legacy Palmer display for all 52 source teeth', () => {
        expect(DEFAULT_CHART_NOTATION_MODE).toBe(CHART_NOTATION_MODES.PALMER);

        [
            ...LEGACY_ADULT_SOURCE_IDS.map((sourceToothId) => ({ sourceToothId, isPediatric: false })),
            ...LEGACY_PRIMARY_SOURCE_IDS.map((sourceToothId) => ({ sourceToothId, isPediatric: true })),
        ].forEach(({ sourceToothId, isPediatric }) => {
            const toothKey = String(toothToNumber(sourceToothId));
            expect(resolveToothNotation({ toothKey })).toEqual({
                toothKey,
                mode: CHART_NOTATION_MODES.PALMER,
                label: universalToPalmer(sourceToothId, isPediatric),
            });
        });
    });

    it.each([
        ['11', 'UR1', '11', '8'],
        ['28', 'UL8', '28', '16'],
        ['31', 'LL1', '31', '24'],
        ['48', 'LR8', '48', '32'],
        ['51', 'UR A', '51', 'E'],
        ['65', 'UL E', '65', 'J'],
        ['75', 'LL E', '75', 'K'],
        ['85', 'LR E', '85', 'T'],
    ])('keeps FDI %s identity stable across presentation modes', (
        toothKey,
        palmer,
        fdi,
        universal,
    ) => {
        const resolve = (notationMode) => resolveToothNotation({ toothKey, notationMode });

        expect(resolve(CHART_NOTATION_MODES.PALMER)).toMatchObject({ toothKey, label: palmer });
        expect(resolve(CHART_NOTATION_MODES.FDI)).toMatchObject({ toothKey, label: fdi });
        expect(resolve(CHART_NOTATION_MODES.UNIVERSAL)).toMatchObject({ toothKey, label: universal });
        expect(DENTAL_ANATOMY_REGISTRY[toothKey].toothKey).toBe(toothKey);
    });

    it('derives every permanent Universal label from canonical FDI identity', () => {
        PERMANENT_TOOTH_KEYS.forEach((toothKey) => {
            expect(resolveToothNotation({
                toothKey,
                notationMode: CHART_NOTATION_MODES.UNIVERSAL,
            }).label).toBe(String(fdiToUniversal(toothKey)));
        });
    });

    it('does not allow caller data to reinterpret permanent or primary identity', () => {
        expect(resolveToothNotation({
            toothKey: '11',
            sourceToothId: 1,
            notationMode: CHART_NOTATION_MODES.UNIVERSAL,
        })).toMatchObject({ toothKey: '11', label: '8' });
        expect(resolveToothNotation({
            toothKey: '51',
            sourceToothId: 'A',
            notationMode: CHART_NOTATION_MODES.UNIVERSAL,
        })).toMatchObject({ toothKey: '51', label: 'E' });
    });

    it('exposes frozen presentation configs and rejects semantic ambiguity', () => {
        expect(Object.isFrozen(CHART_NOTATION_CONFIG)).toBe(true);
        expect(getChartNotationConfig().displayName).toBe('Palmer Notation');
        ['iso-unknown', 'toString', 'constructor', null, 42].forEach((notationMode) => {
            expect(() => getChartNotationConfig(notationMode)).toThrow(TypeError);
        });
        expect(() => resolveToothNotation({ toothKey: '99' })).toThrow('Unknown tooth key: 99');
    });
});
