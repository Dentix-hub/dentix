import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalWorkspaceStatusBanner from './ClinicalWorkspaceStatusBanner';
import { formatClinicalWarning, KNOWN_CLINICAL_WARNING_CODES } from '../utils/clinicalWarningFormatter';
import { useAuthStore } from '@/store/auth.store';
import arTranslations from '@/locales/ar/translation.json';
import enTranslations from '@/locales/en/translation.json';
import { flattenTranslations } from '../../../../scripts/extract-i18n-keys.mjs';

const mockT = (key, fallback, options = {}) => {
    if (typeof fallback === 'object' && fallback !== null && !options) {
        options = fallback;
        fallback = undefined;
    }
    const flatAr = flattenTranslations(arTranslations);
    let tmpl = flatAr[key] || fallback || key;
    if (typeof tmpl === 'string' && options) {
        for (const [k, v] of Object.entries(options)) {
            tmpl = tmpl.replace(new RegExp(`{{${k}}}`, 'g'), v);
        }
    }
    return tmpl;
};

describe('Clinical Workspace Warnings & Status Chips (D4 / A5)', () => {
    it('component test: visible text contains Arabic letters and NOT the raw code; raw code only in collapsed details', () => {
        useAuthStore.setState({ user: { id: 1, role: 'admin' } });

        const sampleChart = {
            coverage: { teeth: 'COMPLETE' },
            isFallback: false,
            warnings: [
                {
                    code: 'UNKNOWN_PROCEDURE_CODE',
                    message: "Unknown legacy procedure: 'special_scaling'. Exact allowlist match required.",
                    raw_value: 'special_scaling',
                },
            ],
            isEmpty: false,
        };

        render(
            <ClinicalWorkspaceStatusBanner adaptedChart={sampleChart} t={mockT} />
        );

        // Warning banner container is present
        const warningBox = screen.getByTestId('clinical-workspace-warnings');
        expect(warningBox).toBeInTheDocument();

        // Friendly text is visible and contains Arabic
        const friendlyText = screen.getByTestId('clinical-warning-friendly-0');
        expect(friendlyText).toBeInTheDocument();
        expect(/[\u0600-\u06FF]/.test(friendlyText.textContent)).toBe(true);
        expect(friendlyText.textContent).not.toContain('UNKNOWN_PROCEDURE_CODE');

        // Collapsed details element exists and contains technical code
        const details = screen.getByTestId('clinical-workspace-technical-details');
        expect(details).toBeInTheDocument();
        expect(details.textContent).toContain('UNKNOWN_PROCEDURE_CODE');
    });

    it('contract test: every backend warning code has a translation in ar and en; unknown codes render generic Arabic', () => {
        const flatAr = flattenTranslations(arTranslations);
        const flatEn = flattenTranslations(enTranslations);

        expect(KNOWN_CLINICAL_WARNING_CODES.length).toBeGreaterThanOrEqual(25);

        for (const code of KNOWN_CLINICAL_WARNING_CODES) {
            const arKey = `clinical.warning_messages.${code}`;
            expect(flatAr[arKey], `AR message for ${code} must exist`).toBeDefined();
            expect(flatEn[arKey], `EN message for ${code} must exist`).toBeDefined();
            expect(/[\u0600-\u06FF]/.test(flatAr[arKey]), `AR message for ${code} must contain Arabic`).toBe(true);
        }

        // Unknown/future code renders generic Arabic sentence, never raw code as main text
        const fallbackWarning = formatClinicalWarning({ code: 'FUTURE_EXPERIMENTAL_CODE_XYZ' }, mockT);
        expect(fallbackWarning.friendlyMessage).not.toContain('FUTURE_EXPERIMENTAL_CODE_XYZ');
        expect(/[\u0600-\u06FF]/.test(fallbackWarning.friendlyMessage)).toBe(true);
    });
});
