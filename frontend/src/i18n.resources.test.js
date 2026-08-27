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
});
