import { useTenantStore } from '@/store/tenant.store';
import { DEFAULT_TENANT_TIMEZONE, getDateInTimeZone } from '@/utils/dateTime';

/**
 * Finance date range presets.
 *
 * A Finance "day" is a tenant business day, never the browser's local day.
 * Calendar arithmetic is performed in UTC only after resolving the tenant-local
 * YYYY-MM-DD key, so browser timezone/DST cannot shift the selected dates.
 */

const formatCalendarDate = (date) => {
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const calendarDateFromKey = (key) => {
    const [year, month, day] = key.split('-').map(Number);
    return new Date(Date.UTC(year, month - 1, day));
};

const resolveFinanceTimeZone = (override) => (
    override
    || useTenantStore.getState().tenant?.timezone
    || DEFAULT_TENANT_TIMEZONE
);

export const DATE_PRESETS = [
    { id: 'today', labelEn: 'Today', labelAr: 'اليوم' },
    { id: 'yesterday', labelEn: 'Yesterday', labelAr: 'أمس' },
    { id: 'this_week', labelEn: 'This week', labelAr: 'هذا الأسبوع' },
    { id: 'this_month', labelEn: 'This month', labelAr: 'هذا الشهر' },
    { id: 'last_month', labelEn: 'Last month', labelAr: 'الشهر الماضي' },
    { id: 'custom', labelEn: 'Custom', labelAr: 'مخصص' },
];

/**
 * Resolve a preset from the tenant timezone already loaded in TenantStore.
 * `timeZone` and `now` remain injectable for deterministic boundary tests.
 */
export const getPresetDates = (presetId, { timeZone, now = new Date() } = {}) => {
    const tenantTimeZone = resolveFinanceTimeZone(timeZone);
    const businessTodayKey = getDateInTimeZone(tenantTimeZone, now);
    const today = calendarDateFromKey(businessTodayKey);

    switch (presetId) {
        case 'today':
            return {
                from: formatCalendarDate(today),
                to: formatCalendarDate(today),
            };
        case 'yesterday': {
            const yesterday = new Date(today);
            yesterday.setUTCDate(today.getUTCDate() - 1);
            return {
                from: formatCalendarDate(yesterday),
                to: formatCalendarDate(yesterday),
            };
        }
        case 'this_week': {
            // Saturday is the DENTIX/MENA start of week.
            const dayOfWeek = today.getUTCDay();
            const startOfWeek = new Date(today);
            const diff = (dayOfWeek + 1) % 7;
            startOfWeek.setUTCDate(today.getUTCDate() - diff);
            return {
                from: formatCalendarDate(startOfWeek),
                to: formatCalendarDate(today),
            };
        }
        case 'this_month': {
            const startOfMonth = new Date(Date.UTC(
                today.getUTCFullYear(),
                today.getUTCMonth(),
                1,
            ));
            return {
                from: formatCalendarDate(startOfMonth),
                to: formatCalendarDate(today),
            };
        }
        case 'last_month': {
            const startOfLastMonth = new Date(Date.UTC(
                today.getUTCFullYear(),
                today.getUTCMonth() - 1,
                1,
            ));
            const endOfLastMonth = new Date(Date.UTC(
                today.getUTCFullYear(),
                today.getUTCMonth(),
                0,
            ));
            return {
                from: formatCalendarDate(startOfLastMonth),
                to: formatCalendarDate(endOfLastMonth),
            };
        }
        default:
            return {
                from: formatCalendarDate(new Date(Date.UTC(
                    today.getUTCFullYear(),
                    today.getUTCMonth(),
                    1,
                ))),
                to: formatCalendarDate(today),
            };
    }
};

export const formatRangeLabel = (from, to, locale = 'ar') => {
    if (!from || !to) return '';
    try {
        // Render date-only values in UTC so the viewer's browser timezone cannot
        // move a displayed calendar day backward or forward.
        const fromDate = calendarDateFromKey(from);
        const toDate = calendarDateFromKey(to);
        const options = { month: 'short', day: 'numeric', timeZone: 'UTC' };
        const displayLocale = locale === 'ar' ? 'ar-EG' : 'en-US';
        const fromStr = fromDate.toLocaleDateString(displayLocale, options);
        const toStr = toDate.toLocaleDateString(displayLocale, options);

        if (from === to) {
            return fromStr;
        }
        return `${fromStr} – ${toStr}`;
    } catch {
        return `${from} – ${to}`;
    }
};
