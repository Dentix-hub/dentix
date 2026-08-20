import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import DoctorCompensationPage from '../features/finance/pages/DoctorCompensationPage';
import DoctorDetailPage from '../features/finance/pages/DoctorDetailPage';
import DoctorCompensationEquation from '../features/finance/compensation/components/DoctorCompensationEquation';
import DoctorSettingsDrawer from '../features/finance/compensation/components/DoctorSettingsDrawer';
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

// Mock financials APIs
vi.mock('../api/financials', () => ({
    getDoctorRevenue: vi.fn(),
    getDoctorDetails: vi.fn(),
    updateDoctorCompensation: vi.fn(),
}));

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
}

describe('Finance Doctor Compensation V2', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('<DoctorCompensationPage />', () => {
        it('renders doctor compensation overview and table with authoritative calculations', async () => {
            financialsApi.getDoctorRevenue.mockResolvedValue({
                data: {
                    data: {
                        doctors: [
                            {
                                doctor_id: 10,
                                doctor_name: 'د. كريم الشريف',
                                treatments: 15,
                                gross_cost: 20000,
                                patient_discount: 2000,
                                revenue: 18000,
                                collected: 15000,
                                lab_cost: 3000,
                                net_revenue: 15000,
                                commission_base: 12000,
                                commission_percent: 40,
                                commission_amount: 4800,
                                fixed_salary: 2000,
                                total_due: 6800,
                            },
                        ],
                    },
                },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter>
                        <DoctorCompensationPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('إجمالي مستحقات الأطباء')).toBeDefined();
                expect(screen.getAllByText('د. كريم الشريف').length).toBeGreaterThan(0);
            });

            expect(screen.getAllByLabelText('6800 EGP').length).toBeGreaterThan(0);
            expect(screen.getAllByLabelText('15000 EGP').length).toBeGreaterThan(0);
            expect(screen.getAllByLabelText('3000 EGP').length).toBeGreaterThan(0);
            expect(screen.getAllByText(/40% عمولة/).length).toBeGreaterThan(0);
        });
    });

    describe('<DoctorCompensationEquation />', () => {
        it('renders visual mathematical equation explaining doctor entitlement derivation', () => {
            render(
                <DoctorCompensationEquation
                    collected={10000}
                    labCost={2000}
                    commissionPercent={30}
                    fixedSalary={1500}
                    totalDue={3900}
                />
            );

            expect(screen.getByText('معادلة احتساب مستحقات الطبيب للفترة')).toBeDefined();
            expect(screen.getByLabelText('10000 EGP')).toBeDefined();
            expect(screen.getByLabelText('2000 EGP')).toBeDefined();
            expect(screen.getByLabelText('2400 EGP')).toBeDefined();
            expect(screen.getByLabelText('1500 EGP')).toBeDefined();
            expect(screen.getByLabelText('3900 EGP')).toBeDefined();
        });
    });

    describe('<DoctorDetailPage />', () => {
        it('renders routed doctor details with equation, treatments and lab breakdown', async () => {
            financialsApi.getDoctorDetails.mockResolvedValueOnce({
                data: {
                    data: {
                        doctor_id: 10,
                        doctor_name: 'د. سارة عادل',
                        commission_percent: 35,
                        fixed_salary: 3000,
                        revenue: 25000,
                        collected: 20000,
                        lab_cost: 4000,
                        commission_base: 16000,
                        commission_amount: 5600,
                        total_due: 8600,
                        treatments: [
                            {
                                id: 101,
                                date: '2026-08-05',
                                procedure: 'حشو عصب جراحي',
                                cost: 2500,
                                discount: 200,
                                net: 2300,
                                patient_name: 'محمد خالد',
                            },
                        ],
                        lab_orders: [
                            {
                                id: 201,
                                date: '2026-08-06',
                                work_type: 'تركيبة زيركون',
                                cost: 1200,
                                patient_name: 'محمد خالد',
                            },
                        ],
                    },
                },
            });

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter initialEntries={['/finance/compensation/doctors/10']}>
                        <Routes>
                            <Route path="/finance/compensation/doctors/:doctorId" element={<DoctorDetailPage />} />
                        </Routes>
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('د. سارة عادل')).toBeDefined();
                expect(screen.getByText('حشو عصب جراحي')).toBeDefined();
                expect(screen.getByText('محمد خالد')).toBeDefined();
            });

            expect(screen.getAllByLabelText('8600 EGP').length).toBeGreaterThan(0);
        });
    });

    describe('<DoctorSettingsDrawer />', () => {
        it('submits updated compensation rules when configured by authorized staff', async () => {
            const onSave = vi.fn().mockResolvedValue({});
            const onClose = vi.fn();
            const doctor = {
                doctor_id: 10,
                doctor_name: 'د. أحمد سمير',
                commission_percent: 30,
                fixed_salary: 2000,
            };

            render(
                <DoctorSettingsDrawer
                    doctor={doctor}
                    isOpen={true}
                    onClose={onClose}
                    onSave={onSave}
                    isSaving={false}
                />
            );

            expect(screen.getByText('إعدادات أتعاب الطبيب')).toBeDefined();
            expect(screen.getByText('د. أحمد سمير')).toBeDefined();

            const commInput = screen.getByDisplayValue('30');
            fireEvent.change(commInput, { target: { value: '45' } });

            const saveBtn = screen.getByText('حفظ التعديلات');
            fireEvent.click(saveBtn);

            await waitFor(() => {
                expect(onSave).toHaveBeenCalledWith({
                    commission_percent: 45,
                    fixed_salary: 2000,
                    per_appointment_fee: 0,
                });
            });
        });
    });
});
