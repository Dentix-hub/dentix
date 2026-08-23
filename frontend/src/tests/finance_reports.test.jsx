import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import ReportsPage from '../features/finance/pages/ReportsPage';
import {
    adaptComprehensiveStats,
    adaptPatientsReport,
    adaptExpensesReport,
} from '../features/finance/reports/utils/reportAdapters';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

vi.mock('../features/finance/useFinancePermissions', () => ({
    useFinancePermissions: () => ({
        canViewOverview: true,
        canViewPatientAccounts: true,
        canViewPayments: true,
        canViewExpenses: true,
        canViewActivity: true,
        canViewPayroll: true,
        isDoctor: false,
    }),
}));

describe('Finance Reports & Insights', () => {
    describe('reportAdapters - compatibility integrity', () => {
        it('adapts exact authoritative summary payload without recreating formulas', () => {
            const rawBackendResponse = {
                definition_version: 'finance-summary-v1',
                currency: 'EGP',
                period: {
                    start: '2026-08-01',
                    end: '2026-08-15',
                    timezone: 'Africa/Cairo',
                    scope: 'period',
                },
                income: {
                    total_revenue: 120000,
                    gross_revenue: 125000,
                    total_discounts: 5000,
                    net_revenue: 120000,
                    total_collected: 95000,
                    outstanding: 35000,
                    all_time_outstanding: 35000,
                    period_balance: 25000,
                    total_appointments: 55,
                    unique_patients: 40,
                },
                deductions: {
                    doctor_dues: { total: 30000, details: [] },
                    staff_dues: { total: 12000, details: [] },
                    lab_costs: 9500,
                    expenses: 14500,
                    total_deductions: 66000,
                },
                net_operational_result: 29000,
                net_profit: 29000,
            };

            const adapted = adaptComprehensiveStats(rawBackendResponse);
            expect(adapted.invoiced_revenue).toBe(125000);
            expect(adapted.total_discounts).toBe(5000);
            expect(adapted.net_production).toBe(120000);
            expect(adapted.collected_revenue).toBe(95000);
            expect(adapted.manual_expenses).toBe(14500);
            expect(adapted.lab_costs).toBe(9500);
            expect(adapted.doctor_dues).toBe(30000);
            expect(adapted.staff_dues).toBe(12000);
            expect(adapted.total_deductions).toBe(66000);
            expect(adapted.net_profit).toBe(29000);
            expect(adapted.all_time_outstanding).toBe(35000);
            expect(adapted.period.timezone).toBe('Africa/Cairo');
            expect(adapted.definition_version).toBe('finance-summary-v1');
        });

        it('does not recreate profit or balance formulas when server fields are absent', () => {
            const adapted = adaptComprehensiveStats({
                income: {
                    gross_revenue: 1000,
                    net_revenue: 900,
                    total_collected: 800,
                },
                deductions: {
                    expenses: 100,
                    lab_costs: 50,
                    doctor_dues: { total: 100 },
                    staff_dues: { total: 50 },
                },
            });

            expect(adapted.total_deductions).toBe(0);
            expect(adapted.net_profit).toBe(0);
            expect(adapted.period_balance).toBe(0);
        });

        it('keeps server aggregate scope instead of deriving it from the current patient page', () => {
            const adapted = adaptPatientsReport({
                total: 100,
                summary: {
                    total_invoiced: 25000,
                    total_paid: 21000,
                    period_balance: 4000,
                    total_outstanding: 4500,
                    total_outstanding_scope: 'all_time_as_of_now',
                },
                patients: [
                    {
                        patient_id: 10,
                        patient_name: 'أحمد محمود',
                        total_invoiced: 8000,
                        total_paid: 6000,
                        all_time_outstanding: 2500,
                    },
                ],
            });

            expect(adapted.summary.total_invoiced).toBe(25000);
            expect(adapted.summary.total_outstanding).toBe(4500);
            expect(adapted.summary.total_outstanding_scope).toBe('all_time_as_of_now');
            expect(adapted.total).toBe(100);
        });

        it('preserves manual expense provenance for compatibility consumers', () => {
            const adapted = adaptExpensesReport([
                {
                    id: 1,
                    item_name: 'شراء قفازات',
                    category: 'مستلزمات طبية',
                    cost: 450,
                    notes: 'صيدلية النور',
                    date: '2026-08-10',
                    source: 'manual_expense',
                },
            ]);

            expect(adapted[0].amount).toBe(450);
            expect(adapted[0].source).toBe('manual_expense');
        });
    });

    describe('<ReportsPage /> PR5 hub', () => {
        it('links to canonical operational sources while preserving only the shared period', () => {
            render(
                <MemoryRouter initialEntries={['/finance/reports?from=2026-08-01&to=2026-08-15&preset=custom&type=providers&q=drop-me']}>
                    <ReportsPage />
                </MemoryRouter>
            );

            const overview = screen.getByRole('link', { name: /الملخص المالي المعتمد/ });
            const cash = screen.getByRole('link', { name: /الحركات النقدية/ });
            const team = screen.getByRole('link', { name: /الفريق والمستحقات/ });

            for (const link of [overview, cash, team]) {
                const url = new URL(link.getAttribute('href'), 'https://dentix.test');
                expect(url.searchParams.get('from')).toBe('2026-08-01');
                expect(url.searchParams.get('to')).toBe('2026-08-15');
                expect(url.searchParams.get('preset')).toBe('custom');
                expect(url.searchParams.has('type')).toBe(false);
                expect(url.searchParams.has('q')).toBe(false);
            }

            expect(new URL(overview.getAttribute('href'), 'https://dentix.test').pathname).toBe('/finance/overview');
            expect(new URL(cash.getAttribute('href'), 'https://dentix.test').pathname).toBe('/finance/cash-movements');
            expect(new URL(team.getAttribute('href'), 'https://dentix.test').pathname).toBe('/finance/team');
        });

        it('does not expose the retired duplicate report tabs or browser export action', () => {
            render(
                <MemoryRouter initialEntries={['/finance/reports']}>
                    <ReportsPage />
                </MemoryRouter>
            );

            expect(screen.getByTestId('reports-insights-hub')).toBeDefined();
            expect(screen.getByTestId('advanced-insights-deferred')).toBeDefined();
            expect(screen.queryByText('الملخص المالي العام')).toBeNull();
            expect(screen.queryByText('المصروفات حسب البند')).toBeNull();
            expect(screen.queryByText('أداء الأطباء')).toBeNull();
            expect(screen.queryByText('ربحية الإجراءات')).toBeNull();
            expect(screen.queryByRole('button', { name: /تصدير/ })).toBeNull();
        });
    });
});
