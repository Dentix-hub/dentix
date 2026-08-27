import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import AdminCharts from './AdminCharts';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/components/charts/LazyChart', () => ({
    LazyChart: ({ children }) => <div data-testid="lazy-chart">{children}</div>,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
    PieChart: ({ children }) => <div>{children}</div>,
    Pie: () => <div />,
    Cell: () => <div />,
    AreaChart: () => <div />,
    Area: () => <div />,
    BarChart: () => <div />,
    Bar: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
}));

describe('AdminCharts MS-11', () => {
    it('renders 12-month analytics charts and non-duplicated plan legend', () => {
        const mockStats = {
            monthly_revenue: {
                '2026-01': 10000,
                '2026-02': 15000,
                '2026-03': 20000,
            },
            clinic_growth: {
                '2026-01': 2,
                '2026-02': 5,
                '2026-03': 8,
            },
            plan_distribution: {
                Gold: 12,
                Silver: 8,
                Basic: 4,
            },
        };

        render(<AdminCharts stats={mockStats} />);

        expect(screen.getByText('super_admin.charts.revenue_title')).toBeInTheDocument();
        expect(screen.getByText('super_admin.charts.growth_title')).toBeInTheDocument();
        expect(screen.getByText('super_admin.charts.distribution_title')).toBeInTheDocument();

        // Custom non-duplicated legend cards
        expect(screen.getByText('Gold')).toBeInTheDocument();
        expect(screen.getByText('12')).toBeInTheDocument();
        expect(screen.getByText('Silver')).toBeInTheDocument();
        expect(screen.getByText('8')).toBeInTheDocument();
    });

    it('renders empty fallback when plan distribution is empty', () => {
        const mockStats = {
            monthly_revenue: {},
            clinic_growth: {},
            plan_distribution: {},
        };

        render(<AdminCharts stats={mockStats} />);

        expect(screen.getByText('common.no_results')).toBeInTheDocument();
    });
});
