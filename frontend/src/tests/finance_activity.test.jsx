import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import ActivityPage from '../features/finance/pages/ActivityPage';
import ActivityTypeBadge from '../features/finance/activity/components/ActivityTypeBadge';
import * as financialsApi from '../api/financials';

// Mock react-i18next
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

// Mock permissions hook
vi.mock('../features/finance/useFinancePermissions', () => ({
    useFinancePermissions: () => ({
        canReadFinance: true,
        canWriteFinance: true,
        canConfigFinance: true,
        isAdmin: true,
        isAccountant: false,
    }),
}));

// Mock financials APIs
vi.mock('../api/financials', () => ({
    getFinancialActivity: vi.fn(),
}));

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
}

describe('Finance Activity V2', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('<ActivityPage />', () => {
        it('renders financial activity timeline with inflow/outflow metrics and event rows', async () => {
            financialsApi.getFinancialActivity.mockResolvedValue({
                data: {
                    data: {
                        events: [
                            {
                                id: 'payment-1',
                                source_type: 'payment',
                                source_id: 1,
                                timestamp: '2026-08-15T10:30:00',
                                direction: 'inflow',
                                amount: 1500,
                                currency: 'EGP',
                                title: 'أحمد حسن',
                                subtitle: 'دفعة نقدية مسددة',
                                badge_text: 'دفعة مريض',
                                nav_url: '/finance/payments?patient_id=10',
                                patient_id: 10,
                                user_id: 2,
                            },
                            {
                                id: 'expense-2',
                                source_type: 'expense',
                                source_id: 2,
                                timestamp: '2026-08-15T11:00:00',
                                direction: 'outflow',
                                amount: 350,
                                currency: 'EGP',
                                title: 'أدوات ومستهلكات',
                                subtitle: 'شراء قفازات وكمامات',
                                badge_text: 'مصروف عيادة',
                                nav_url: '/finance/expenses',
                                patient_id: null,
                                user_id: null,
                            },
                            {
                                id: 'salary-3',
                                source_type: 'salary',
                                source_id: 3,
                                timestamp: '2026-08-15T12:00:00',
                                direction: 'outflow',
                                amount: 4000,
                                currency: 'EGP',
                                title: 'راتب: مروة علي',
                                subtitle: 'راتب شهر أغسطس',
                                badge_text: 'راتب موظف',
                                nav_url: '/finance/compensation/payroll?month=2026-08',
                                patient_id: null,
                                user_id: 5,
                            },
                        ],
                        total_count: 3,
                        total_inflow: 1500,
                        total_outflow: 4350,
                        net_flow: -2850,
                        skip: 0,
                        limit: 20,
                    },
                },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter initialEntries={['/finance/activity?from=2026-08-01&to=2026-08-15']}>
                        <ActivityPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('إجمالي التدفقات الواردة')).toBeDefined();
                expect(screen.getAllByText('أحمد حسن').length).toBeGreaterThan(0);
                expect(screen.getAllByText('أدوات ومستهلكات').length).toBeGreaterThan(0);
                expect(screen.getAllByText('راتب: مروة علي').length).toBeGreaterThan(0);
            });

            expect(screen.getAllByText('دفعة مريض').length).toBeGreaterThan(0);
            expect(screen.getAllByText('مصروف عيادة').length).toBeGreaterThan(0);
            expect(screen.getAllByText('راتب موظف').length).toBeGreaterThan(0);
        });
    });

    describe('<ActivityTypeBadge />', () => {
        it('renders badges with distinct directional markers and labels', () => {
            const { rerender } = render(
                <ActivityTypeBadge sourceType="payment" direction="inflow" />
            );
            expect(screen.getByText('دفعة مريض')).toBeDefined();
            expect(screen.getByText('(+)')).toBeDefined();

            rerender(
                <ActivityTypeBadge sourceType="expense" direction="outflow" />
            );
            expect(screen.getByText('مصروف عيادة')).toBeDefined();
            expect(screen.getByText('(−)')).toBeDefined();

            rerender(
                <ActivityTypeBadge sourceType="lab" direction="outflow" />
            );
            expect(screen.getByText('معمل أسنان')).toBeDefined();

            rerender(
                <ActivityTypeBadge sourceType="salary" direction="outflow" />
            );
            expect(screen.getByText('راتب موظف')).toBeDefined();
        });
    });
});
