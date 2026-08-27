/**
 * DENTIX Canonical UI Formatters
 * Provides standardized locale-aware formatting for currency, percentages, numbers, dates, roles, and statuses.
 */

export function formatCurrency(amount, currency = 'USD', language = 'ar') {
    if (amount === null || amount === undefined || isNaN(Number(amount))) {
        return '—';
    }
    const num = Number(amount);
    try {
        const locale = language === 'ar' ? 'ar-EG' : 'en-US';
        return `${num.toLocaleString(locale, { maximumFractionDigits: 2, minimumFractionDigits: 0 })} ${currency}`;
    } catch {
        return `${num.toFixed(2)} ${currency}`;
    }
}

export function formatNumber(value, language = 'ar') {
    if (value === null || value === undefined || isNaN(Number(value))) {
        return '—';
    }
    const num = Number(value);
    const locale = language === 'ar' ? 'ar-EG' : 'en-US';
    return num.toLocaleString(locale);
}

export function formatPercent(value, language = 'ar', decimals = 1) {
    if (value === null || value === undefined || isNaN(Number(value))) {
        return '—';
    }
    const num = Number(value);
    const locale = language === 'ar' ? 'ar-EG' : 'en-US';
    return `${num.toLocaleString(locale, { maximumFractionDigits: decimals, minimumFractionDigits: 0 })}%`;
}

export function formatDateTime(dateValue, language = 'ar', options = {}) {
    if (!dateValue) return '—';
    try {
        const d = dateValue instanceof Date ? dateValue : new Date(dateValue);
        if (isNaN(d.getTime())) return '—';
        const locale = language === 'ar' ? 'ar-SA' : 'en-US';
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            ...options,
        };
        return d.toLocaleDateString(locale, defaultOptions);
    } catch {
        return String(dateValue);
    }
}

export function formatDurationDays(days, language = 'ar') {
    if (days === null || days === undefined) return '∞';
    const num = Number(days);
    if (isNaN(num)) return '—';
    if (language === 'ar') {
        return `${num} يوم`;
    }
    return `${num} ${num === 1 ? 'day' : 'days'}`;
}

export function formatRole(role, t) {
    const norm = String(role || '').toLowerCase();
    const map = {
        super_admin: t ? t('roles.super_admin', 'مدير النظام العام') : 'مدير النظام العام',
        admin: t ? t('roles.admin', 'مدير عيادة') : 'مدير عيادة',
        doctor: t ? t('roles.doctor', 'طبيب') : 'طبيب',
        receptionist: t ? t('roles.receptionist', 'موظف استقبال') : 'موظف استقبال',
        accountant: t ? t('roles.accountant', 'محاسب') : 'محاسب',
        nurse: t ? t('roles.nurse', 'ممرض') : 'ممرض',
    };
    return map[norm] || role || '—';
}

export function formatStatus(status, t) {
    const norm = String(status || '').toLowerCase();
    const map = {
        active: t ? t('status.active', 'نشط') : 'نشط',
        inactive: t ? t('status.inactive', 'غير نشط') : 'غير نشط',
        expired: t ? t('status.expired', 'منتهي') : 'منتهي',
        archived: t ? t('status.archived', 'مؤرشف') : 'مؤرشف',
        success: t ? t('status.success', 'ناجح') : 'ناجح',
        failed: t ? t('status.failed', 'فاشل') : 'فاشل',
        pending: t ? t('status.pending', 'قيد الانتظار') : 'قيد الانتظار',
        running: t ? t('status.running', 'قيد التشغيل') : 'قيد التشغيل',
    };
    return map[norm] || status || '—';
}
