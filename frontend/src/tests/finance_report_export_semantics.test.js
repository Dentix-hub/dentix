import { describe, expect, it } from 'vitest';

import {
    adaptExpensesReport,
    adaptProvidersReport,
} from '../features/finance/reports/utils/reportAdapters';


describe('Finance report export semantics', () => {
    it('keeps monthly salary configuration separate from selected-period salary share', () => {
        const [provider] = adaptProvidersReport([{
            doctor_id: 1,
            doctor_name: 'Dr Test',
            fixed_salary: 3100,
            fixed_salary_period: 100,
            total_due: 250,
        }]);

        expect(provider.fixed_salary).toBe(3100);
        expect(provider.fixed_salary_period).toBe(100);
        expect(provider.total_due).toBe(250);
    });

    it('preserves expense notes for the CSV description column', () => {
        const [expense] = adaptExpensesReport([{
            id: 1,
            category: 'Supplies',
            cost: 450,
            notes: 'Box of gloves',
            date: '2026-08-18',
        }]);

        expect(expense.notes).toBe('Box of gloves');
        expect(expense.amount).toBe(450);
    });
});
