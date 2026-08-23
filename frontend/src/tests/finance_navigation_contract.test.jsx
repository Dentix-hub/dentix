import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import {
    MemoryRouter,
    Route,
    Routes,
    useLocation,
} from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import FinanceNav from '../features/finance/components/FinanceNav';
import CompensationLayout from '../features/finance/pages/CompensationLayout';
import LegacyFinanceRedirect from '../features/finance/LegacyFinanceRedirect';
import ReportsPage from '../features/finance/pages/ReportsPage';
import * as financialsApi from '../api/financials';

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
        canViewOverview: true,
        canViewPatientAccounts: true,
        canViewPayments: true,
        canViewExpenses: true,
        canViewPayroll: true,
        canViewActivity: true,
        canViewReports: true,
        isDoctor: false,
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
    return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function LocationProbe() {
    const location = useLocation();
    return (
        <output data-testid="location-probe">
            {`${location.pathname}${location.search}${location.hash}`}
        </output>
    );
}

const summaryPayload = {
    definition_version: 'finance-summary-v1',
    period: {
        start: '2026-08-01',
        end: '2026-08-15',
        timezone: 'Africa/Cairo',
        scope: 'period',
    },
    income: {
        gross_revenue: 1000,
        total_revenue: 900,
        total_discounts: 100,
        net_revenue: 900,
        total_collected: 700,
        all_time_outstanding: 200,
        period_balance: 200,
        total_appointments: 2,
        unique_patients: 2,
    },
    deductions: {
        doctor_dues: { total: 100, details: [] },
        staff_dues: { total: 50, details: [] },
        lab_costs: 25,
        expenses: 25,
        total_deductions: 200,
    },
    net_operational_result: 500,
    net_profit: 500,
};

describe('Finance PR4 URL/navigation contracts', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        financialsApi.getFinanceSummary.mockResolvedValue({
            data: { data: summaryPayload },
        });
    });

    it('canonicalizes an invalid reports type to summary instead of rendering a blank report', async () => {
        render(
            <QueryClientProvider client={createTestQueryClient()}>
                <MemoryRouter initialEntries={['/finance/reports?type=not-a-report&from=2026-08-01&to=2026-08-15']}>
                    <ReportsPage />
                    <LocationProbe />
                </MemoryRouter>
            </QueryClientProvider>
        );

        await waitFor(() => {
            expect(screen.getByText('قائمة الدخل والتدفقات المالية المعتمدة')).toBeDefined();
            expect(financialsApi.getFinanceSummary).toHaveBeenCalledWith('2026-08-01', '2026-08-15');
            expect(screen.getByTestId('location-probe').textContent).toContain('type=summary');
        });
    });

    it('FinanceNav preserves only shared period params across destinations', () => {
        render(
            <MemoryRouter initialEntries={['/finance/payments?from=2026-08-01&to=2026-08-15&preset=custom&q=ali&page=3&payment_id=99']}>
                <FinanceNav />
            </MemoryRouter>
        );

        const reportsLink = screen.getByRole('link', { name: /التقارير المالية/ });
        const url = new URL(reportsLink.getAttribute('href'), 'https://dentix.test');
        expect(url.pathname).toBe('/finance/reports');
        expect(url.searchParams.get('from')).toBe('2026-08-01');
        expect(url.searchParams.get('to')).toBe('2026-08-15');
        expect(url.searchParams.get('preset')).toBe('custom');
        expect(url.searchParams.has('q')).toBe(false);
        expect(url.searchParams.has('page')).toBe(false);
        expect(url.searchParams.has('payment_id')).toBe(false);
    });

    it('compensation index redirect preserves the shared period', async () => {
        render(
            <MemoryRouter initialEntries={['/finance/compensation?from=2026-08-01&to=2026-08-15&preset=custom&q=drop-me']}>
                <Routes>
                    <Route path="/finance/compensation" element={<CompensationLayout />} />
                    <Route path="/finance/compensation/doctors" element={<LocationProbe />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            const text = screen.getByTestId('location-probe').textContent;
            expect(text).toContain('/finance/compensation/doctors');
            expect(text).toContain('from=2026-08-01');
            expect(text).toContain('to=2026-08-15');
            expect(text).toContain('preset=custom');
            expect(text).not.toContain('q=drop-me');
        });
    });

    it('legacy redirects preserve query and hash while changing only the pathname', async () => {
        render(
            <MemoryRouter initialEntries={['/expenses?from=2026-08-01&to=2026-08-15#manual-42']}>
                <Routes>
                    <Route path="/expenses" element={<LegacyFinanceRedirect to="/finance/expenses" />} />
                    <Route path="/finance/expenses" element={<LocationProbe />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByTestId('location-probe').textContent).toBe(
                '/finance/expenses?from=2026-08-01&to=2026-08-15#manual-42',
            );
        });
    });
});
