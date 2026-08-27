export const KNOWN_PLAN_FEATURES = [
    { key: 'ai_insights', label_ar: 'تحليلات ومساعد الذكاء الاصطناعي', label_en: 'AI Insights & Assistant' },
    { key: 'multi_branch', label_ar: 'إدارة الفروع المتعددة', label_en: 'Multi-Branch Management' },
    { key: 'export_reports', label_ar: 'تصدير التقارير المالية والطبية', label_en: 'Advanced Reports & Export' },
    { key: 'patient_portal', label_ar: 'بوابة المريض الإلكترونية', label_en: 'Patient Portal' },
    { key: 'telehealth', label_ar: 'الاستشارات الطبية عن بعد', label_en: 'Telehealth Consultations' },
    { key: 'custom_branding', label_ar: 'هوية مخصصة ودومين خاص', label_en: 'Custom Branding & Domain' },
];

export function parseFeatures(raw) {
    if (!raw) return { keys: [], custom: '' };
    if (typeof raw === 'object') {
        if (Array.isArray(raw)) {
            const known = raw.filter(k => KNOWN_PLAN_FEATURES.some(f => f.key === k));
            const customItems = raw.filter(k => !KNOWN_PLAN_FEATURES.some(f => f.key === k));
            return { keys: known, custom: customItems.join(', ') };
        }
        const known = Object.keys(raw).filter(k => raw[k] && KNOWN_PLAN_FEATURES.some(f => f.key === k));
        const customItems = Object.keys(raw).filter(k => raw[k] && !KNOWN_PLAN_FEATURES.some(f => f.key === k));
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
                const keys = Object.keys(parsed).filter(k => parsed[k] && KNOWN_PLAN_FEATURES.some(f => f.key === k));
                const customItems = Object.keys(parsed).filter(k => parsed[k] && !KNOWN_PLAN_FEATURES.some(f => f.key === k));
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

export function serializeFeatures(keys = [], customText = '') {
    const list = [...new Set(keys)];
    if (customText && customText.trim()) {
        const customItems = customText.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
        list.push(...customItems);
    }
    return JSON.stringify(list);
}
