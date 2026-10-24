import { describe, expect, it } from 'vitest';

import i18n from './i18n';

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
});
