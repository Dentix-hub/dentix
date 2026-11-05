import { webcrypto } from 'node:crypto';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FinancePage from './FinancePage';
import {
    getSubscriptionPayments,
    getSubscriptionPlans,
    recordSubscriptionPayment,
    previewSubscriptionPayment,
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
    previewSubscriptionPayment: vi.fn(),
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

Object.defineProperty(globalThis.crypto, 'subtle', { value: webcrypto.subtle, configurable: true });

beforeEach(() => {
    previewSubscriptionPayment.mockResolvedValue({ data: { data: {
        amount: '400.00', currency: 'EGP', preview_marker: 'a'.repeat(64),
        before: { subscription_end_date: '2027-01-31T10:00:00', plan_id: 1 },
        after: { subscription_end_date: '2027-02-28T10:00:00', plan_id: 1 },
    } } });
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

    it('previews exact dates and requires confirmation before recording a receipt', async () => {
        render(<FinancePage />);
        await screen.findByText('Dental Care Clinic');
        fireEvent.click(screen.getByText('super_admin.payments.record_button'));
        fireEvent.change(screen.getByLabelText((label) => label.includes('super_admin.tenants.title') || label.includes('العيادة')), { target: { value: '10' } });
        fireEvent.click(screen.getByText('super_admin.payments.submit_button'));
        await waitFor(() => expect(previewSubscriptionPayment).toHaveBeenCalled());
        expect(recordSubscriptionPayment).not.toHaveBeenCalled();
        expect(await screen.findByText(/2027-01-31/)).toBeInTheDocument();
        expect(screen.getByText(/2027-02-28/)).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'common.confirm' }));
        await waitFor(() => expect(recordSubscriptionPayment).toHaveBeenCalledWith(expect.objectContaining({ preview_marker: 'a'.repeat(64) })));
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

        fireEvent.click(await screen.findByRole('button', { name: 'common.confirm' }));
        await waitFor(() => {
            expect(recordSubscriptionPayment).toHaveBeenCalledWith(expect.objectContaining({
                tenant_id: 10,
                plan_id: 1,
                amount: 1500,
            }));
            expect(toast.success).toHaveBeenCalledWith('super_admin.payments.success_recorded');
        });
    });

    it('preserves finalized receipts without offering destructive deletion', async () => {
        render(<FinancePage />);
        expect(await screen.findByText('Dental Care Clinic')).toBeInTheDocument();
        expect(screen.queryByLabelText('super_admin.payments.delete_title')).not.toBeInTheDocument();
        expect(deleteSubscriptionPayment).not.toHaveBeenCalled();
    });
});

it('reuses the manual receipt identity after a lost response and reload', async () => {
    vi.clearAllMocks();
    sessionStorage.clear();
    getSubscriptionPayments.mockResolvedValue({ data: [] });
    getSubscriptionPlans.mockResolvedValue({ data: [{ id: 1, name: 'professional', price: 400 }] });
    api.get.mockImplementation(async (url) => ({ data: url.includes('/users') ? { users: [] } : [{ id: 10, name: 'Synthetic retry clinic' }] }));
    recordSubscriptionPayment.mockRejectedValueOnce(new Error('Lost response')).mockResolvedValueOnce({ data: {} });
    const page = render(<FinancePage />);
    await screen.findByText('super_admin.payments.record_button');
    fireEvent.click(screen.getByText('super_admin.payments.record_button'));
    fireEvent.change(screen.getByLabelText((label) => label.includes('super_admin.tenants.title') || label.includes('العيادة')), { target: { value: '10' } });
    fireEvent.click(screen.getByText('super_admin.payments.submit_button'));
    fireEvent.click(await screen.findByRole('button', { name: 'common.confirm' }));
    await waitFor(() => expect(recordSubscriptionPayment).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText('super_admin.payments.submit_button')).not.toBeDisabled());
    page.unmount();
    render(<FinancePage />);
    await screen.findByText('super_admin.payments.record_button');
    fireEvent.click(screen.getByText('super_admin.payments.record_button'));
    fireEvent.change(screen.getByLabelText((label) => label.includes('super_admin.tenants.title') || label.includes('العيادة')), { target: { value: '10' } });
    fireEvent.click(screen.getByText('super_admin.payments.submit_button'));
    fireEvent.click(await screen.findByRole('button', { name: 'common.confirm' }));
    await waitFor(() => expect(recordSubscriptionPayment.mock.calls.length).toBeGreaterThan(1));
    const calls = recordSubscriptionPayment.mock.calls.slice(-2);
    expect(calls[0][0].idempotency_key).toBeTruthy();
    expect(calls[1][0].idempotency_key).toBe(calls[0][0].idempotency_key);
});
