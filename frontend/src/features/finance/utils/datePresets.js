/**
 * Date range presets and utilities for DENTIX Finance V2.
 * Supports: today, yesterday, this_week, this_month, last_month, custom.
 */

const formatDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

export const DATE_PRESETS = [
    { id: 'today', labelEn: 'Today', labelAr: 'اليوم' },
    { id: 'yesterday', labelEn: 'Yesterday', labelAr: 'أمس' },
    { id: 'this_week', labelEn: 'This week', labelAr: 'هذا الأسبوع' },
    { id: 'this_month', labelEn: 'This month', labelAr: 'هذا الشهر' },
    { id: 'last_month', labelEn: 'Last month', labelAr: 'الشهر الماضي' },
    { id: 'custom', labelEn: 'Custom', labelAr: 'مخصص' },
];

export const getPresetDates = (presetId) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    switch (presetId) {
        case 'today':
            return {
                from: formatDate(today),
                to: formatDate(today),
            };
        case 'yesterday': {
            const yesterday = new Date(today);
            yesterday.setDate(today.getDate() - 1);
            return {
                from: formatDate(yesterday),
                to: formatDate(yesterday),
            };
        }
        case 'this_week': {
            // Saturday is start of week in Egypt/MENA, or Sunday in standard
            const dayOfWeek = today.getDay(); // 0: Sunday, 6: Saturday
            const startOfWeek = new Date(today);
            // Saturday as day 0 of week (if Saturday is 6, offset 0; Sunday is 0 -> offset 1)
            const diff = (dayOfWeek + 1) % 7;
            startOfWeek.setDate(today.getDate() - diff);
            return {
                from: formatDate(startOfWeek),
                to: formatDate(today),
            };
        }
        case 'this_month': {
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            return {
                from: formatDate(startOfMonth),
                to: formatDate(today),
            };
        }
        case 'last_month': {
            const startOfLastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
            return {
                from: formatDate(startOfLastMonth),
                to: formatDate(endOfLastMonth),
            };
        }
        default:
            return {
                from: formatDate(new Date(today.getFullYear(), today.getMonth(), 1)),
                to: formatDate(today),
            };
    }
};

export const formatRangeLabel = (from, to, locale = 'ar') => {
    if (!from || !to) return '';
    try {
        const fromDate = new Date(from);
        const toDate = new Date(to);

        const options = { month: 'short', day: 'numeric' };
        const fromStr = fromDate.toLocaleDateString(locale === 'ar' ? 'ar-EG' : 'en-US', options);
        const toStr = toDate.toLocaleDateString(locale === 'ar' ? 'ar-EG' : 'en-US', options);

        if (from === to) {
            return fromStr;
        }
        return `${fromStr} – ${toStr}`;
    } catch {
        return `${from} – ${to}`;
    }
};
