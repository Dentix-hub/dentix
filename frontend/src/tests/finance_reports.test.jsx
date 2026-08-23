import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import ReportsPage from '../features/finance/pages/ReportsPage';
import {
    adaptComprehensiveStats,
    adaptPatientsReport,
    adaptExpensesReport,
} from '../features/finance/reports/utils/reportAdapters';
import * as financialsApi from '../api/financials';
import * as billingApi from '../api/billing';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

vi.mock('../features/finance/useFinancePermissions', () => ({
    useFinancePermissions: () => ({
        canReadFinance: true,
        canWriteFinance: true,
        canConfigFinance: true,
        isAdmin: true,
        isAccountant: false,
    }),
}));

vi.mock('../api/financials', () => ({
    getFinanceSummary: vi.fn(),
    getPatientsReport: vi.fn(),
    getDoctorRevenue: vi.fn(),
    getAllProceduresFinancials: vi.fn(),
}));

vi.mock('../api/billing', () => ({
    getExpenses: vi.fn(),
}));

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
}

describe('Finance Reports V2 (Real Backend Contracts)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('reportAdapters - Contract Integrity', () => {
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
                    total_revenue: 120000.0,
                    gross_revenue: 125000.0,
                    total_discounts: 5000.0,
                    net_revenue: 120000.0,
                    total_collected: 95000.0,
                    outstanding: 35000.0,
                    all_time_outstanding: 35000.0,
                    period_balance: 25000.0,
                    total_appointments: 55,
                    unique_patients: 40,
                },
                deductions: {
                    doctor_dues: {
                        total: 30000.0,
                        details: [{ id: 1, name: 'د. خالد', total_due: 30000.0 }],
                    },
                    staff_dues: {
                        total: 12000.0,
                        details: [{ id: 2, username: 'مروة', due: 12000.0 }],
                    },
                    lab_costs: 9500.0,
                    expenses: 14500.0,
                    total_deductions: 66000.0,
                },
                net_operational_result: 29000.0,
                net_profit: 29000.0,
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

        it('adapts exact /accounting/patients-report response correctly', () => {
            const rawBackendResponse = {
                total: 2,
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
                        file_number: 101,
                        patient_name: 'أحمد محمود',
                        patient_phone: '01012345678',
                        total_invoiced: 8000.0,
                        total_paid: 6000.0,
                        outstanding_balance: 2000.0,
                        all_time_outstanding: 2500.0,
                    },
                    {
                        patient_id: 11,
                        file_number: 102,
                        patient_name: 'سارة إبراهيم',
                        patient_phone: '01098765432',
                        total_invoiced: 5000.0,
                        total_paid: 5000.0,
                        outstanding_balance: 0.0,
                        all_time_outstanding: 0.0,
                    },
                ],
            };

            const adapted = adaptPatientsReport(rawBackendResponse);

            expect(adapted.total).toBe(2);
            expect(adapted.summary.total_invoiced).toBe(25000);
            expect(adapted.summary.total_paid).toBe(21000);
            expect(adapted.summary.period_balance).toBe(4000);
            expect(adapted.summary.total_outstanding).toBe(4500);
            expect(adapted.summary.total_outstanding_scope).toBe('all_time_as_of_now');
            expect(adapted.patients[0].patient_name).toBe('أحمد محمود');
            expect(adapted.patients[0].invoiced_in_period).toBe(8000);
            expect(adapted.patients[0].paid_in_period).toBe(6000);
        });

        it('never derives report aggregates from the currently loaded patient page', () => {
            const adapted = adaptPatientsReport({
                total: 100,
                patients: [
                    {
                        patient_id: 1,
                        total_invoiced: 10000,
                        total_paid: 1000,
                        outstanding_balance: 9000,
                        all_time_outstanding: 9000,
                    },
                ],
            });

            expect(adapted.summary.total_invoiced).toBe(0);
            expect(adapted.summary.total_paid).toBe(0);
            expect(adapted.summary.period_balance).toBe(0);
            expect(adapted.summary.total_outstanding).toBe(0);
        });

        it('adapts expenses with explicit manual provenance', () => {
            const rawBackendResponse = [
                {
                    id: 1,
                    item_name: 'شراء قفازات',
                    category: 'مستلزمات طبية',
                    cost: 450.0,
                    notes: 'صيدلية النور',
                    date: '2026-08-10',
                    source: 'manual_expense',
                },
                {
                    id: 2,
                    item_name: 'فاتورة كهرباء',
                    category: 'مرافق',
                    cost: 1200.0,
                    notes: 'شهر يوليو',
                    date: '2026-08-01',
                    source: 'manual_expense',
                },
            ];

            const adapted = adaptExpensesReport(rawBackendResponse);

            expect(adapted.length).toBe(2);
            expect(adapted[0].amount).toBe(450);
            expect(adapted[0].notes).toBe('صيدلية النور');
            expect(adapted[0].source).toBe('manual_expense');
            expect(adapted[1].amount).toBe(1200);
            expect(adapted[1].category).toBe('مرافق');
        });
    });

    describe('<ReportsPage /> Rendering & Interaction', () => {
        it('renders executive financial income statement report with real backend data shape', async () => {
            financialsApi.getFinanceSummary.mockResolvedValue({
                data: {
                    data: {
                        definition_version: 'finance-summary-v1',
                        period: { start: '2026-08-01', end: '2026-08-15', timezone: 'Africa/Cairo' },
                        income: {
                            gross_revenue: 100000.0,
                            total_revenue: 100000.0,
                            net_revenue: 100000.0,
                            total_discounts: 0,
                            total_collected: 80000.0,
                            outstanding: 20000.0,
                            all_time_outstanding: 25000.0,
                            period_balance: 20000.0,
                            total_appointments: 40,
                            unique_patients: 30,
                        },
                        deductions: {
                            doctor_dues: { total: 25000.0, details: [] },
                            staff_dues: { total: 10000.0, details: [] },
                            lab_costs: 8000.0,
                            expenses: 12000.0,
                            total_deductions: 55000.0,
                        },
                        net_operational_result: 25000.0,
                        net_profit: 25000.0,
                    },
                },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter initialEntries={['/finance/reports?type=summary&from=2026-08-01&to=2026-08-15']}>
                        <ReportsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('الملخص المالي العام')).toBeDefined();
                expect(screen.getByText('قائمة الدخل والتدفقات المالية المعتمدة')).toBeDefined();
                expect(screen.getAllByText(/إجمالي قيمة الخدمات العلاجية/).length).toBeGreaterThan(0);
                expect(screen.getAllByText(/صافي الدخل التشغيلي للعيادة/).length).toBeGreaterThan(0);
            });
        });

        it('fetches every expense page before building the report', async () => {
            const firstPage = Array.from({ length: 200 }, (_, index) => ({
                id: index + 1,
                item_name: `مصروف ${index + 1}`,
                category: 'تشغيل',
                cost: 10,
            }));
            billingApi.getExpenses
                .mockResolvedValueOnce({ data: { data: { items: firstPage, total: 201 } } })
                .mockResolvedValueOnce({
                    data: {
                        data: {
                            items: [{ id: 201, item_name: 'آخر مصروف', category: 'صفحة ثانية', cost: 25 }],
                            total: 201,
                        },
                    },
                });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter initialEntries={['/finance/reports?type=expenses&from=2026-08-01&to=2026-08-15']}>
                        <ReportsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => expect(screen.getAllByText('صفحة ثانية').length).toBeGreaterThan(0));
            expect(billingApi.getExpenses).toHaveBeenCalledTimes(2);
            expect(billingApi.getExpenses).toHaveBeenLastCalledWith(expect.objectContaining({
                skip: 200,
                limit: 200,
            }));
        });
    });
});
