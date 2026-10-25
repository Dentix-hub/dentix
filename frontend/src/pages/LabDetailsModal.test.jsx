import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LabDetailsModal from './LabDetailsModal';
import * as api from '@/api';

vi.mock('@/api', () => ({
    getLabStats: vi.fn(),
    getLabOrders: vi.fn(),
    getLabPayments: vi.fn(),
    createLabPayment: vi.fn(),
}));

const translations = {
    'labs.details.tabs.overview': 'نظرة عامة',
    'labs.details.tabs.orders': 'الطلبات',
    'labs.details.tabs.payments': 'المعاملات المالية',
    'labs.details.overview.total_cost': 'إجمالي التكلفة',
    'labs.details.overview.paid': 'المدفوع',
    'labs.details.overview.balance': 'المستحق للمعمل (مديونية)',
    'labs.details.overview.clinic_credit': 'رصيد لصالح العيادة',
    'labs.details.orders.status_unpaid': 'غير مدفوع',
    'labs.details.orders.status_partial': 'جزئي',
    'labs.details.orders.status_paid': 'مدفوع',
    'labs.details.orders.status_cancelled': 'ملغي',
    'labs.details.orders.record_payment': 'تسجيل دفعة',
    'labs.details.payments.allocated_to_order': 'دفعة مخصصة للطلب',
    'labs.details.payments.clear_allocation': 'إلغاء التخصيص (على الحساب)',
    'labs.details.payments.on_account': 'على الحساب',
    'labs.details.payments.table.linked_order': 'الطلب المرتبط',
    'labs.details.payments.form.amount': 'المبلغ',
    'labs.details.payments.form.submit': 'تسجيل الدفعة',
    'labs.details.payments.add_button': 'إضافة دفعة',
};

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => translations[key] || (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

const mockLab = {
    id: 10,
    name: 'Al-Amal Dental Lab',
    total_cost: 1500,
    total_paid: 600,
    balance: 900,
};

const mockStats = {
    total_cost: 1500,
    total_paid: 600,
    balance: 900,
    total_orders: 4,
    status_counts: { pending: 1, in_progress: 1, completed: 1, cancelled: 1 },
};

const mockOrders = [
    {
        id: 101,
        order_date: '2026-10-10',
        patient_name: 'أحمد محمود',
        work_type: 'Crown Zirconia',
        tooth_number: '16',
        cost: 600,
        paid_amount: 200,
        remaining_amount: 400,
        payment_status: 'partial',
        status: 'in_progress',
    },
    {
        id: 102,
        order_date: '2026-10-12',
        patient_name: 'سارة علي',
        work_type: 'Bridge PFM',
        tooth_number: '21',
        cost: 500,
        paid_amount: 0,
        remaining_amount: 500,
        payment_status: 'unpaid',
        status: 'pending',
    },
    {
        id: 103,
        order_date: '2026-10-14',
        patient_name: 'محمد خالد',
        work_type: 'Inlay',
        tooth_number: '14',
        cost: 400,
        paid_amount: 400,
        remaining_amount: 0,
        payment_status: 'paid',
        status: 'completed',
    },
    {
        id: 104,
        order_date: '2026-10-15',
        patient_name: 'منى حسين',
        work_type: 'Veneer',
        tooth_number: '11',
        cost: 300,
        paid_amount: 0,
        remaining_amount: 0,
        payment_status: 'unpaid',
        status: 'cancelled',
    },
];

const mockPayments = [
    {
        id: 501,
        created_at: '2026-10-11T10:00:00Z',
        amount: 200,
        payment_method: 'Cash',
        lab_order_id: 101,
        notes: 'دفعة أولى للتاج',
    },
    {
        id: 502,
        created_at: '2026-10-13T12:00:00Z',
        amount: 400,
        payment_method: 'Bank Transfer',
        lab_order_id: null,
        notes: 'دفعة عامة على الحساب',
    },
];

describe('<LabDetailsModal /> (L4 frontend)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        api.getLabStats.mockResolvedValue({ data: mockStats });
        api.getLabOrders.mockResolvedValue({ data: mockOrders });
        api.getLabPayments.mockResolvedValue({ data: mockPayments });
        api.createLabPayment.mockResolvedValue({ data: { id: 503 } });
    });

    it('renders overview with positive balance labeled as المستحق للمعمل (مديونية)', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        expect(screen.getByText('Al-Amal Dental Lab')).toBeInTheDocument();
        expect(await screen.findByText('المستحق للمعمل (مديونية)')).toBeInTheDocument();
        expect(screen.getByText('900')).toBeInTheDocument();
    });

    it('renders overview with negative balance labeled as رصيد لصالح العيادة', async () => {
        const creditStats = {
            total_cost: 1000,
            total_paid: 1500,
            balance: -500,
            total_orders: 2,
            status_counts: {},
        };
        api.getLabStats.mockResolvedValueOnce({ data: creditStats });

        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={{ ...mockLab, balance: -500 }}
                onUpdate={vi.fn()}
            />
        );

        expect(await screen.findByText('رصيد لصالح العيادة')).toBeInTheDocument();
        expect(screen.getByText('500')).toBeInTheDocument();
    });

    it('displays orders table with cost, paid, remaining, and correct status chips', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        // Switch to Orders tab
        const ordersTabBtn = await screen.findByRole('button', { name: /الطلبات/i });
        fireEvent.click(ordersTabBtn);

        // Status chips
        expect(await screen.findByText('جزئي')).toBeInTheDocument();
        expect(screen.getByText('غير مدفوع')).toBeInTheDocument();
        expect(screen.getByText('مدفوع')).toBeInTheDocument();
        expect(screen.getByText('ملغي')).toBeInTheDocument();

        // Check cost/paid/remaining values
        expect(screen.getByText('600')).toBeInTheDocument();
        expect(screen.getByText('200')).toBeInTheDocument();
        expect(screen.getAllByText('400').length).toBeGreaterThanOrEqual(1);
    });

    it('clicking تسجيل دفعة on an order pre-allocates payment form with remaining amount and submits lab_order_id', async () => {
        const onUpdateMock = vi.fn();
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={onUpdateMock}
            />
        );

        // Switch to Orders tab
        const ordersTabBtn = await screen.findByRole('button', { name: /الطلبات/i });
        fireEvent.click(ordersTabBtn);

        // Click تسجيل دفعة on Order #101 (remaining 400)
        const payBtns = await screen.findAllByRole('button', { name: /تسجيل دفعة/i });
        fireEvent.click(payBtns[0]);

        // Should switch to Payments tab and open payment form with banner
        expect(await screen.findByText(/دفعة مخصصة للطلب/i)).toBeInTheDocument();
        expect(screen.getAllByText(/Crown Zirconia/i).length).toBeGreaterThan(0);

        // Amount input should default to remaining amount (400)
        const amountInput = screen.getByLabelText(/المبلغ/i);
        expect(amountInput.value).toBe('400');

        // Submit payment form
        const submitBtn = screen.getByRole('button', { name: /تسجيل الدفعة/i });
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(api.createLabPayment).toHaveBeenCalledTimes(1);
        });

        expect(api.createLabPayment).toHaveBeenCalledWith(10, expect.objectContaining({
            amount: 400,
            method: 'Cash',
            lab_order_id: 101,
        }));
    });

    it('displays linked order or على الحساب in payments table', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        // Switch to Payments tab
        const paymentsTabBtn = await screen.findByRole('button', { name: /المعاملات المالية/i });
        fireEvent.click(paymentsTabBtn);

        // Linked order display: Crown Zirconia (أحمد محمود)
        expect(await screen.findByText('Crown Zirconia (أحمد محمود)')).toBeInTheDocument();

        // Unallocated display: على الحساب
        expect(screen.getByText('على الحساب')).toBeInTheDocument();
    });
});
