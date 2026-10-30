import { describe, it, expect } from 'vitest';
import {
    INFORMATIONAL_CLINICAL_WARNING_CODES,
    isInformationalClinicalWarning,
    getRealClinicalWarnings,
    getInformationalClinicalWarnings,
} from './clinicalWarningFormatter';

describe('clinicalWarningFormatter helpers', () => {
    it('defines informational warning codes accurately', () => {
        expect(INFORMATIONAL_CLINICAL_WARNING_CODES).toEqual([
            'FALLBACK_DATA_ACTIVE',
            'LEGACY_WRITE_COMPATIBILITY_ACTIVE',
        ]);
    });

    it('identifies informational warnings by object or code string', () => {
        expect(isInformationalClinicalWarning({ code: 'FALLBACK_DATA_ACTIVE' })).toBe(true);
        expect(isInformationalClinicalWarning('LEGACY_WRITE_COMPATIBILITY_ACTIVE')).toBe(true);
        expect(isInformationalClinicalWarning({ code: 'UNKNOWN_PROCEDURE_CODE' })).toBe(false);
        expect(isInformationalClinicalWarning(null)).toBe(false);
        expect(isInformationalClinicalWarning(undefined)).toBe(false);
    });

    it('filters real warnings and guarantees any unknown future codes are real', () => {
        const warnings = [
            { code: 'FALLBACK_DATA_ACTIVE', message: 'Fallback' },
            { code: 'UNKNOWN_PROCEDURE_CODE', message: 'Unknown procedure' },
            { code: 'FUTURE_EXPERIMENTAL_CODE_XYZ', message: 'Future unknown issue' },
            { code: 'LEGACY_WRITE_COMPATIBILITY_ACTIVE', message: 'Compat active' },
        ];

        const real = getRealClinicalWarnings(warnings);
        expect(real).toHaveLength(2);
        expect(real.map((w) => w.code)).toEqual([
            'UNKNOWN_PROCEDURE_CODE',
            'FUTURE_EXPERIMENTAL_CODE_XYZ',
        ]);

        const info = getInformationalClinicalWarnings(warnings);
        expect(info).toHaveLength(2);
        expect(info.map((w) => w.code)).toEqual([
            'FALLBACK_DATA_ACTIVE',
            'LEGACY_WRITE_COMPATIBILITY_ACTIVE',
        ]);
    });

    it('handles empty or non-array inputs safely', () => {
        expect(getRealClinicalWarnings(null)).toEqual([]);
        expect(getRealClinicalWarnings(undefined)).toEqual([]);
        expect(getRealClinicalWarnings([])).toEqual([]);
        expect(getInformationalClinicalWarnings(null)).toEqual([]);
        expect(getInformationalClinicalWarnings(undefined)).toEqual([]);
        expect(getInformationalClinicalWarnings([])).toEqual([]);
    });
});
