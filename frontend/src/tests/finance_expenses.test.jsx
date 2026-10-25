import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import ExpensesPage from '../features/finance/pages/ExpensesPage';
import AddExpenseDrawer from '../features/finance/expenses/components/AddExpenseDrawer';
import DeleteExpenseModal from '../features/finance/expenses/components/DeleteExpenseModal';
import * as billingApi from '../api/billing';
import * as financialsApi from '../api/financials';

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
    getExpenses: vi.fn(),
    createExpense: vi.fn(),
    deleteExpense: vi.fn(),
}));

vi.mock('../api/financials', () => ({
    getFinanceSummary: vi.fn(),
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
                        source: 'manual_expense',
                        items: [
                            {
                                id: 1,
                                item_name: 'شراء قفازات وكمامات',
                                cost: 1200,
                                category: 'Supplies',
                                date: '2026-08-10',
                                notes: 'فاتورة رقم 450',
                                source: 'manual_expense',
                            },
                            {
                                id: 2,
                                item_name: 'فاتورة الكهرباء الشهرية',
                                cost: 850,
                                category: 'Utilities',
                                date: '2026-08-12',
                                source: 'manual_expense',
                            },
                        ],
                    },
                },
            });

            financialsApi.getFinanceSummary.mockResolvedValueOnce({
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
                    <MemoryRouter initialEntries={['/finance/expenses?from=2026-08-01&to=2026-08-31']}>
                        <ExpensesPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('المصروفات التشغيلية المباشرة')).toBeDefined();
                expect(screen.getByText('مدفوعات المعامل')).toBeDefined();
                expect(screen.getByText('مدفوعات المعامل تظهر في سجل المعاملات')).toBeDefined();
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
                        source: 'manual_expense',
                        items: [
                            {
                                id: 30,
                                item_name: 'مصروف الصفحة الثانية',
                                cost: 50,
                                source: 'manual_expense',
                            },
                        ],
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

        it('keeps Laboratory in category filter options for viewing historical expenses', async () => {
            billingApi.getExpenses.mockResolvedValueOnce({
                data: {
                    data: {
                        total: 0,
                        source: 'manual_expense',
                        items: [],
                    },
                },
            });
            financialsApi.getFinanceSummary.mockResolvedValueOnce({
                data: {
                    data: {
                        deductions: {
                            expenses: 0,
                            lab_costs: 0,
                            total_deductions: 0,
                        },
                    },
                },
            });

            const queryClient = createTestQueryClient();
            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter initialEntries={['/finance/expenses?from=2026-08-01&to=2026-08-31']}>
                        <ExpensesPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('تسجيل مصروف')).toBeDefined();
            });

            const labFilterOption = screen.queryByRole('option', { name: /معامل \(Laboratory\)/ });
            expect(labFilterOption).not.toBeNull();
            expect(labFilterOption?.value).toBe('Laboratory');
        });

        it('defaults to current month preset when date range is empty, fetches summary, and shows period scope badge (L5 fix)', async () => {
            billingApi.getExpenses.mockResolvedValueOnce({
                data: {
                    data: {
                        total: 1,
                        source: 'manual_expense',
                        items: [
                            {
                                id: 99,
                                item_name: 'شراء شاش طبي',
                                cost: 250,
                                category: 'Supplies',
                                date: '2026-10-25',
                                source: 'manual_expense',
                            },
                        ],
                    },
                },
            });

            financialsApi.getFinanceSummary.mockResolvedValueOnce({
                data: {
                    data: {
                        deductions: {
                            expenses: 250,
                            lab_costs: 100,
                            total_deductions: 350,
                        },
                    },
                },
            });

            const queryClient = createTestQueryClient();
            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter initialEntries={['/finance/expenses']}>
                        <ExpensesPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            // financialsApi.getFinanceSummary MUST be called even without query parameters
            await waitFor(() => {
                expect(financialsApi.getFinanceSummary).toHaveBeenCalled();
            });

            // Summary cards must display the real fetched amount (250), not 0
            await waitFor(() => {
                expect(screen.getAllByLabelText('250 EGP').length).toBeGreaterThan(0);
            });

            // Scope badge must reflect the period, not misleading all_time
            expect(screen.queryAllByText('الفترة المحددة').length).toBeGreaterThan(0);
            expect(screen.queryByText('الرصيد التراكمي (الكل)')).toBeNull();
        });
    });

    describe('<AddExpenseDrawer />', () => {
        it('validates required inputs and submits expense data', async () => {
            const onSubmit = vi.fn().mockResolvedValue({});
            const onClose = vi.fn();

            render(
                <MemoryRouter>
                    <AddExpenseDrawer
                        isOpen={true}
                        onClose={onClose}
                        onSubmit={onSubmit}
                        isSubmitting={false}
                    />
                </MemoryRouter>
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

        it('does not offer Laboratory category and shows a hint pointing to /labs (L3 guard)', () => {
            const onSubmit = vi.fn().mockResolvedValue({});
            const onClose = vi.fn();

            render(
                <MemoryRouter>
                    <AddExpenseDrawer
                        isOpen={true}
                        onClose={onClose}
                        onSubmit={onSubmit}
                        isSubmitting={false}
                    />
                </MemoryRouter>
            );

            // Verify Laboratory option is NOT in the category select
            const options = screen.getAllByRole('option');
            const optionValues = options.map((opt) => opt.value);
            expect(optionValues).not.toContain('Laboratory');
            expect(screen.queryByText(/معامل وتركيبات خارجية/)).toBeNull();

            // Verify hint text and link pointing to /labs
            expect(screen.getByText(/مدفوعات المعامل تتسجل من صفحة المعامل/)).toBeDefined();
            const labsLink = screen.getByRole('link', { name: /صفحة المعامل/ });
            expect(labsLink).toBeDefined();
            expect(labsLink.getAttribute('href')).toBe('/labs');
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
