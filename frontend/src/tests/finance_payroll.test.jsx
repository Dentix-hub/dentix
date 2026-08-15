import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import PayrollPage from '../features/finance/pages/PayrollPage';
import MonthPicker from '../features/finance/payroll/components/MonthPicker';
import SalaryPaymentDrawer from '../features/finance/payroll/components/SalaryPaymentDrawer';
import StaffSettingsDrawer from '../features/finance/payroll/components/StaffSettingsDrawer';
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
        isAdmin: true,
        isAccountant: false,
    }),
}));

// Mock financials APIs
vi.mock('../api/financials', () => ({
    getSalariesStatus: vi.fn(),
    recordSalaryPayment: vi.fn(),
    deleteSalaryPayment: vi.fn(),
    updateStaffCompensation: vi.fn(),
    updateHireDate: vi.fn(),
}));

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
}

describe('Finance Payroll V2', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('<PayrollPage />', () => {
        it('renders monthly payroll summary cards, employee list, and status badges', async () => {
            financialsApi.getSalariesStatus.mockResolvedValue({
                data: {
                    data: {
                        month: '2026-08',
                        employees: [
                            {
                                id: 1,
                                username: 'أحمد محمود',
                                role: 'receptionist',
                                base_salary: 5000,
                                days_in_month: 31,
                                is_new_this_month: false,
                                days_worked: 31,
                                prorated_salary: 5000,
                                hire_date: '2025-01-01',
                                payment: {
                                    id: 10,
                                    amount: 5000,
                                    payment_date: '2026-08-01',
                                    is_partial: false,
                                    notes: 'راتب شهر أغسطس',
                                },
                                is_paid: true,
                            },
                            {
                                id: 2,
                                username: 'مروة علي',
                                role: 'nurse',
                                base_salary: 4000,
                                days_in_month: 31,
                                is_new_this_month: true,
                                days_worked: 15,
                                prorated_salary: 1935.48,
                                hire_date: '2026-08-17',
                                payment: null,
                                is_paid: false,
                            },
                        ],
                    },
                },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter initialEntries={['/finance/compensation/payroll?month=2026-08']}>
                        <PayrollPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('إجمالي الرواتب المستحقة')).toBeDefined();
                expect(screen.getAllByText('أحمد محمود').length).toBeGreaterThan(0);
                expect(screen.getAllByText('مروة علي').length).toBeGreaterThan(0);
            });

            expect(screen.getAllByText('مسدد بالكامل').length).toBeGreaterThan(0);
            expect(screen.getAllByText('غير مسدد').length).toBeGreaterThan(0);
        });

        it('uses cumulative paid and remaining amounts in the mobile payroll card', async () => {
            financialsApi.getSalariesStatus.mockResolvedValue({
                data: {
                    data: {
                        employees: [{
                            id: 3,
                            username: 'موظف متعدد الدفعات',
                            role: 'assistant',
                            prorated_salary: 5000,
                            payable_amount: 5000,
                            paid_amount: 5000,
                            remaining_amount: 0,
                            status: 'paid',
                            payment: { id: 12, amount: 3000, is_partial: false },
                        }],
                    },
                },
            });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter initialEntries={['/finance/compensation/payroll?month=2026-08']}>
                        <PayrollPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => expect(screen.getAllByText('موظف متعدد الدفعات').length).toBeGreaterThan(0));
            expect(screen.getAllByLabelText('5000 EGP').length).toBeGreaterThan(1);
            expect(screen.queryByLabelText('3000 EGP')).toBeNull();
        });
    });

    describe('<MonthPicker />', () => {
        it('navigates to previous and next month correctly', () => {
            const onChange = vi.fn();
            render(<MonthPicker month="2026-08" onChange={onChange} />);

            const prevBtn = screen.getByTitle('الشهر السابق');
            fireEvent.click(prevBtn);
            expect(onChange).toHaveBeenCalledWith('2026-07');

            const nextBtn = screen.getByTitle('الشهر التالي');
            fireEvent.click(nextBtn);
            expect(onChange).toHaveBeenCalledWith('2026-09');
        });
    });

    describe('<SalaryPaymentDrawer />', () => {
        it('submits salary payment payload with partial flag and notes', async () => {
            const onSave = vi.fn().mockResolvedValue({});
            const onClose = vi.fn();

            const employee = {
                id: 2,
                username: 'مروة علي',
                role: 'nurse',
                prorated_salary: 4000,
                days_worked: 30,
                payment: null,
            };

            render(
                <SalaryPaymentDrawer
                    employee={employee}
                    month="2026-08"
                    isOpen={true}
                    onClose={onClose}
                    onSave={onSave}
                    isSaving={false}
                />
            );

            expect(screen.getByText('صرف راتب الموظف')).toBeDefined();
            expect(screen.getByText(/مروة علي/)).toBeDefined();

            const amountInput = screen.getByDisplayValue('4000');
            fireEvent.change(amountInput, { target: { value: '2000' } });

            const partialCheckbox = screen.getByLabelText(/دفعة جزئية/);
            fireEvent.click(partialCheckbox);

            const notesInput = screen.getByPlaceholderText(/سلفة، مكافأة/);
            fireEvent.change(notesInput, { target: { value: 'سلفة منتصف الشهر' } });

            const confirmBtn = screen.getByText('تأكيد تسجيل الصرف');
            fireEvent.click(confirmBtn);

            await waitFor(() => {
                expect(onSave).toHaveBeenCalledWith({
                    userId: 2,
                    amount: 2000,
                    isPartial: true,
                    daysWorked: 30,
                    notes: 'سلفة منتصف الشهر',
                });
            });
        });
    });

    describe('<StaffSettingsDrawer />', () => {
        it('submits updated salary and hire date rules when configured', async () => {
            const onSave = vi.fn().mockResolvedValue({});
            const onClose = vi.fn();

            const employee = {
                id: 2,
                username: 'مروة علي',
                role: 'nurse',
                base_salary: 4000,
                hire_date: '2026-01-15',
            };

            render(
                <StaffSettingsDrawer
                    employee={employee}
                    isOpen={true}
                    onClose={onClose}
                    onSave={onSave}
                    isSaving={false}
                />
            );

            expect(screen.getByText('قواعد راتب الموظف')).toBeDefined();
            expect(screen.getByText(/مروة علي/)).toBeDefined();

            const salaryInput = screen.getByDisplayValue('4000');
            fireEvent.change(salaryInput, { target: { value: '5500' } });

            const saveBtn = screen.getByText('حفظ التعديلات');
            fireEvent.click(saveBtn);

            await waitFor(() => {
                expect(onSave).toHaveBeenCalledWith({
                    userId: 2,
                    salary: 5500,
                    hireDate: '2026-01-15',
                });
            });
        });
    });
});
