import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Overview from './Overview';

const apiMocks = vi.hoisted(() => ({
    apiGet: vi.fn(),
}));

vi.mock('@/api', () => ({
    api: {
        get: apiMocks.apiGet,
    },
}));

vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
    }),
}));

vi.mock('@/features/admin/SuperAdmin/DashboardStats', () => ({
    default: ({ stats }) => <div data-testid="dashboard-stats">{stats.total_tenants} tenants</div>,
}));

vi.mock('@/features/admin/SuperAdmin/SystemHealth', () => ({
    default: () => <div data-testid="system-health">System Health Component</div>,
}));

vi.mock('@/features/admin/SuperAdmin/ActivityFeed', () => ({
    default: () => <div data-testid="activity-feed">Activity Feed</div>,
}));

vi.mock('@/features/admin/SuperAdmin/AdminCharts', () => ({
    default: () => <div data-testid="admin-charts">Admin Charts</div>,
}));

describe('Overview truth-state and resilient loading', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders stats and components on successful fetch', async () => {
        apiMocks.apiGet.mockResolvedValue({
            data: {
                total_tenants: 15,
                active_tenants: 12,
                expired_tenants: 3,
                total_revenue: 50000,
                activity_feed: [],
            },
        });

        render(<Overview />);

        expect(await screen.findByTestId('dashboard-stats')).toHaveTextContent('15 tenants');
        expect(screen.getByTestId('system-health')).toBeInTheDocument();
        expect(screen.getByTestId('admin-charts')).toBeInTheDocument();
        expect(screen.queryByText('تعذر تحميل إحصائيات مركز القيادة')).not.toBeInTheDocument();
    });

    it('renders error banner and keeps SystemHealth usable when stats API fails', async () => {
        apiMocks.apiGet.mockRejectedValue(new Error('Stats service offline'));

        render(<Overview />);

        expect(await screen.findByText('تعذر تحميل إحصائيات مركز القيادة')).toBeInTheDocument();
        expect(screen.getByText('إعادة المحاولة')).toBeInTheDocument();
        // SystemHealth is still rendered and usable
        expect(screen.getByTestId('system-health')).toBeInTheDocument();
        expect(screen.queryByTestId('dashboard-stats')).not.toBeInTheDocument();
    });
});
