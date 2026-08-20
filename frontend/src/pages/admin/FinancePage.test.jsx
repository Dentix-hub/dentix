import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiMocks = vi.hoisted(() => ({
    get: vi.fn(),
    getSubscriptionPayments: vi.fn(),
    getSubscriptionPlans: vi.fn(),
}));

vi.mock('@/api', () => ({
    api: { get: apiMocks.get },
    deleteSubscriptionPayment: vi.fn(),
    getSubscriptionPayments: apiMocks.getSubscriptionPayments,
    getSubscriptionPlans: apiMocks.getSubscriptionPlans,
    recordSubscriptionPayment: vi.fn(),
    updateSubscriptionPlan: vi.fn(),
}));

vi.mock('@/utils/logger', () => ({
    default: { error: vi.fn() },
}));

vi.mock('@/features/admin/SuperAdmin/PaymentsManager', () => ({
    default: () => <div>payments-manager</div>,
}));

vi.mock('@/features/admin/SuperAdmin/PlansManager', () => ({
    default: ({ plans }) => <div>{plans.map((plan) => plan.display_name_ar).join(',')}</div>,
}));

vi.mock('@/features/admin/SuperAdmin/ActiveSubscriptions', () => ({
    default: () => <div>active-subscriptions</div>,
}));

vi.mock('@/features/admin/SuperAdmin/FinanceReports', () => ({
    default: () => <div>finance-reports</div>,
}));

vi.mock('@/shared/ui', () => ({
    DateTimePicker: () => <input aria-label="payment-date" />,
    toast: { error: vi.fn(), success: vi.fn() },
}));

import FinancePage from './FinancePage';

describe('admin FinancePage data loading', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        apiMocks.get.mockResolvedValue({ data: [{ id: 9, name: 'Clinic' }] });
        apiMocks.getSubscriptionPlans.mockResolvedValue({
            data: [{ id: 3, display_name_ar: 'الخطة المحفوظة', price: 1500 }],
        });
    });

    it('keeps saved plans visible when subscription payments fail to load', async () => {
        apiMocks.getSubscriptionPayments.mockRejectedValue(new Error('payments unavailable'));

        render(<FinancePage />);

        await waitFor(() => expect(screen.queryByText('جاري تحميل البيانات المالية...')).not.toBeInTheDocument());
        fireEvent.click(screen.getByRole('button', { name: 'الخطط' }));

        expect(screen.getByText('الخطة المحفوظة')).toBeInTheDocument();
        expect(apiMocks.getSubscriptionPayments).toHaveBeenCalledTimes(1);
        expect(apiMocks.getSubscriptionPlans).toHaveBeenCalledTimes(1);
        expect(apiMocks.get).toHaveBeenCalledWith('/api/v1/admin/tenants');
    });
});
