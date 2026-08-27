import { describe, it, expect } from 'vitest';
import {
    formatCurrency,
    formatNumber,
    formatPercent,
    formatDateTime,
    formatDurationDays,
    formatRole,
    formatStatus,
} from './formatters';

describe('Canonical UI Formatters MS-32', () => {
    it('formats currency gracefully across languages and handles null/undefined', () => {
        expect(formatCurrency(1500, 'USD', 'en')).toBe('1,500 USD');
        expect(formatCurrency(0, 'EGP', 'ar')).toContain('EGP');
        expect(formatCurrency(null)).toBe('—');
        expect(formatCurrency(undefined)).toBe('—');
        expect(formatCurrency('not_a_number')).toBe('—');
    });

    it('formats numbers and percentages accurately', () => {
        expect(formatNumber(12500, 'en')).toBe('12,500');
        expect(formatNumber(null)).toBe('—');

        expect(formatPercent(98.54, 'en', 1)).toBe('98.5%');
        expect(formatPercent(null)).toBe('—');
        expect(formatPercent(undefined)).toBe('—');
    });

    it('formats duration in days with language awareness and infinite fallback', () => {
        expect(formatDurationDays(30, 'ar')).toBe('30 يوم');
        expect(formatDurationDays(1, 'en')).toBe('1 day');
        expect(formatDurationDays(45, 'en')).toBe('45 days');
        expect(formatDurationDays(null)).toBe('∞');
    });

    it('formats dates safely without throwing on invalid input', () => {
        expect(formatDateTime(null)).toBe('—');
        expect(formatDateTime('invalid-date')).toBe('—');
        expect(formatDateTime(new Date('2026-08-26T12:00:00Z'), 'en')).toContain('2026');
    });

    it('formats canonical roles and statuses with translation boundary fallback', () => {
        const mockT = (k, fallback) => fallback || k;
        expect(formatRole('super_admin', mockT)).toBe('مدير النظام العام');
        expect(formatRole('doctor', mockT)).toBe('طبيب');
        expect(formatRole('unknown_role', mockT)).toBe('unknown_role');

        expect(formatStatus('active', mockT)).toBe('نشط');
        expect(formatStatus('expired', mockT)).toBe('منتهي');
        expect(formatStatus('archived', mockT)).toBe('مؤرشف');
    });
});
