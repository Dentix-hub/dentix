import { describe, expect, it } from 'vitest';
import { getDateInTimeZone, selectAppointmentsForBusinessDate } from './dateTime';

describe('tenant business-date helpers', () => {
    it('uses the tenant timezone rather than UTC calendar date', () => {
        const instant = new Date('2026-08-16T21:30:00Z');
        expect(getDateInTimeZone('Africa/Cairo', instant)).toBe('2026-08-17');
        expect(getDateInTimeZone('UTC', instant)).toBe('2026-08-16');
    });

    it('supports different tenant timezones for the same instant', () => {
        const instant = new Date('2026-08-17T20:30:00Z');
        expect(getDateInTimeZone('Asia/Riyadh', instant)).toBe('2026-08-17');
        expect(getDateInTimeZone('Asia/Dubai', instant)).toBe('2026-08-18');
    });

    it('falls back safely when a bad stored timezone is encountered at runtime', () => {
        const instant = new Date('2026-08-16T21:30:00Z');
        expect(getDateInTimeZone('Not/AZone', instant)).toBe('2026-08-17');
    });

    it('filters legacy appointment wall-clock strings by clinic business date without UTC conversion', () => {
        const rows = [
            { id: 1, date_time: '2026-08-17T00:00:00' },
            { id: 2, date_time: '2026-08-17T23:59:59' },
            { id: 3, date_time: '2026-08-18T00:00:00' },
        ];
        expect(selectAppointmentsForBusinessDate(rows, '2026-08-17').map((row) => row.id)).toEqual([1, 2]);
    });
});
