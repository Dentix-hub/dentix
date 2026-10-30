import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LabDetailsModal from './LabDetailsModal';
import * as api from '@/api';

vi.mock('@/api', () => ({
    getLabStats: vi.fn(),
    getLabOrders: vi.fn(),
    getLabPayments: vi.fn(),
    createLabPayment: vi.fn(),
    allocateLabPayment: vi.fn(),
    deallocateLabPayment: vi.fn(),
}));

const translations = {
    'labs.details.tabs.overview': 'نظرة عامة',
    'labs.details.tabs.orders': 'الطلبات',
    'labs.details.tabs.payments': 'المعاملات المالية',
    'labs.details.overview.total_cost': 'إجمالي التكلفة',
    'labs.details.overview.paid': 'المدفوع',
    'labs.details.overview.balance': 'المستحق للمعمل (مديونية)',
    'labs.details.overview.clinic_credit': 'رصيد لصالح العيادة',
    'labs.details.overview.view_unallocated': 'عرض المدفوعات',
    'labs.details.overview.unallocated_alert': 'عندك دفعات على الحساب لسه ما اتربطتش بحالات: {{amount}}',
    'labs.details.orders.status_unpaid': 'غير مدفوع',
    'labs.details.orders.status_partial': 'جزئي',
    'labs.details.orders.status_paid': 'مدفوع',
    'labs.details.orders.status_cancelled': 'ملغي',
    'labs.details.orders.settle_remaining': 'سدّدت المتبقي',
    'labs.details.orders.partial_payment': 'دفعة جزئية',
    'labs.details.orders.settle_sheet.title': 'سداد المتبقي للطلب',
    'labs.details.orders.settle_sheet.confirm': 'تأكيد السداد',
    'labs.details.orders.settle_sheet.cancel': 'إلغاء',
    'labs.details.orders.settle_sheet.amount_label': 'المبلغ المسدد',
    'labs.details.orders.filter_all': 'كل الحالات',
    'labs.details.orders.filter_payment_all': 'كل حالات السداد',
    'labs.details.orders.filter_payment_unpaid': 'غير مدفوع',
    'labs.details.orders.filter_payment_partial': 'جزئي',
    'labs.details.orders.filter_payment_paid': 'مدفوع',
    'labs.details.payments.allocated_to_order': 'دفعة مخصصة للطلب',
    'labs.details.payments.clear_allocation': 'إلغاء التخصيص (على الحساب)',
    'labs.details.payments.on_account': 'على الحساب',
    'labs.details.payments.title': 'سجل المدفوعات',
    'labs.details.payments.allocate_button': 'ربط بطلب',
    'labs.details.payments.deallocate_button': 'إلغاء الربط',
    'labs.details.payments.table.linked_order': 'الطلب المرتبط',
    'labs.details.payments.form.order_label': 'الطلب',
    'labs.details.payments.form.unallocated_option': 'على الحساب (غير مخصص)',
    'labs.details.payments.form.amount': 'المبلغ',
    'labs.details.payments.form.submit': 'تسجيل الدفعة',
    'labs.details.payments.add_button': 'إضافة دفعة',
    'labs.details.payments.allocate_modal.title': 'ربط الدفعة بطلب معمل',
    'labs.details.payments.allocate_modal.select_order_label': 'اختر الطلب المراد ربط الدفعة به',
    'labs.details.payments.allocate_modal.confirm': 'تأكيد الربط',
    'labs.details.payments.messages.overpay': 'المبلغ المدفوع يتجاوز المتبقي للطلب',
};

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback, options) => {
            let str = translations[key] || (typeof fallback === 'string' ? fallback : key);
            if (options && typeof options === 'object') {
                Object.keys(options).forEach(k => {
                    str = str.replace(`{{${k}}}`, options[k]);
                });
            }
            return str;
        },
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
    unallocated_payments_total: 400,
    unallocated_payments_count: 1,
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
        method: 'Cash',
        lab_order_id: 101,
        notes: 'دفعة أولى للتاج',
    },
    {
        id: 502,
        created_at: '2026-10-13T12:00:00Z',
        amount: 400,
        method: 'Bank Transfer',
        lab_order_id: null,
        notes: 'دفعة عامة على الحساب',
    },
];

describe('<LabDetailsModal /> (PR-2 mobile settlement UX)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        api.getLabStats.mockResolvedValue({ data: mockStats });
        api.getLabOrders.mockResolvedValue({ data: mockOrders });
        api.getLabPayments.mockResolvedValue({ data: mockPayments });
        api.createLabPayment.mockResolvedValue({ data: { id: 503 } });
        api.allocateLabPayment.mockResolvedValue({ data: { status: 'allocated' } });
        api.deallocateLabPayment.mockResolvedValue({ data: { status: 'deallocated' } });
    });

    it('renders overview with unallocated banner when unallocated_payments_total > 0 and clicking it opens payments', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        expect(screen.getByText('Al-Amal Dental Lab')).toBeInTheDocument();
        expect(await screen.findByTestId('unallocated-banner')).toBeInTheDocument();
        expect(screen.getByText(/عندك دفعات على الحساب لسه ما اتربطتش بحالات: 400/i)).toBeInTheDocument();

        // Clicking عرض المدفوعات switches to payments tab
        const viewPaymentsBtn = screen.getByRole('button', { name: /عرض المدفوعات/i });
        fireEvent.click(viewPaymentsBtn);

        expect(await screen.findByText('سجل المدفوعات')).toBeInTheDocument();
    });

    it('does not render unallocated banner when unallocated_payments_total is 0', async () => {
        api.getLabStats.mockResolvedValueOnce({
            data: { ...mockStats, unallocated_payments_total: 0, unallocated_payments_count: 0 },
        });

        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        await screen.findByText('Al-Amal Dental Lab');
        expect(screen.queryByTestId('unallocated-banner')).not.toBeInTheDocument();
    });

    it('renders mobile cards container and displays both سدّدت المتبقي and دفعة جزئية buttons', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        const ordersTabBtn = await screen.findByRole('button', { name: /الطلبات/i });
        fireEvent.click(ordersTabBtn);

        // Mobile cards container
        expect(await screen.findByTestId('orders-cards-mobile')).toBeInTheDocument();

        // Cards contain both buttons
        const settleBtns = screen.getAllByRole('button', { name: /سدّدت المتبقي/i });
        const partialBtns = screen.getAllByRole('button', { name: /دفعة جزئية/i });

        expect(settleBtns.length).toBeGreaterThanOrEqual(1);
        expect(partialBtns.length).toBeGreaterThanOrEqual(1);

        // Status chips
        expect(screen.getAllByText('جزئي').length).toBeGreaterThan(0);
        expect(screen.getAllByText('غير مدفوع').length).toBeGreaterThan(0);
        expect(screen.getAllByText('مدفوع').length).toBeGreaterThan(0);
        expect(screen.getAllByText('ملغي').length).toBeGreaterThan(0);
    });

    it('one-tap settle opens settle sheet pre-filled with remaining and posts lab_order_id and amount', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        const ordersTabBtn = await screen.findByRole('button', { name: /الطلبات/i });
        fireEvent.click(ordersTabBtn);

        // Click سدّدت المتبقي for Order #101 (remaining 400)
        const settleBtns = await screen.findAllByRole('button', { name: /سدّدت المتبقي/i });
        fireEvent.click(settleBtns[0]);

        // Settle sheet opens
        expect(await screen.findByText('سداد المتبقي للطلب')).toBeInTheDocument();
        expect(screen.getByText('Crown Zirconia — أحمد محمود')).toBeInTheDocument();
        expect(screen.getAllByText('400').length).toBeGreaterThan(0);

        // Confirm settlement
        const confirmBtn = screen.getByRole('button', { name: /تأكيد السداد/i });
        fireEvent.click(confirmBtn);

        await waitFor(() => {
            expect(api.createLabPayment).toHaveBeenCalledTimes(1);
        });

        expect(api.createLabPayment).toHaveBeenCalledWith(10, {
            amount: 400,
            method: 'Cash',
            notes: undefined,
            lab_order_id: 101,
        });
    });

    it('clicking دفعة جزئية opens payment form with pre-filled order and remaining amount', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        const ordersTabBtn = await screen.findByRole('button', { name: /الطلبات/i });
        fireEvent.click(ordersTabBtn);

        // Click دفعة جزئية on Order #101
        const partialBtns = await screen.findAllByRole('button', { name: /دفعة جزئية/i });
        fireEvent.click(partialBtns[0]);

        // Form opens on payments tab
        expect(await screen.findByText(/دفعة مخصصة للطلب/i)).toBeInTheDocument();
        const amountInput = screen.getByLabelText(/المبلغ/i);
        expect(amountInput.value).toBe('400');

        const orderSelect = screen.getByLabelText(/الطلب/i);
        expect(orderSelect.value).toBe('101');
    });

    it('order select in payment form excludes cancelled and fully-paid orders, and validates remaining', async () => {
        window.alert = vi.fn();
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        const paymentsTabBtn = await screen.findByRole('button', { name: /المعاملات المالية/i });
        fireEvent.click(paymentsTabBtn);

        const addBtn = screen.getByRole('button', { name: /إضافة دفعة/i });
        fireEvent.click(addBtn);

        const orderSelect = screen.getByLabelText(/الطلب/i);
        // Eligible options should be unallocated + Order 101 (remaining 400) + Order 102 (remaining 500)
        // 103 (paid, remaining 0) and 104 (cancelled) should NOT be listed
        expect(orderSelect.querySelector('option[value="101"]')).toBeInTheDocument();
        expect(orderSelect.querySelector('option[value="102"]')).toBeInTheDocument();
        expect(orderSelect.querySelector('option[value="103"]')).toBeNull();
        expect(orderSelect.querySelector('option[value="104"]')).toBeNull();

        // Selecting order 102 pre-fills amount with 500
        fireEvent.change(orderSelect, { target: { value: '102' } });
        const amountInput = screen.getByLabelText(/المبلغ/i);
        expect(amountInput.value).toBe('500');

        // Entering amount > 500 triggers overpay validation
        fireEvent.change(amountInput, { target: { value: '600' } });
        const submitBtn = screen.getByRole('button', { name: /تسجيل الدفعة/i });
        fireEvent.click(submitBtn);

        expect(window.alert).toHaveBeenCalledWith(expect.stringMatching(/المبلغ المدفوع يتجاوز المتبقي للطلب/i));
        expect(api.createLabPayment).not.toHaveBeenCalled();
    });

    it('renders payments tab cards below md with ربط بطلب for unallocated and إلغاء الربط for linked', async () => {
        window.confirm = vi.fn(() => true);
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        const paymentsTabBtn = await screen.findByRole('button', { name: /المعاملات المالية/i });
        fireEvent.click(paymentsTabBtn);

        // Mobile container
        expect(await screen.findByTestId('payments-cards-mobile')).toBeInTheDocument();

        // Linked payment shows إلغاء الربط
        const unlinkBtns = screen.getAllByRole('button', { name: /إلغاء الربط/i });
        expect(unlinkBtns.length).toBeGreaterThanOrEqual(1);

        // Unallocated payment shows ربط بطلب
        const linkBtns = screen.getAllByRole('button', { name: /ربط بطلب/i });
        expect(linkBtns.length).toBeGreaterThanOrEqual(1);

        // Test إلغاء الربط calls deallocateLabPayment
        fireEvent.click(unlinkBtns[0]);
        expect(window.confirm).toHaveBeenCalled();
        expect(api.deallocateLabPayment).toHaveBeenCalledWith(10, 501);

        // Test ربط بطلب opens allocate modal
        fireEvent.click(linkBtns[0]);
        expect(await screen.findByText('ربط الدفعة بطلب معمل')).toBeInTheDocument();

        // Order 101 remaining is 400, Order 102 remaining is 500 (both >= payment amount 400)
        const modalSelect = screen.getByLabelText(/اختر الطلب المراد ربط الدفعة به/i);
        expect(modalSelect.querySelector('option[value="101"]')).toBeInTheDocument();
        expect(modalSelect.querySelector('option[value="102"]')).toBeInTheDocument();

        fireEvent.change(modalSelect, { target: { value: '101' } });
        const confirmAllocateBtn = screen.getByRole('button', { name: /تأكيد الربط/i });
        fireEvent.click(confirmAllocateBtn);

        await waitFor(() => {
            expect(api.allocateLabPayment).toHaveBeenCalledWith(10, 502, 101);
        });
    });

    it('filters orders by payment status', async () => {
        render(
            <LabDetailsModal
                isOpen={true}
                onClose={vi.fn()}
                lab={mockLab}
                onUpdate={vi.fn()}
            />
        );

        const ordersTabBtn = await screen.findByRole('button', { name: /الطلبات/i });
        fireEvent.click(ordersTabBtn);

        const paymentFilter = screen.getByLabelText(/كل حالات السداد/i);

        // Filter to 'paid'
        await waitFor(() => {
            fireEvent.change(paymentFilter, { target: { value: 'paid' } });
        });
        expect(screen.getAllByText('Inlay').length).toBeGreaterThanOrEqual(1);
        expect(screen.queryByText('Crown Zirconia')).toBeNull();
        expect(screen.queryByText('Bridge PFM')).toBeNull();

        // Filter to 'partial'
        await waitFor(() => {
            fireEvent.change(paymentFilter, { target: { value: 'partial' } });
        });
        expect(screen.getAllByText('Crown Zirconia').length).toBeGreaterThanOrEqual(1);
        expect(screen.queryByText('Inlay')).toBeNull();
        expect(screen.queryByText('Bridge PFM')).toBeNull();
    });
});
