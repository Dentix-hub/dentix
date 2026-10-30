import { describe, expect, it } from 'vitest';

import i18n from './i18n';
import { extractI18nKeys, flattenTranslations } from '../scripts/extract-i18n-keys.mjs';
import arTranslations from './locales/ar/translation.json';
import enTranslations from './locales/en/translation.json';
import allowlist from './locales/i18n-allowlist.json';
// Baseline exemptions for pre-existing keys in staging (1907061). This list MAY ONLY SHRINK over time, never grow.
import baselineExemptions from './locales/i18n-exemptions-baseline.json';

const expectedResources = {
    ar: {
        'sidebar.system_admin': 'مدير النظام',
        'super_admin.finance.subtitle': 'متابعة المدفوعات والاشتراكات والخطط والتقارير المالية',
        'super_admin.finance.tabs.payments': 'المدفوعات',
        'super_admin.finance.tabs.subscriptions': 'الاشتراكات',
        'super_admin.finance.tabs.plans': 'الخطط',
        'super_admin.finance.tabs.reports': 'التقارير',
        'super_admin.payments.record_button': 'تسجيل دفعة',
    },
    en: {
        'sidebar.system_admin': 'System Admin',
        'super_admin.finance.subtitle': 'Monitor payments, subscriptions, plans, and financial reports',
        'super_admin.finance.tabs.payments': 'Payments',
        'super_admin.finance.tabs.subscriptions': 'Subscriptions',
        'super_admin.finance.tabs.plans': 'Plans',
        'super_admin.finance.tabs.reports': 'Reports',
        'super_admin.payments.record_button': 'Record Payment',
    },
};

describe('i18n resource integrity', () => {
    it.each(Object.entries(expectedResources))('resolves required %s admin labels', (language, resources) => {
        for (const [key, expected] of Object.entries(resources)) {
            expect(i18n.getResource(language, 'translation', key)).toBe(expected);
        }
    });

    it('enforces ar and en key parity for care_session, dental_chart, and quick_treatment_sheet', () => {
        const sections = ['care_session', 'dental_chart', 'quick_treatment_sheet'];
        for (const section of sections) {
            const arSection = i18n.getResource('ar', 'translation', section);
            const enSection = i18n.getResource('en', 'translation', section);

            expect(arSection, `ar should have section "${section}"`).toBeDefined();
            expect(enSection, `en should have section "${section}"`).toBeDefined();

            const arKeys = Object.keys(arSection || {}).sort();
            const enKeys = Object.keys(enSection || {}).sort();

            expect(arKeys.length).toBeGreaterThan(0);
            expect(arKeys).toEqual(enKeys);
        }
    });

    it('enforces that all static t() calls in the codebase exist in ar and en', () => {
        const report = extractI18nKeys();
        expect(report.missingInBoth, 'Static keys missing in both AR and EN').toEqual([]);
        expect(report.missingInAr, 'Static keys missing in AR').toEqual([]);
        expect(report.missingInEn, 'Static keys missing in EN').toEqual([]);
    });

    it('enforces complete key set parity across ar and en translation files', () => {
        const report = extractI18nKeys();
        expect(report.enMissingInAr, 'Keys in EN translation missing in AR').toEqual([]);
        expect(report.arMissingInEn, 'Keys in AR translation missing in EN').toEqual([]);
        expect(report.arTotalKeys).toBe(report.enTotalKeys);
    });

    it('enforces that every ar value contains Arabic letters unless allowlisted or in baseline exemptions', () => {
        const flatAr = flattenTranslations(arTranslations);
        const hasArabic = /[\u0600-\u06FF]/;
        const permitted = new Set([...allowlist, ...baselineExemptions]);

        const violations = [];
        for (const [key, value] of Object.entries(flatAr)) {
            if (!permitted.has(key) && !hasArabic.test(String(value))) {
                violations.push({ key, value });
            }
        }
        expect(violations, 'AR translation values without Arabic letters must be translated or allowlisted').toEqual([]);
    });

    it('enforces that ar values equal to en values are explicitly allowlisted', () => {
        const flatAr = flattenTranslations(arTranslations);
        const flatEn = flattenTranslations(enTranslations);
        const permitted = new Set([...allowlist, ...baselineExemptions]);

        const identical = [];
        for (const [key, arVal] of Object.entries(flatAr)) {
            const enVal = flatEn[key];
            if (!permitted.has(key) && typeof arVal === 'string' && arVal.trim() !== '' && arVal.trim() === String(enVal).trim()) {
                identical.push({ key, arVal, enVal });
            }
        }
        expect(identical, 'AR values identical to EN values must be translated or allowlisted').toEqual([]);
    });
});
