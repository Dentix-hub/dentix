import { describe, expect, it } from 'vitest';

import {
    formatRangeLabel,
    getPresetDates,
} from '../features/finance/utils/datePresets';


describe('Finance tenant-local date presets', () => {
    it('uses the clinic timezone at the UTC/Cairo midnight boundary', () => {
        const instant = new Date('2026-08-17T21:30:00Z');

        expect(getPresetDates('today', {
            timeZone: 'Africa/Cairo',
            now: instant,
        })).toEqual({
            from: '2026-08-18',
            to: '2026-08-18',
        });

        expect(getPresetDates('today', {
            timeZone: 'America/New_York',
            now: instant,
        })).toEqual({
            from: '2026-08-17',
            to: '2026-08-17',
        });
    });

    it('keeps month/week arithmetic calendar-only after resolving tenant today', () => {
        const instant = new Date('2026-08-17T21:30:00Z');
        const options = { timeZone: 'Africa/Cairo', now: instant };

        expect(getPresetDates('this_month', options)).toEqual({
            from: '2026-08-01',
            to: '2026-08-18',
        });
        expect(getPresetDates('this_week', options)).toEqual({
            from: '2026-08-15',
            to: '2026-08-18',
        });
    });

    it('renders a date-only range without allowing browser timezone shifts', () => {
        const label = formatRangeLabel('2026-08-18', '2026-08-18', 'en');
        expect(label).toContain('Aug');
        expect(label).toContain('18');
    });
});
