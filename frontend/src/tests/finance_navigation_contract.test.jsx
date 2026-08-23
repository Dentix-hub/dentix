import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import {
    MemoryRouter,
    Route,
    Routes,
    useLocation,
} from 'react-router-dom';

import FinanceNav from '../features/finance/components/FinanceNav';
import CashMovementsLayout from '../features/finance/pages/CashMovementsLayout';
import TeamLayout from '../features/finance/pages/TeamLayout';
import LegacyFinanceRedirect from '../features/finance/LegacyFinanceRedirect';
import ReportsPage from '../features/finance/pages/ReportsPage';

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

function LocationProbe() {
    const location = useLocation();
    return (
        <output data-testid="location-probe">
            {`${location.pathname}${location.search}${location.hash}`}
        </output>
    );
}

describe('Finance PR5 information-architecture contracts', () => {
    it('exposes exactly five canonical Finance destinations and preserves only shared period params', () => {
        render(
            <MemoryRouter initialEntries={['/finance/cash-movements/payments?from=2026-08-01&to=2026-08-15&preset=custom&q=ali&page=3&payment_id=99']}>
                <FinanceNav />
            </MemoryRouter>
        );

        const links = screen.getAllByRole('link');
        expect(links).toHaveLength(5);
        expect(links.map((link) => link.textContent)).toEqual([
            'الملخص',
            'حسابات المرضى',
            'الحركات النقدية',
            'الفريق',
            'التقارير والرؤى',
        ]);

        const reportsLink = screen.getByRole('link', { name: /التقارير والرؤى/ });
        const url = new URL(reportsLink.getAttribute('href'), 'https://dentix.test');
        expect(url.pathname).toBe('/finance/reports');
        expect(url.searchParams.get('from')).toBe('2026-08-01');
        expect(url.searchParams.get('to')).toBe('2026-08-15');
        expect(url.searchParams.get('preset')).toBe('custom');
        expect(url.searchParams.has('q')).toBe(false);
        expect(url.searchParams.has('page')).toBe(false);
        expect(url.searchParams.has('payment_id')).toBe(false);
    });

    it('Cash Movements index redirects to the first authorized operational child with the shared period only', async () => {
        render(
            <MemoryRouter initialEntries={['/finance/cash-movements?from=2026-08-01&to=2026-08-15&preset=custom&q=drop-me']}>
                <Routes>
                    <Route path="/finance/cash-movements" element={<CashMovementsLayout />} />
                    <Route path="/finance/cash-movements/payments" element={<LocationProbe />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            const text = screen.getByTestId('location-probe').textContent;
            expect(text).toContain('/finance/cash-movements/payments');
            expect(text).toContain('from=2026-08-01');
            expect(text).toContain('to=2026-08-15');
            expect(text).toContain('preset=custom');
            expect(text).not.toContain('q=drop-me');
        });
    });

    it('Team index redirects to doctors while preserving the shared period', async () => {
        render(
            <MemoryRouter initialEntries={['/finance/team?from=2026-08-01&to=2026-08-15&preset=custom&q=drop-me']}>
                <Routes>
                    <Route path="/finance/team" element={<TeamLayout />} />
                    <Route path="/finance/team/doctors" element={<LocationProbe />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            const text = screen.getByTestId('location-probe').textContent;
            expect(text).toContain('/finance/team/doctors');
            expect(text).toContain('from=2026-08-01');
            expect(text).toContain('to=2026-08-15');
            expect(text).toContain('preset=custom');
            expect(text).not.toContain('q=drop-me');
        });
    });

    it('legacy expense and doctor-detail bookmarks redirect to canonical paths without losing query/hash', async () => {
        const { unmount } = render(
            <MemoryRouter initialEntries={['/expenses?from=2026-08-01&to=2026-08-15#manual-42']}>
                <Routes>
                    <Route path="/expenses" element={<LegacyFinanceRedirect to="/finance/cash-movements/expenses" />} />
                    <Route path="/finance/cash-movements/expenses" element={<LocationProbe />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByTestId('location-probe').textContent).toBe(
                '/finance/cash-movements/expenses?from=2026-08-01&to=2026-08-15#manual-42',
            );
        });
        unmount();

        render(
            <MemoryRouter initialEntries={['/finance/compensation/doctors/42?from=2026-08-01#due']}>
                <Routes>
                    <Route
                        path="/finance/compensation/doctors/:doctorId"
                        element={<LegacyFinanceRedirect to={({ doctorId }) => `/finance/team/doctors/${doctorId}`} />}
                    />
                    <Route path="/finance/team/doctors/:doctorId" element={<LocationProbe />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByTestId('location-probe').textContent).toBe(
                '/finance/team/doctors/42?from=2026-08-01#due',
            );
        });
    });

    it('Reports & Insights is a non-duplicated hub instead of a second operational report workspace', () => {
        render(
            <MemoryRouter initialEntries={['/finance/reports?from=2026-08-01&to=2026-08-15&type=summary']}>
                <ReportsPage />
            </MemoryRouter>
        );

        expect(screen.getByTestId('reports-insights-hub')).toBeDefined();
        expect(screen.getByText('التقارير والرؤى')).toBeDefined();
        expect(screen.getByText('الملخص المالي المعتمد')).toBeDefined();
        expect(screen.getByText('التحصيلات والذمم')).toBeDefined();
        expect(screen.getByText('الحركات النقدية')).toBeDefined();
        expect(screen.getByText('الفريق والمستحقات')).toBeDefined();
        expect(screen.queryByText('الملخص المالي العام')).toBeNull();
        expect(screen.queryByText('تصدير')).toBeNull();
    });
});
