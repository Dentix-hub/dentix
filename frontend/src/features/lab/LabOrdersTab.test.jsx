import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LabOrdersTab from './LabOrdersTab';
import * as api from '@/api';
import { toast } from '@/shared/ui';

vi.mock('@/api', () => ({
    getPatientLabOrders: vi.fn(),
    getLaboratories: vi.fn(),
    getPatientTreatments: vi.fn(),
    createLabOrder: vi.fn(),
    updateLabOrder: vi.fn(),
    deleteLabOrder: vi.fn(),
}));

vi.mock('@/shared/ui', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn(),
        info: vi.fn(),
    },
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
    }),
}));

const mockLabs = [
    { id: 1, name: 'Dental Art Lab' },
    { id: 2, name: 'Apex Ceramics' },
];

const mockTreatments = [
    { id: 42, procedure: 'Crown PFM', tooth_number: 16 },
    { id: 43, procedure: 'Composite Filling', tooth_number: 14 },
];

describe('LabOrdersTab (D2, D3, Step 6)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        api.getPatientLabOrders.mockResolvedValue({ data: [] });
        api.getLaboratories.mockResolvedValue({ data: mockLabs });
        api.getPatientTreatments.mockResolvedValue({ data: mockTreatments });
        api.createLabOrder.mockResolvedValue({ data: { id: 101 } });
    });

    it('displays treatment link dropdown in new lab order modal and auto-fills tooth and work_type', async () => {
        render(<LabOrdersTab patientId={12} treatments={mockTreatments} />);

        // Click Add Lab Order
        const addBtn = await screen.findByRole('button', { name: /add_empty|إضافة/i });
        fireEvent.click(addBtn);

        // Check treatment link select exists
        const treatmentSelect = await screen.findByLabelText(/ربط بإجراء علاجي/i);
        expect(treatmentSelect).toBeInTheDocument();
        expect(screen.getByText(/#42 — Crown PFM/i)).toBeInTheDocument();

        // Select Treatment #42
        fireEvent.change(treatmentSelect, { target: { value: '42' } });

        // Tooth number should be auto-filled to "16"
        const toothInput = screen.getByPlaceholderText(/tooth_placeholder/i);
        expect(toothInput.value).toBe('16');

        // Select laboratory
        const labSelect = screen.getAllByRole('combobox').find(select => select.required && select.value === '');
        fireEvent.change(labSelect, { target: { value: '1' } });

        // Save lab order
        const saveBtn = screen.getByRole('button', { name: /save_add/i });
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.createLabOrder).toHaveBeenCalledTimes(1);
        });

        expect(api.createLabOrder).toHaveBeenCalledWith(expect.objectContaining({
            patient_id: 12,
            treatment_id: 42,
            laboratory_id: 1,
            tooth_number: '16',
            work_type: 'Crown PFM',
            price_to_patient: 0,
        }));
    });

    it('allows unlinked lab orders when treatment link is left empty', async () => {
        render(<LabOrdersTab patientId={12} treatments={mockTreatments} />);

        const addBtn = await screen.findByRole('button', { name: /add_empty|إضافة/i });
        fireEvent.click(addBtn);

        // Select laboratory and manual work type
        const labSelects = screen.getAllByRole('combobox');
        const labSelect = labSelects[1]; // second combobox is laboratory_id
        fireEvent.change(labSelect, { target: { value: '2' } });

        const workTypeSelect = labSelects[2]; // third combobox is work_type
        fireEvent.change(workTypeSelect, { target: { value: 'Crown' } });

        const toothInput = screen.getByPlaceholderText(/tooth_placeholder/i);
        fireEvent.change(toothInput, { target: { value: '21' } });

        const saveBtn = screen.getByRole('button', { name: /save_add/i });
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.createLabOrder).toHaveBeenCalledTimes(1);
        });

        expect(api.createLabOrder).toHaveBeenCalledWith(expect.objectContaining({
            patient_id: 12,
            laboratory_id: 2,
            tooth_number: '21',
            work_type: 'Crown',
        }));
        expect(api.createLabOrder.mock.calls[0][0].treatment_id).toBeUndefined();
    });

    it('shows paid_now input only when cost > 0, validates paid_now <= cost, and sends paid_now in payload', async () => {
        const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
        render(<LabOrdersTab patientId={12} treatments={mockTreatments} />);

        const addBtn = await screen.findByRole('button', { name: /add_empty|إضافة/i });
        fireEvent.click(addBtn);

        // Initially with cost 0, paid_now input is not visible
        expect(screen.queryByLabelText(/دفعت الآن للمعمل/i)).toBeNull();

        // Select lab & work type
        const labSelects = screen.getAllByRole('combobox');
        fireEvent.change(labSelects[1], { target: { value: '1' } });
        fireEvent.change(labSelects[2], { target: { value: 'Crown' } });

        // Enter cost 500
        const costInputs = screen.getAllByPlaceholderText('0');
        const costInput = costInputs[0];
        fireEvent.change(costInput, { target: { value: '500' } });

        // Now paid_now input is rendered
        const paidNowInput = screen.getByLabelText(/دفعت الآن للمعمل/i);
        expect(paidNowInput).toBeInTheDocument();

        // Enter paid_now > cost (600) -> inline warning + toast + modal error without blocking alert
        fireEvent.change(paidNowInput, { target: { value: '600' } });
        expect(screen.getAllByText(/المبلغ المدفوع الآن لا يمكن أن يتجاوز تكلفة الطلب/i).length).toBeGreaterThanOrEqual(1);

        // Try submitting -> blocked via non-blocking toast + inline error, never window.alert
        const saveBtn = screen.getByRole('button', { name: /save_add/i });
        fireEvent.click(saveBtn);
        expect(alertSpy).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalledWith(
            expect.stringContaining('المبلغ المدفوع الآن لا يمكن أن يتجاوز')
        );
        expect(screen.getByTestId('lab-order-modal-error')).toHaveTextContent(
            /المبلغ المدفوع الآن لا يمكن أن يتجاوز/i
        );
        expect(api.createLabOrder).not.toHaveBeenCalled();

        // Fix paid_now to 200 and submit
        fireEvent.change(paidNowInput, { target: { value: '200' } });
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.createLabOrder).toHaveBeenCalledTimes(1);
        });
        expect(api.createLabOrder).toHaveBeenCalledWith(expect.objectContaining({
            cost: 500,
            paid_now: 200,
        }));
        alertSpy.mockRestore();
    });

    it('renders linked bilingual treatment procedure in work_type select and handles 422 without blocking alert', async () => {
        const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
        const arabicTreatments = [
            { id: 88, procedure: 'تاج زيركون – Zirconia Crown', tooth_number: 16 },
            { id: 89, procedure: 'جسر ثابت', tooth_number: 24, lab_choice: 'in_clinic' },
        ];
        api.createLabOrder.mockRejectedValueOnce({
            response: {
                status: 422,
                data: { detail: 'إجراء طلب المعمل لا يطابق العلاج' },
            },
        });

        render(<LabOrdersTab patientId={12} treatments={arabicTreatments} />);

        const addBtn = await screen.findByRole('button', { name: /add_empty|إضافة/i });
        fireEvent.click(addBtn);

        // in_clinic treatment should not appear in treatment link options
        expect(screen.queryByText(/#89 — جسر ثابت/)).toBeNull();

        const treatmentSelect = await screen.findByLabelText(/ربط بإجراء علاجي/i);
        fireEvent.change(treatmentSelect, { target: { value: '88' } });

        const workTypeSelect = screen.getAllByRole('combobox')[2];
        expect(workTypeSelect.value).toBe('تاج زيركون – Zirconia Crown');

        fireEvent.change(screen.getAllByRole('combobox')[1], { target: { value: '1' } });
        const saveBtn = screen.getByRole('button', { name: /save_add/i });
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.createLabOrder).toHaveBeenCalledTimes(1);
        });
        expect(alertSpy).not.toHaveBeenCalled();
        expect(await screen.findByTestId('lab-order-modal-error')).toHaveTextContent(
            'إجراء طلب المعمل لا يطابق العلاج'
        );
        expect(toast.error).toHaveBeenCalledWith('إجراء طلب المعمل لا يطابق العلاج');

        // Retry succeeds cleanly without hanging
        fireEvent.click(saveBtn);
        await waitFor(() => {
            expect(api.createLabOrder).toHaveBeenCalledTimes(2);
        });
        alertSpy.mockRestore();
    });

    it('renders payment status chips and sums lab cost (not price_to_patient) excluding cancelled orders', async () => {
        const mockOrders = [
            {
                id: 101,
                order_date: '2026-10-01',
                laboratory_name: 'Dental Art Lab',
                work_type: 'Crown',
                tooth_number: '16',
                shade: 'A2',
                status: 'in_progress',
                payment_status: 'unpaid',
                cost: 600,
                paid_amount: 0,
                price_to_patient: 1200,
            },
            {
                id: 102,
                order_date: '2026-10-02',
                laboratory_name: 'Apex Ceramics',
                work_type: 'Bridge',
                tooth_number: '21',
                shade: 'A1',
                status: 'completed',
                payment_status: 'partial',
                cost: 800,
                paid_amount: 300,
                price_to_patient: 1800,
            },
            {
                id: 103,
                order_date: '2026-10-03',
                laboratory_name: 'Dental Art Lab',
                work_type: 'Inlay',
                tooth_number: '14',
                shade: 'B1',
                status: 'completed',
                payment_status: 'paid',
                cost: 400,
                paid_amount: 400,
                price_to_patient: 900,
            },
            {
                id: 104,
                order_date: '2026-10-04',
                laboratory_name: 'Apex Ceramics',
                work_type: 'Veneer',
                tooth_number: '11',
                shade: 'BL1',
                status: 'cancelled',
                cost: 500,
                paid_amount: 0,
                price_to_patient: 1500,
            },
        ];

        api.getPatientLabOrders.mockResolvedValueOnce({ data: mockOrders });
        render(<LabOrdersTab patientId={12} treatments={mockTreatments} />);

        expect(await screen.findByText('غير مدفوع')).toBeInTheDocument();
        expect(screen.getByText('جزئي')).toBeInTheDocument();
        expect(screen.getByText('مدفوع')).toBeInTheDocument();
        expect(screen.getAllByText('ملغي').length).toBeGreaterThan(0);

        // Bug 5: prosthetics_cost stat card must show lab cost sum (600 + 800 + 400 = 1800), not price_to_patient
        expect(screen.getByTestId('lab-orders-prosthetics-cost')).toHaveTextContent('1800');

        // Check cost and paid values rendered
        expect(screen.getByText('600')).toBeInTheDocument();
        expect(screen.getByText('800')).toBeInTheDocument();
        expect(screen.getByText('300')).toBeInTheDocument();
        expect(screen.getAllByText('400').length).toBeGreaterThanOrEqual(1);
    });
});
