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
        canExportReports: true,
        isDoctor: false,
    }),
}));

vi.mock('../api/financials', () => ({
    getPeriodComparisonReport: vi.fn(),
    getMaterialMarginReport: vi.fn(),
    exportPeriodComparisonReport: vi.fn(),
    exportMaterialMarginReport: vi.fn(),
}));

function createQueryClient() {
    return new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
}

function renderReports(initialEntry = '/finance/reports?from=2026-08-01&to=2026-08-15') {
    return render(
        <QueryClientProvider client={createQueryClient()}>
            <MemoryRouter initialEntries={[initialEntry]}>
                <ReportsPage />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

const comparisonPayload = {
    definition_version: 'finance-summary-v1',
    currency: 'EGP',
    current_period: {
        start: '2026-08-01',
        end: '2026-08-15',
        timezone: 'Africa/Cairo',
    },
    comparison_period: {
        start: '2026-07-17',
        end: '2026-07-31',
        timezone: 'Africa/Cairo',
    },
    metrics: [
        {
            metric: 'collected',
            current: 95000,
            comparison: 80000,
            delta: 15000,
            delta_percent: 18.75,
        },
        {
            metric: 'net_operational_result',
            current: 29000,
            comparison: 25000,
            delta: 4000,
            delta_percent: 16,
        },
    ],
};

const materialPayload = {
    definition_version: 'estimated-material-margin-v2',
    metric_scope: 'materials_only',
    warning: 'Incomplete procedures have null margin values',
    items: [
        {
            procedure_id: 1,
            procedure_name: 'زراعة سن',
            current_price: 12000,
            material_cost: null,
            material_margin: null,
            margin_percent: null,
            coverage_percent: 0,
            confidence: 'unavailable',
            status: 'unavailable',
        },
        {
            procedure_id: 2,
            procedure_name: 'حشو تجميلي',
            current_price: 1500,
            material_cost: 250,
            material_margin: 1250,
            margin_percent: 83.3,
            coverage_percent: 100,
            confidence: 'medium',
            status: 'complete',
        },
    ],
    pagination: { skip: 0, limit: 25, total: 2, returned: 2 },
    completeness: {
        complete: 1,
        partial: 0,
        unavailable: 1,
        errors: 0,
        coverage_percent: 50,
    },
};

describe('Finance Reports & Insights', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        financialsApi.getPeriodComparisonReport.mockResolvedValue({ data: comparisonPayload });
        financialsApi.getMaterialMarginReport.mockResolvedValue({ data: materialPayload });
    });

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
                income: { gross_revenue: 1000, net_revenue: 900, total_collected: 800 },
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
                patients: [{ patient_id: 10, patient_name: 'أحمد محمود', total_invoiced: 8000, total_paid: 6000, all_time_outstanding: 2500 }],
            });
            expect(adapted.summary.total_invoiced).toBe(25000);
            expect(adapted.summary.total_outstanding).toBe(4500);
            expect(adapted.total).toBe(100);
        });

        it('preserves manual expense provenance for compatibility consumers', () => {
            const adapted = adaptExpensesReport([{ id: 1, item_name: 'شراء قفازات', category: 'مستلزمات طبية', cost: 450, notes: 'صيدلية النور', date: '2026-08-10', source: 'manual_expense' }]);
            expect(adapted[0].amount).toBe(450);
            expect(adapted[0].source).toBe('manual_expense');
        });
    });

    describe('<ReportsPage /> PR6 server-backed workspace', () => {
        it('uses active URL period/filter/pagination state in server requests', async () => {
            renderReports('/finance/reports?from=2026-08-01&to=2026-08-15&q=implant&page=2&sort=price_desc');

            await waitFor(() => {
                expect(financialsApi.getPeriodComparisonReport).toHaveBeenCalledWith({
                    start_date: '2026-08-01',
                    end_date: '2026-08-15',
                });
                expect(financialsApi.getMaterialMarginReport).toHaveBeenCalledWith({
                    search: 'implant',
                    skip: 25,
                    limit: 25,
                    sort: 'price_desc',
                });
            });
        });

        it('renders server comparison and withholds incomplete material margin without faking a 100% margin', async () => {
            renderReports();

            await waitFor(() => {
                expect(screen.getByText('مقارنة الفترة')).toBeDefined();
                expect(screen.getAllByText('زراعة سن').length).toBeGreaterThan(0);
                expect(screen.getAllByText('حشو تجميلي').length).toBeGreaterThan(0);
            });

            expect(screen.getAllByText('غير متاح').length).toBeGreaterThan(0);
            expect(screen.getByText(/تم حجب الهامش بدل افتراض تكلفة صفرية/)).toBeDefined();

            const implantMatches = screen.getAllByText('زراعة سن');
            const unavailableItem = implantMatches.find((node) => node.closest('tr')) || implantMatches[0];
            const unavailableRow = unavailableItem.closest('tr') || unavailableItem.closest('article');
            expect(unavailableRow).not.toBeNull();
            expect(unavailableRow.textContent).toContain('غير متاح');
            expect(unavailableRow.textContent).not.toContain('100%');

            // 100% coverage is valid for a complete row; the actual material margin is 83.3%.
            expect(screen.getAllByText('100%').length).toBeGreaterThan(0);
            expect(screen.getAllByText('83.3%').length).toBeGreaterThan(0);
        });

        it('keeps canonical operational links and preserves only shared period params', async () => {
            renderReports('/finance/reports?from=2026-08-01&to=2026-08-15&preset=custom&q=drop-me&page=3');

            await waitFor(() => expect(screen.getByText('المصادر التشغيلية الأصلية')).toBeDefined());
            const overview = screen.getByRole('link', { name: /الملخص المالي المعتمد/ });
            const cash = screen.getByRole('link', { name: /الحركات النقدية/ });
            const team = screen.getByRole('link', { name: /الفريق والمستحقات/ });

            for (const link of [overview, cash, team]) {
                const url = new URL(link.getAttribute('href'), 'https://dentix.test');
                expect(url.searchParams.get('from')).toBe('2026-08-01');
                expect(url.searchParams.get('to')).toBe('2026-08-15');
                expect(url.searchParams.get('preset')).toBe('custom');
                expect(url.searchParams.has('q')).toBe(false);
                expect(url.searchParams.has('page')).toBe(false);
            }
        });

        it('disables exports when report APIs fail and does not render fallback zero reports', async () => {
            financialsApi.getPeriodComparisonReport.mockRejectedValueOnce(new Error('comparison failed'));
            financialsApi.getMaterialMarginReport.mockRejectedValueOnce(new Error('material failed'));
            renderReports();

            await waitFor(() => {
                expect(screen.getByText(/تعذر تحميل مقارنة الفترة/)).toBeDefined();
                expect(screen.getByText(/تعذر تحميل هامش المواد/)).toBeDefined();
            });

            const exportButtons = screen.getAllByRole('button', { name: /تصدير/ });
            expect(exportButtons.length).toBe(2);
            exportButtons.forEach((button) => expect(button.disabled).toBe(true));
            expect(screen.queryByLabelText('0 EGP')).toBeNull();
        });
    });
});
