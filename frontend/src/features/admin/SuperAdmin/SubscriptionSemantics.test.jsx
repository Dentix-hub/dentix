import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TenantsManager from './TenantsManager';
import ActiveSubscriptions from './ActiveSubscriptions';
import DashboardStats from './DashboardStats';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar' },
    }),
}));

describe('Subscription Status Semantics MS-10', () => {
    const mockPlans = [
        { id: 1, name: 'Basic', display_name_ar: 'الأساسية', price: 200 },
        { id: 2, name: 'Pro', display_name_ar: 'الاحترافية', price: 500 },
    ];

    const mockTenants = [
        {
            id: 1,
            name: 'Active Future Clinic',
            is_active: true,
            is_deleted: false,
            subscription_end_date: '2026-12-31',
            plan_id: 1,
        },
        {
            id: 2,
            name: 'Expired Past Clinic',
            is_active: true,
            is_deleted: false,
            subscription_end_date: '2026-01-01',
            plan_id: 2,
        },
        {
            id: 3,
            name: 'Archived Clinic',
            is_active: true,
            is_deleted: true,
            subscription_end_date: '2026-12-31',
            plan_id: 1,
        },
    ];

    const mockGetDays = (date) => {
        if (!date) return null;
        return date === '2026-12-31' ? 120 : -10;
    };

    it('renders consistent status across TenantsManager', () => {
        render(
            <TenantsManager
                tenants={mockTenants}
                plans={mockPlans}
                handlePlanChange={vi.fn()}
                getDaysRemaining={mockGetDays}
                handleArchiveTenant={vi.fn()}
                handleRestoreTenant={vi.fn()}
                handlePermanentDelete={vi.fn()}
            />
        );

        expect(screen.getByText('super_admin.tenants.active')).toBeInTheDocument();
        expect(screen.getByText('super_admin.tenants.inactive')).toBeInTheDocument();
        expect(screen.getAllByText('super_admin.tenants.archived').length).toBeGreaterThanOrEqual(1);
    });

    it('renders consistent status across ActiveSubscriptions', () => {
        render(
            <ActiveSubscriptions
                tenants={mockTenants}
                plans={mockPlans}
                getDaysRemaining={mockGetDays}
            />
        );

        expect(screen.getByText('common.active')).toBeInTheDocument();
        expect(screen.getByText('common.expired')).toBeInTheDocument();
        expect(screen.getByText('super_admin.tenants.archived')).toBeInTheDocument();
    });

    it('renders DashboardStats with operational KPI counts', () => {
        const stats = {
            total_tenants: 4,
            active_tenants: 2,
            expired_tenants: 1,
            total_revenue: 15000,
        };

        render(<DashboardStats stats={stats} />);

        expect(screen.getByText('4')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument();
        expect(screen.getByText('1')).toBeInTheDocument();
        expect(screen.getByText('15,000 super_admin.finance.currency')).toBeInTheDocument();
    });
});
