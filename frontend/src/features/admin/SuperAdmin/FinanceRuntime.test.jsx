import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import FinanceReports from './FinanceReports';
import PaymentsManager from './PaymentsManager';
import ActiveSubscriptions from './ActiveSubscriptions';
import { api } from '@/api';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    api: {
        get: vi.fn(),
    },
}));

vi.mock('@/components/charts/LazyChart', () => ({
    LazyChart: ({ children }) => <div data-testid="lazy-chart">{children}</div>,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
    PieChart: ({ children }) => <div>{children}</div>,
    Pie: () => <div />,
    Cell: () => <div />,
    AreaChart: () => <div />,
    Area: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
}));

vi.mock('@/shared/ui', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe('Finance Runtime & Mobile Safety MS-09', () => {
    it('renders FinanceReports with zero overdue clinics without ReferenceError', async () => {
        api.get.mockResolvedValueOnce({
            data: {
                monthly_forecast: 50000,
                overdue_clinics: [],
                churn_risks: [],
                revenue_by_plan: [{ name: 'Gold', value: 30000 }],
                growth_trends: [{ month: 'Jan', revenue: 10000 }],
            },
        });

        render(<FinanceReports />);

        await waitFor(() => {
            expect(screen.getByText('super_admin.finance.no_overdue')).toBeInTheDocument();
            expect(screen.getByText('super_admin.finance.no_churn')).toBeInTheDocument();
        });
    });

    it('renders PaymentsManager with overflow container and handles null fields gracefully', () => {
        const mockPayments = [
            {
                id: 1,
                tenant_id: 10,
                plan_id: 2,
                amount: 1500,
                payment_date: '2026-08-15T12:00:00Z',
                paid_by: 'Dr. John',
                payment_method: 'credit_card',
            },
            {
                id: 2,
                tenant_id: 999, // unknown tenant
                plan_id: null,
                amount: null,
                payment_date: null,
                paid_by: null,
                payment_method: 'cash',
            },
        ];

        const mockTenants = [{ id: 10, name: 'Apex Dental' }];
        const mockPlans = [{ id: 2, name: 'Pro', display_name_ar: 'الاحترافية' }];

        const { container } = render(
            <PaymentsManager
                payments={mockPayments}
                tenants={mockTenants}
                plans={mockPlans}
                onDelete={vi.fn()}
            />
        );

        expect(container.querySelector('.overflow-x-auto')).toBeInTheDocument();
        expect(screen.getByText('Apex Dental')).toBeInTheDocument();
        expect(screen.getAllByText((content) => content.includes('super_admin.finance.currency') && content.includes('+')).length).toBe(2);
    });



    it('renders ActiveSubscriptions with null-safe clinic names and proper status', () => {
        const mockTenants = [
            {
                id: 1,
                name: 'Smiles Clinic',
                plan_id: 5,
                subscription_end_date: '2026-12-31',
                is_active: true,
            },
            {
                id: 2,
                name: '',
                clinic_name: 'Al-Nour Clinic',
                plan_id: null,
                subscription_end_date: '2026-01-01',
                is_active: false,
            },
        ];

        const mockPlans = [{ id: 5, name: 'Starter', display_name_ar: 'الأساسية', price: 500 }];

        const { container } = render(
            <ActiveSubscriptions
                tenants={mockTenants}
                plans={mockPlans}
                getDaysRemaining={(date) => (date === '2026-12-31' ? 120 : -10)}
            />
        );

        expect(container.querySelector('.overflow-x-auto')).toBeInTheDocument();
        expect(screen.getByText('Smiles Clinic')).toBeInTheDocument();
        expect(screen.getByText('Al-Nour Clinic')).toBeInTheDocument();
        expect(screen.getByText('common.active')).toBeInTheDocument();
        expect(screen.getByText('common.expired')).toBeInTheDocument();
    });
});
