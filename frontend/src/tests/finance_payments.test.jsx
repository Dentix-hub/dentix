import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import PaymentsPage from '../features/finance/pages/PaymentsPage';
import PaymentDetailDrawer from '../features/finance/payments/components/PaymentDetailDrawer';
import RecordPaymentModal from '../features/finance/payments/components/RecordPaymentModal';
import * as billingApi from '../api/billing';
import * as patientsApi from '../api/patients';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

vi.mock('../features/finance/useFinancePermissions', () => ({
    useFinancePermissions: () => ({
        canReadFinance: true,
        canWriteFinance: true,
        canConfigFinance: true,
        isDoctor: false,
        isReceptionist: false,
    }),
}));

vi.mock('../api/billing', () => ({
    getPayments: vi.fn(),
    getAllPayments: vi.fn(),
    createPayment: vi.fn(),
    deletePayment: vi.fn(),
}));

vi.mock('../api/patients', () => ({
    getPatients: vi.fn(),
}));

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
}

const targetPayment = {
    id: 101,
    patient_id: 1,
    patient_name: 'أحمد علي',
    patient_file_number: 1,
    amount: 750,
    date: '2026-08-15T10:30:00',
    notes: 'دفعة جلسة تنظيف',
};

describe('Finance Payments V2 Components & Page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('<PaymentsPage />', () => {
        it('renders payments list, summary totals, and action buttons', async () => {
            billingApi.getPayments.mockResolvedValueOnce({
                data: {
                    data: [
                        targetPayment,
                        {
                            id: 102,
                            patient_id: 2,
                            patient_name: 'سارة محمد',
                            patient_file_number: 2,
                            amount: 1200,
                            date: '2026-08-15T11:00:00',
                            notes: 'دفعة تركيب تقويم',
                        },
                    ],
                },
            });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter>
                        <PaymentsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            expect(screen.getByText('سجل التحصيلات النقدية')).toBeDefined();
            expect(screen.getByText('تسجيل دفعة جديدة')).toBeDefined();

            await waitFor(() => {
                expect(screen.getAllByText('أحمد علي').length).toBeGreaterThan(0);
                expect(screen.getAllByText('سارة محمد').length).toBeGreaterThan(0);
            });

            expect(screen.getAllByLabelText('750 EGP').length).toBeGreaterThan(0);
            expect(screen.getAllByLabelText('1200 EGP').length).toBeGreaterThan(0);
        });

        it('honors patient and receipt deep-link filters and opens the exact receipt', async () => {
            billingApi.getPayments.mockResolvedValue({
                data: { data: [targetPayment] },
            });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter initialEntries={['/finance/payments?patient_id=1&payment_id=101&from=2026-08-01&to=2026-08-15']}>
                        <PaymentsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(billingApi.getPayments).toHaveBeenCalledWith(expect.objectContaining({
                    patient_id: 1,
                    payment_id: 101,
                    start_date: '2026-08-01',
                    end_date: '2026-08-15',
                    skip: 0,
                    limit: 21,
                }));
                expect(screen.getAllByText('#101').length).toBeGreaterThan(0);
            });
            expect(screen.getByText('patient #1')).toBeDefined();
            expect(screen.getByText('receipt #101')).toBeDefined();
            expect(screen.getAllByText('دفعة جلسة تنظيف').length).toBeGreaterThan(0);
        });

        it('renders empty state when no payments are returned', async () => {
            billingApi.getPayments.mockResolvedValueOnce({
                data: { data: [] },
            });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter>
                        <PaymentsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('لا توجد سندات تحصيل')).toBeDefined();
            });
        });
    });

    describe('<PaymentDetailDrawer />', () => {
        it('renders payment details and allows deletion when confirmed', async () => {
            const payment = {
                id: 45,
                patient_id: 10,
                patient_name: 'محمود حسن',
                patient_file_number: 1045,
                amount: 500,
                date: '2026-08-15T14:00:00',
                notes: 'سند قبض نقدي',
                doctor_name: 'طارق',
            };

            const onDelete = vi.fn().mockResolvedValue(true);
            const onClose = vi.fn();

            render(
                <MemoryRouter>
                    <PaymentDetailDrawer
                        payment={payment}
                        isOpen={true}
                        onClose={onClose}
                        onDelete={onDelete}
                    />
                </MemoryRouter>
            );

            expect(screen.getByText('#45')).toBeDefined();
            expect(screen.getByText('محمود حسن')).toBeDefined();
            expect(screen.getByLabelText('500 EGP')).toBeDefined();
            expect(screen.getByText('د. طارق')).toBeDefined();

            fireEvent.click(screen.getByText('حذف سند التحصيل'));
            expect(screen.getByText('تأكيد حذف سند التحصيل؟')).toBeDefined();
            fireEvent.click(screen.getByText('حذف'));

            await waitFor(() => {
                expect(onDelete).toHaveBeenCalledWith(45);
            });
        });
    });

    describe('<RecordPaymentModal />', () => {
        it('validates amount and calls onSubmit with correct payload', async () => {
            patientsApi.getPatients.mockResolvedValueOnce({
                data: {
                    data: [
                        { id: 1, name: 'خالد عمر', file_number: 201 },
                        { id: 2, name: 'منى جمال', file_number: 202 },
                    ],
                },
            });

            const onSubmit = vi.fn().mockResolvedValue(true);

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <RecordPaymentModal
                        isOpen={true}
                        initialPatientId={1}
                        onClose={vi.fn()}
                        onSubmit={onSubmit}
                    />
                </QueryClientProvider>
            );

            expect(screen.getByText('تسجيل دفعة مريض')).toBeDefined();
            await waitFor(() => expect(screen.getByText('خالد عمر (#201)')).toBeDefined());

            const select = screen.getByRole('combobox');
            expect(select.value).toBe('1');
            fireEvent.change(screen.getByPlaceholderText('0.00'), { target: { value: '650' } });
            fireEvent.change(
                screen.getByPlaceholderText('مثال: دفعة تحت حساب تقويم الأسنان / جلسة حشو...'),
                { target: { value: 'دفعة نقدية' } },
            );
            fireEvent.click(screen.getByText('تسجيل السند'));

            await waitFor(() => {
                expect(onSubmit).toHaveBeenCalledWith({
                    patient_id: 1,
                    amount: 650,
                    notes: 'دفعة نقدية',
                });
            });
        });
    });
});
