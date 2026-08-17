import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import PaymentsPage from '../features/finance/pages/PaymentsPage';
import PaymentDetailDrawer from '../features/finance/payments/components/PaymentDetailDrawer';
import RecordPaymentModal from '../features/finance/payments/components/RecordPaymentModal';
import * as billingApi from '../api/billing';
import * as patientsApi from '../api/patients';

// Mock react-i18next
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'ar' },
    }),
}));

// Mock permissions hook
vi.mock('../features/finance/useFinancePermissions', () => ({
    useFinancePermissions: () => ({
        canReadFinance: true,
        canWriteFinance: true,
        canConfigFinance: true,
        isDoctor: false,
        isReceptionist: false,
    }),
}));

// Mock billing and patients APIs
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

describe('Finance Payments V2 Components & Page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('<PaymentsPage />', () => {
        it('renders payments list, summary totals, and action buttons', async () => {
            const mockPayments = [
                {
                    id: 101,
                    patient_id: 1,
                    patient_name: 'أحمد علي',
                    patient_file_number: 1001,
                    amount: 750,
                    date: '2026-08-15T10:30:00',
                    notes: 'دفعة جلسة تنظيف',
                },
                {
                    id: 102,
                    patient_id: 2,
                    patient_name: 'سارة محمد',
                    patient_file_number: 1002,
                    amount: 1200,
                    date: '2026-08-15T11:00:00',
                    notes: 'دفعة تركيب تقويم',
                },
            ];

            billingApi.getPayments.mockResolvedValueOnce({
                data: { data: mockPayments },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
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

        it('renders empty state when no payments are returned', async () => {
            billingApi.getPayments.mockResolvedValueOnce({
                data: { data: [] },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
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

            // Click delete button to open confirm prompt
            const deleteBtn = screen.getByText('حذف سند التحصيل');
            fireEvent.click(deleteBtn);

            expect(screen.getByText('تأكيد حذف سند التحصيل؟')).toBeDefined();

            // Confirm deletion
            const confirmBtn = screen.getByText('حذف');
            fireEvent.click(confirmBtn);

            await waitFor(() => {
                expect(onDelete).toHaveBeenCalledWith(45);
            });
        });
    });

    describe('<RecordPaymentModal />', () => {
        it('validates amount and calls onSubmit with correct payload', async () => {
            const mockPatients = [
                { id: 1, name: 'خالد عمر', file_number: 201 },
                { id: 2, name: 'منى جمال', file_number: 202 },
            ];

            patientsApi.getPatients.mockResolvedValueOnce({
                data: { data: mockPatients },
            });

            const onSubmit = vi.fn().mockResolvedValue(true);
            const onClose = vi.fn();
            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <RecordPaymentModal
                        isOpen={true}
                        onClose={onClose}
                        onSubmit={onSubmit}
                    />
                </QueryClientProvider>
            );

            expect(screen.getByText('تسجيل دفعة مريض')).toBeDefined();

            await waitFor(() => {
                expect(screen.getByText('خالد عمر (#201)')).toBeDefined();
            });

            // Select patient and enter amount
            const select = screen.getByRole('combobox');
            fireEvent.change(select, { target: { value: '1' } });

            const amountInput = screen.getByPlaceholderText('0.00');
            fireEvent.change(amountInput, { target: { value: '650' } });

            const notesInput = screen.getByPlaceholderText('مثال: دفعة تحت حساب تقويم الأسنان / جلسة حشو...');
            fireEvent.change(notesInput, { target: { value: 'دفعة نقدية' } });

            // Submit form
            const submitBtn = screen.getByText('تسجيل السند');
            fireEvent.click(submitBtn);

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
