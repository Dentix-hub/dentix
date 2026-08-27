import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import FinanceReports from './FinanceReports';
import { api } from '@/api';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'en' },
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

describe('FinanceReports Forecast & Null-Safety MS-12', () => {
    it('handles null, undefined, and invalid dates in churn risks and overdue clinics without throwing', async () => {
        api.get.mockResolvedValueOnce({
            data: {
                success: true,
                data: {
                    monthly_forecast: 12500,
                    overdue_clinics: [
                        {
                            id: 1,
                            name: 'Overdue Safe Clinic',
                            expiry_date: null,
                            days_overdue: 15,
                            plan_name: 'Pro',
                        },
                        {
                            id: 2,
                            name: 'Invalid Date Clinic',
                            expiry_date: 'invalid-date-string',
                            days_overdue: null,
                            plan_name: null,
                        },
                    ],
                    churn_risks: [
                        {
                            id: 10,
                            name: 'Null Active Clinic',
                            last_active: null,
                            plan_name: 'Basic',
                        },
                        {
                            id: 11,
                            name: 'Invalid Active Clinic',
                            last_active: 'not-a-valid-date',
                            plan_name: null,
                        },
                    ],
                    revenue_by_plan: [{ name: 'Enterprise', value: 8000 }],
                    growth_trends: [{ month: '2026-02', revenue: 12000 }],
                },
            },
        });


        render(<FinanceReports />);

        await waitFor(() => {
            expect(screen.getByText('Overdue Safe Clinic')).toBeInTheDocument();
            expect(screen.getByText('Invalid Date Clinic')).toBeInTheDocument();
            expect(screen.getByText('Null Active Clinic')).toBeInTheDocument();
            expect(screen.getByText('Invalid Active Clinic')).toBeInTheDocument();
            expect(screen.getByText('12,500')).toBeInTheDocument();
        });
    });
});
