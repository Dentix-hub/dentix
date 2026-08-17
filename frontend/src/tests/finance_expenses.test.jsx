import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import ExpensesPage from '../features/finance/pages/ExpensesPage';
import AddExpenseDrawer from '../features/finance/expenses/components/AddExpenseDrawer';
import DeleteExpenseModal from '../features/finance/expenses/components/DeleteExpenseModal';
import * as billingApi from '../api/billing';
import * as financialsApi from '../api/financials';

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

// Mock billing & financials APIs
vi.mock('../api/billing', () => ({
    getExpenses: vi.fn(),
    createExpense: vi.fn(),
    deleteExpense: vi.fn(),
}));

vi.mock('../api/financials', () => ({
    getComprehensiveStats: vi.fn(),
}));

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
}

describe('Finance Expenses V2', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('<ExpensesPage />', () => {
        it('renders expense list, provenance badge, and summary metrics', async () => {
            billingApi.getExpenses.mockResolvedValueOnce({
                data: {
                    data: {
                        total: 30,
                        items: [
                        {
                            id: 1,
                            item_name: 'شراء قفازات وكمامات',
                            cost: 1200,
                            category: 'Supplies',
                            date: '2026-08-10',
                            notes: 'فاتورة رقم 450',
                        },
                        {
                            id: 2,
                            item_name: 'فاتورة الكهرباء الشهرية',
                            cost: 850,
                            category: 'Utilities',
                            date: '2026-08-12',
                        },
                        ],
                    },
                },
            });

            financialsApi.getComprehensiveStats.mockResolvedValueOnce({
                data: {
                    data: {
                        deductions: {
                            expenses: 2050,
                            lab_costs: 1500,
                            total_deductions: 3550,
                        },
                    },
                },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter>
                        <ExpensesPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('المصروفات التشغيلية المباشرة')).toBeDefined();
                expect(screen.getByText('تكاليف المعامل والتركيبات')).toBeDefined();
                expect(screen.getAllByText('شراء قفازات وكمامات').length).toBeGreaterThan(0);
                expect(screen.getAllByText('فاتورة الكهرباء الشهرية').length).toBeGreaterThan(0);
            });

            expect(screen.getAllByLabelText('1200 EGP').length).toBeGreaterThan(0);
            expect(screen.getAllByText('يدوي').length).toBeGreaterThan(0);
            expect(screen.getByText('تسجيل مصروف')).toBeDefined();
            expect(screen.getByLabelText('الصفحة التالية')).toBeDefined();

            billingApi.getExpenses.mockResolvedValueOnce({
                data: {
                    data: {
                        total: 30,
                        items: [{ id: 30, item_name: 'مصروف الصفحة الثانية', cost: 50 }],
                    },
                },
            });
            fireEvent.click(screen.getByLabelText('الصفحة التالية'));

            await waitFor(() => {
                expect(billingApi.getExpenses).toHaveBeenLastCalledWith(expect.objectContaining({
                    skip: 25,
                    limit: 25,
                }));
                expect(screen.getAllByText('مصروف الصفحة الثانية').length).toBeGreaterThan(0);
            });
        });
    });

    describe('<AddExpenseDrawer />', () => {
        it('validates required inputs and submits expense data', async () => {
            const onSubmit = vi.fn().mockResolvedValue({});
            const onClose = vi.fn();

            render(
                <AddExpenseDrawer
                    isOpen={true}
                    onClose={onClose}
                    onSubmit={onSubmit}
                    isSubmitting={false}
                />
            );

            expect(screen.getByText('تسجيل مصروف جديد')).toBeDefined();

            const itemInput = screen.getByPlaceholderText(/شراء مواد تخدير/);
            const costInput = screen.getByPlaceholderText('0.00');

            fireEvent.change(itemInput, { target: { value: 'صيانة جهاز الأشعة' } });
            fireEvent.change(costInput, { target: { value: '450' } });

            const submitBtn = screen.getByText('حفظ المصروف');
            fireEvent.click(submitBtn);

            await waitFor(() => {
                expect(onSubmit).toHaveBeenCalledWith(
                    expect.objectContaining({
                        item_name: 'صيانة جهاز الأشعة',
                        cost: 450,
                        category: 'Supplies',
                    })
                );
            });
        });
    });

    describe('<DeleteExpenseModal />', () => {
        it('shows explicit expense identity and warns of financial impact', () => {
            const expense = {
                id: 10,
                item_name: 'إيجار العيادة لشهر أغسطس',
                cost: 15000,
                category: 'Rent',
            };

            const onConfirm = vi.fn();
            const onClose = vi.fn();

            render(
                <DeleteExpenseModal
                    expense={expense}
                    isOpen={true}
                    onClose={onClose}
                    onConfirm={onConfirm}
                />
            );

            expect(screen.getByText('تأكيد حذف المصروف')).toBeDefined();
            expect(screen.getByText('إيجار العيادة لشهر أغسطس')).toBeDefined();
            expect(screen.getByLabelText('15000 EGP')).toBeDefined();
            expect(screen.getByText(/سيؤدي حذف هذا المصروف إلى خفض إجمالي المصروفات/)).toBeDefined();

            const confirmBtn = screen.getByText('حذف المصروف نهائياً');
            fireEvent.click(confirmBtn);

            expect(onConfirm).toHaveBeenCalledWith(10);
        });
    });
});
