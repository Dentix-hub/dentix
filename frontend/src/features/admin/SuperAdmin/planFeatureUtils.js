export const KNOWN_PLAN_FEATURES = [
    // Verified Sellable Capabilities
    {
        key: 'clinical',
        label_ar: 'السجلات الطبية والمواعيد',
        label_en: 'Clinical Records & Appointments',
        isSellable: true,
    },
    {
        key: 'billing',
        label_ar: 'الفواتير والمدفوعات والمحاسبة',
        label_en: 'Billing & Accounting',
        isSellable: true,
    },
    {
        key: 'laboratories',
        label_ar: 'إدارة المعامل',
        label_en: 'Laboratory Management',
        isSellable: true,
    },
    {
        key: 'inventory',
        label_ar: 'المخزون والمواد الطبية',
        label_en: 'Inventory & Materials',
        isSellable: true,
    },
    {
        key: 'export_reports',
        label_ar: 'تصدير التقارير المالية والطبية',
        label_en: 'Advanced Reports & Export',
        isSellable: true,
    },
    {
        key: 'ai_insights',
        label_ar: 'تحليلات ومساعد الذكاء الاصطناعي',
        label_en: 'AI Insights & Assistant',
        isSellable: true,
    },
    {
        key: 'tenant_backups',
        label_ar: 'النسخ الاحتياطي وأرشفة بيانات العيادة',
        label_en: 'Clinic Backups & Archive',
        isSellable: true,
    },

    // Excluded / Non-Sellable Capabilities (marked clearly as unavailable)
    {
        key: 'multi_branch',
        label_ar: 'إدارة الفروع المتعددة',
        label_en: 'Multi-Branch Management',
        isSellable: false,
    },
    {
        key: 'patient_portal',
        label_ar: 'بوابة المريض الإلكترونية',
        label_en: 'Patient Portal',
        isSellable: false,
    },
    {
        key: 'telehealth',
        label_ar: 'الاستشارات الطبية عن بعد',
        label_en: 'Telehealth Consultations',
        isSellable: false,
    },
    {
        key: 'custom_branding',
        label_ar: 'هوية مخصصة ودومين خاص',
        label_en: 'Custom Branding & Domain',
        isSellable: false,
    },
];

export const REGISTRY_CAPABILITIES = KNOWN_PLAN_FEATURES;

export function parseFeatures(raw) {
    if (!raw) return { keys: [], custom: '' };
    if (typeof raw === 'object') {
        if (Array.isArray(raw)) {
            const known = raw.filter(k => KNOWN_PLAN_FEATURES.some(f => f.key === k));
            const customItems = raw.filter(k => !KNOWN_PLAN_FEATURES.some(f => f.key === k));
            return { keys: known, custom: customItems.join(', ') };
        }
        const known = Object.keys(raw).filter(k => raw[k] === true && KNOWN_PLAN_FEATURES.some(f => f.key === k));
        const customItems = Object.keys(raw).filter(k => raw[k] === true && !KNOWN_PLAN_FEATURES.some(f => f.key === k));
        return { keys: known, custom: customItems.join(', ') };
    }
    const str = String(raw).trim();
    if (str.startsWith('[') || str.startsWith('{')) {
        try {
            const parsed = JSON.parse(str);
            if (Array.isArray(parsed)) {
                const known = parsed.filter(k => KNOWN_PLAN_FEATURES.some(f => f.key === k));
                const customItems = parsed.filter(k => !KNOWN_PLAN_FEATURES.some(f => f.key === k));
                return { keys: known, custom: customItems.join(', ') };
            }
            if (typeof parsed === 'object' && parsed !== null) {
                const keys = Object.keys(parsed).filter(k => parsed[k] === true && KNOWN_PLAN_FEATURES.some(f => f.key === k));
                const customItems = Object.keys(parsed).filter(k => parsed[k] === true && !KNOWN_PLAN_FEATURES.some(f => f.key === k));
                return { keys, custom: customItems.join(', ') };
            }
        } catch {
            // fallback to text splitting
        }
    }
    const items = str.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
    const known = items.filter(k => KNOWN_PLAN_FEATURES.some(f => f.key === k));
    const custom = items.filter(k => !KNOWN_PLAN_FEATURES.some(f => f.key === k)).join(', ');
    return { keys: known, custom };
}

export function serializeFeatures(keys = [], customText = '', originalRaw = null) {
    const list = [...new Set(keys)];
    if (customText && customText.trim()) {
        const customItems = customText.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
        list.push(...customItems);
    }
    let original = originalRaw;
    if (typeof original === 'string') {
        try { original = JSON.parse(original); } catch { original = null; }
    }
    if (original && typeof original === 'object' && !Array.isArray(original)) {
        const policy = Object.fromEntries(Object.keys(original).map(key => [key, list.includes(key)]));
        for (const key of list) policy[key] = true;
        return JSON.stringify(policy);
    }
    return JSON.stringify(list);
}
