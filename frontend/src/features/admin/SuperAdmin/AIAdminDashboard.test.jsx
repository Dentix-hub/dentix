import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AIAdminDashboard from './AIAdminDashboard';
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
    AreaChart: ({ children }) => <div>{children}</div>,
    BarChart: ({ children }) => <div>{children}</div>,
    Area: () => <div />,
    Bar: () => <div />,
    CartesianGrid: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
}));

describe('AIAdminDashboard MS-27 (truthful cards, null success rate, period selector)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders 3 authentic top metrics and no hardcoded active models card', async () => {
        api.get.mockImplementation((url) => {
            if (url.includes('/ai/admin/stats')) {
                return Promise.resolve({
                    data: {
                        period: 'month',
                        total_requests: 120,
                        success_rate: 98.5,
                        estimated_cost: 0.24,
                        tool_usage: [{ name: 'appointment', value: 80 }],
                        top_users: [{ name: 'dr_sami', count: 45 }],
                        usage_trends: [{ date: '2026-08-20', count: 15 }],
                    },
                });
            }
            if (url.includes('/ai/admin/logs')) {
                return Promise.resolve({
                    data: [
                        { id: 1, username: 'dr_sami', tool: 'appointment', status: 'SUCCESS', tenant_id: 1 },
                    ],
                });
            }
            return Promise.resolve({ data: {} });
        });

        render(<AIAdminDashboard />);

        expect(await screen.findByText('120')).toBeInTheDocument();
        expect(screen.getByText('98.5%')).toBeInTheDocument();
        expect(screen.getByText('$0.2400')).toBeInTheDocument();

        // Ensure no hardcoded "active_models" card or value 3
        expect(screen.queryByText('super_admin.ai.stats.active_models')).not.toBeInTheDocument();
        // Ensure no dead "view_all" buttons
        expect(screen.queryByText('super_admin.ai.users.view_all')).not.toBeInTheDocument();
        expect(screen.queryByText('super_admin.ai.logs.view_all')).not.toBeInTheDocument();
    });

    it('renders dash "—" when success_rate is null due to zero requests', async () => {
        api.get.mockImplementation((url) => {
            if (url.includes('/ai/admin/stats')) {
                return Promise.resolve({
                    data: {
                        period: 'today',
                        total_requests: 0,
                        success_rate: null,
                        estimated_cost: 0.0,
                        tool_usage: [],
                        top_users: [],
                        usage_trends: [],
                    },
                });
            }
            if (url.includes('/ai/admin/logs')) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        render(<AIAdminDashboard />);

        expect(await screen.findByText('0')).toBeInTheDocument();
        expect(screen.getByText('—')).toBeInTheDocument();
        expect(screen.getByText('$0.0000')).toBeInTheDocument();
    });

    it('switches periods between today, week, and month and re-fetches stats', async () => {
        api.get.mockResolvedValue({
            data: {
                period: 'month',
                total_requests: 5,
                success_rate: 100,
                estimated_cost: 0.01,
            },
        });

        render(<AIAdminDashboard />);

        const todayBtn = await screen.findByRole('button', { name: /super_admin.ai.periods.today/ });
        fireEvent.click(todayBtn);

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith('/api/v1/ai/admin/stats?period=today');
        });
    });
});
