import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FinancePage from './FinancePage';
import {
    getSubscriptionPayments,
    getSubscriptionPlans,
    recordSubscriptionPayment,
    deleteSubscriptionPayment,
    api,
} from '@/api';
import { toast } from '@/shared/ui';

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
    getSubscriptionPayments: vi.fn(),
    getSubscriptionPlans: vi.fn(),
    recordSubscriptionPayment: vi.fn(),
    deleteSubscriptionPayment: vi.fn(),
    updateSubscriptionPlan: vi.fn(),
}));

vi.mock('@/shared/ui', async () => {
    const actual = await vi.importActual('@/shared/ui');
    return {
        ...actual,
        toast: {
            success: vi.fn(),
            error: vi.fn(),
        },
    };
});

describe('Manual Payment Flow MS-13', () => {
    const mockPayments = [
        {
            id: 1,
            tenant_id: 10,
            plan_id: 1,
            amount: 1500,
            payment_date: '2026-08-15',
            paid_by: 'dr_john',
            payment_method: 'cash',
        },
    ];

    const mockTenants = [
        { id: 10, name: 'Dental Care Clinic' },
        { id: 20, name: 'Apex Clinic' },
    ];

    const mockPlans = [
        { id: 1, name: 'Starter', display_name_ar: 'الأساسية', price: 1500 },
        { id: 2, name: 'Pro', display_name_ar: 'الاحترافية', price: 3000 },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        getSubscriptionPayments.mockResolvedValue({ data: mockPayments });
        getSubscriptionPlans.mockResolvedValue({ data: mockPlans });
        api.get.mockImplementation((url) => {
            if (url === '/api/v1/admin/tenants') {
                return Promise.resolve({ data: mockTenants });
            }
            if (url.includes('/users')) {
                return Promise.resolve({ data: { users: [{ id: 1, username: 'dr_john', role: 'manager' }] } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    it('renders FinancePage and validates required fields on payment modal submit', async () => {
        render(<FinancePage />);

        expect(await screen.findByText('Dental Care Clinic')).toBeInTheDocument();

        // Open payment modal
        fireEvent.click(screen.getByText('super_admin.payments.record_button'));
        expect(screen.getByText('super_admin.payments.modal_title')).toBeInTheDocument();

        // Try submit without selecting clinic
        fireEvent.click(screen.getByText('super_admin.payments.submit_button'));
        expect(toast.error).toHaveBeenCalledWith('super_admin.payments.error_select_tenant');
    });

    it('submits valid payment and updates data', async () => {
        recordSubscriptionPayment.mockResolvedValueOnce({ data: { success: true } });

        render(<FinancePage />);

        expect(await screen.findByText('Dental Care Clinic')).toBeInTheDocument();

        // Open modal
        fireEvent.click(screen.getByText('super_admin.payments.record_button'));

        // Select clinic
        const clinicSelect = screen.getByLabelText((content) => content.includes('super_admin.tenants.title') || content.includes('العيادة'));
        fireEvent.change(clinicSelect, { target: { value: '10' } });

        // Submit form
        fireEvent.click(screen.getByText('super_admin.payments.submit_button'));

        await waitFor(() => {
            expect(recordSubscriptionPayment).toHaveBeenCalledWith(expect.objectContaining({
                tenant_id: 10,
                plan_id: 1,
                amount: 1500,
            }));
            expect(toast.success).toHaveBeenCalledWith('super_admin.payments.success_recorded');
        });
    });

    it('opens confirm dialog on delete payment and performs deletion upon confirmation', async () => {
        deleteSubscriptionPayment.mockResolvedValueOnce({ data: { success: true } });

        render(<FinancePage />);

        expect(await screen.findByText('Dental Care Clinic')).toBeInTheDocument();

        // Click delete button on payment row
        const deleteBtn = screen.getByLabelText('super_admin.payments.delete_title');
        fireEvent.click(deleteBtn);

        // Confirm Dialog should appear
        expect(screen.getByText('super_admin.payments.delete_confirm_msg')).toBeInTheDocument();

        // Confirm deletion
        const confirmBtn = screen.getByRole('button', { name: 'common.delete' });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(deleteSubscriptionPayment).toHaveBeenCalledWith(1);
            expect(toast.success).toHaveBeenCalledWith('super_admin.payments.success_deleted');
        });
    });
});
