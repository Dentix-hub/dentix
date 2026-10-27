import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import QuickTreatmentSheet from '../components/QuickTreatmentSheet';
import * as api from '@/api';

vi.mock('@/api', () => ({
    getQuickProcedures: vi.fn(),
    getPriceLists: vi.fn(),
    getQuickPriceLists: vi.fn(),
    getLaboratories: vi.fn(),
    getPatientDiagnosisHistory: vi.fn(),
    getMaterialEstimates: vi.fn(),
    createLabPayment: vi.fn(),
    getPatientTreatments: vi.fn(),
    getPatientLabOrders: vi.fn(),
    getPatientPayments: vi.fn(),
    createLabOrder: vi.fn(),
    updateLabOrder: vi.fn(),
    deleteLabOrder: vi.fn(),
}));

vi.mock('@/api/inventory', () => ({
    getStockSummary: vi.fn().mockResolvedValue({ data: [] }),
    getMaterials: vi.fn().mockResolvedValue({ data: [] }),
    getActiveSessions: vi.fn().mockResolvedValue({ data: [] }),
}));

vi.mock('@/shared/ui', () => ({
    toast: Object.assign(vi.fn(), {
        error: vi.fn(),
        success: vi.fn(),
        dismiss: vi.fn(),
    }),
}));

const mockLaboratories = [
    { id: 1, name: 'Dental Art Lab' },
    { id: 2, name: 'Apex Ceramics' },
];

const defaultInitialData = {
    id: 42,
    patient_id: 10,
    doctor_id: 2,
    tooth_number: '16',
    diagnosis: 'Caries',
    procedure: 'Crown Zirconia',
    cost: '1500',
    discount: '0',
    status: 'Done',
    notes: 'Lab crown preparation',
    consumedMaterials: [],
};

const procedures = [
    { id: 1, name: 'Crown Zirconia', category: 'prosthetics', price: 1500, suggestedMaterials: [] },
];

function renderSheet(overrides = {}) {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return render(
        <QueryClientProvider client={queryClient}>
            <QuickTreatmentSheet
                isOpen={true}
                onClose={vi.fn()}
                initialData={defaultInitialData}
                procedures={procedures}
                onSave={vi.fn().mockResolvedValue(undefined)}
                {...overrides}
            />
        </QueryClientProvider>
    );
}

describe('QuickTreatmentSheet Lab Cost & Payment UI (L4)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        api.getLaboratories.mockResolvedValue({ data: mockLaboratories });
        api.getPatientLabOrders.mockResolvedValue({ data: [] });
        api.createLabPayment.mockResolvedValue({ data: { id: 777 } });
    });

    it('requires an explicit choice and omits lab fields for in-clinic work', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        renderSheet({ isNativeWritesEnabled: true, onSave, procedures: [{ ...procedures[0], requires_lab: true }] });
        const select = await screen.findByLabelText(/quick_treatment_sheet.lab_select|اختر المعمل/i);
        const save = screen.getByTestId('quick-treatment-save-button');
        expect(save).toBeDisabled();
        fireEvent.change(select, { target: { value: 'in_clinic' } });
        expect(screen.queryByLabelText(/quick_treatment_sheet.lab_cost_label|تكلفة المعمل/i)).toBeNull();
        fireEvent.click(save);
        await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
        expect(onSave.mock.calls[0][0]).toMatchObject({ lab_choice: 'in_clinic', idempotency_key: expect.any(String) });
        expect(onSave.mock.calls[0][0].lab_order).toBeUndefined();
    });

    it('renders lab cost and shows paid_now only when cost > 0 with accounting note', async () => {
        renderSheet();

        // Lab Cost input exists
        const costInput = await screen.findByLabelText(/quick_treatment_sheet.lab_cost_label|تكلفة المعمل/i);
        expect(costInput).toBeInTheDocument();

        // paid_now input is not visible when cost is 0 / empty
        expect(screen.queryByLabelText(/quick_treatment_sheet.paid_now_label|دفعت الآن/i)).toBeNull();

        // Enter cost 600
        fireEvent.change(costInput, { target: { value: '600' } });

        // Now paid_now input is rendered
        const paidNowInput = await screen.findByLabelText(/quick_treatment_sheet.paid_now_label|دفعت الآن/i);
        expect(paidNowInput).toBeInTheDocument();

        // Accounting note is rendered
        expect(screen.getByText(/التكلفة بتتسجل مديونية على المعمل/i)).toBeInTheDocument();

        // Enter paid_now > cost (700) -> inline error
        fireEvent.change(paidNowInput, { target: { value: '700' } });
        expect(screen.getByText(/المبلغ المدفوع الآن لا يمكن أن يتجاوز تكلفة الطلب/i)).toBeInTheDocument();
    });

    it('renders read-only lab order details with payment status chip and records inline payment when linkedLabOrder exists', async () => {
        const mockLinkedOrder = {
            id: 88,
            treatment_id: 42,
            laboratory_id: 1,
            cost: 800,
            paid_amount: 300,
            remaining_amount: 500,
            payment_status: 'partial',
            status: 'in_progress',
        };

        api.getPatientLabOrders.mockResolvedValue({ data: [mockLinkedOrder] });

        renderSheet();

        // Verify both status chips rendered: order status + payment status
        expect(await screen.findByText('قيد التنفيذ')).toBeInTheDocument();
        expect(await screen.findByText('جزئي')).toBeInTheDocument();

        // Verify read-only values
        expect(screen.getByText('800')).toBeInTheDocument();
        expect(screen.getByText('300')).toBeInTheDocument();
        expect(screen.getByText('500')).toBeInTheDocument();

        // Click تسجيل دفعة button to toggle inline payment form
        const togglePayBtn = screen.getByRole('button', { name: /quick_treatment_sheet.record_payment|تسجيل دفعة/i });
        fireEvent.click(togglePayBtn);

        // Form appears: amount input pre-filled with remaining (500)
        const payAmountInput = await screen.findByLabelText(/labs.details.payments.form.amount|المبلغ/i);
        expect(payAmountInput.value).toBe('500');

        // Submit payment
        const submitPayBtn = screen.getByRole('button', { name: /تسجيل الدفعة|quick_treatment_sheet.record_payment/i });
        fireEvent.click(submitPayBtn);

        await waitFor(() => {
            expect(api.createLabPayment).toHaveBeenCalledTimes(1);
        });

        expect(api.createLabPayment).toHaveBeenCalledWith(1, expect.objectContaining({
            amount: 500,
            lab_order_id: 88,
        }));
    });
});
