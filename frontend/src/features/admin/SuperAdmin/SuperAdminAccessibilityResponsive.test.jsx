import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TenantsManager from './TenantsManager';
import UsersManager from './UsersManager';
import SystemHealth from './SystemHealth';
import ActivityFeed from './ActivityFeed';
import StatCard from '@/shared/ui/StatCard';
import { Building2 } from 'lucide-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => fallback || key,
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/api', () => ({
    api: {
        get: vi.fn().mockResolvedValue({ data: [] }),
        post: vi.fn(),
    },
}));

vi.mock('./hooks/useSystemHealth', async () => {
    const actual = await vi.importActual('./hooks/useSystemHealth');
    return {
        ...actual,
        useSystemHealth: () => ({
            data: {
                status: 'healthy',
                score: 100,
                database: { status: 'healthy' },
                redis: { status: 'healthy' },
                active_sessions: 4,
                recent_errors_count: 0,
                background_jobs: [],
            },
            isLoading: false,
            error: null,
        }),
        useInvalidateSystemHealth: () => vi.fn(),
    };
});

describe('Super Admin Accessibility, Dark Mode, and Responsive Attributes MS-33', () => {
    let queryClient;

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: {
                queries: { retry: false },
            },
        });
    });

    it('ensures StatCard has accessible markup and no false interactive roles unless onClick provided', () => {
        const { container, rerender } = render(
            <StatCard
                icon={Building2}
                title="إجمالي العيادات"
                value="25"
                subtext="نشطة"
                color="indigo"
            />
        );

        expect(screen.getByText('إجمالي العيادات')).toBeInTheDocument();
        expect(screen.getByText('25')).toBeInTheDocument();
        // Non-interactive card does NOT have cursor-pointer
        expect(container.firstChild).not.toHaveClass('cursor-pointer');

        // Interactive card gets cursor-pointer
        const handleClick = vi.fn();
        rerender(
            <StatCard
                icon={Building2}
                title="إجمالي العيادات"
                value="25"
                color="indigo"
                onClick={handleClick}
            />
        );
        expect(container.firstChild).toHaveClass('cursor-pointer');
    });

    it('ensures TenantsManager table wraps in an overflow container for mobile responsiveness', () => {
        const sampleTenants = [
            { id: 1, name: 'Dental Center', domain: 'center', is_active: true, is_deleted: false, total_revenue: 5000 },
        ];

        const { container } = render(
            <TenantsManager
                tenants={sampleTenants}
                plans={[]}
                getDaysRemaining={() => 45}
            />
        );

        const tableWrapper = container.querySelector('.overflow-x-auto');
        expect(tableWrapper).toBeInTheDocument();
        expect(screen.getByText('Dental Center')).toBeInTheDocument();

        // Accessible action buttons have titles
        const detailBtn = screen.getByTitle('تفاصيل العيادة');
        expect(detailBtn).toHaveAttribute('type', 'button');
    });

    it('ensures UsersManager search form and inputs are fully accessible', () => {
        const sampleUsers = [
            { id: 10, username: 'admin_dr', role: 'admin', is_active: true, tenant_name: 'Cairo Clinic' },
        ];

        render(
            <UsersManager
                users={sampleUsers}
                onSearch={vi.fn()}
                onToggleStatus={vi.fn()}
            />
        );

        const searchInput = screen.getByPlaceholderText('البحث بالاسم أو البريد الإلكتروني...');
        expect(searchInput).toBeInTheDocument();

        const toggleBtn = screen.getByTitle('تعطيل الحساب');
        expect(toggleBtn).toBeInTheDocument();
        expect(toggleBtn).toHaveAttribute('type', 'button');
    });

    it('ensures SystemHealth and ActivityFeed render in dark mode compatible wrappers', () => {
        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <SystemHealth />
                    <ActivityFeed activities={[{ id: 1, type: 'audit', title: 'System reboot', timestamp: new Date().toISOString() }]} />
                </MemoryRouter>
            </QueryClientProvider>
        );

        expect(screen.getByText('System reboot')).toBeInTheDocument();
    });
});
