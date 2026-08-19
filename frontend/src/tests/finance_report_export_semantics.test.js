import { describe, expect, it } from 'vitest';

import {
    adaptComprehensiveStats,
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

    it('does not replace authoritative backend zero metrics with derived fallbacks', () => {
        const summary = adaptComprehensiveStats({
            income: {
                gross_revenue: 1000,
                net_revenue: 1000,
                total_collected: 400,
                all_time_outstanding: 0,
                outstanding: 600,
                period_balance: 0,
            },
            deductions: {
                expenses: 100,
                lab_costs: 100,
                doctor_dues: { total: 100 },
                staff_dues: { total: 100 },
                total_deductions: 0,
            },
            net_profit: 0,
        });

        expect(summary.total_deductions).toBe(0);
        expect(summary.net_profit).toBe(0);
        expect(summary.all_time_outstanding).toBe(0);
        expect(summary.period_balance).toBe(0);
    });
});
