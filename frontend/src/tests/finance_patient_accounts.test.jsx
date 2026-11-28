import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import PatientAccountsPage from '../features/finance/pages/PatientAccountsPage';
import PatientStatementDrawer from '../features/finance/patient-accounts/components/PatientStatementDrawer';
import { queryKeys } from '../lib/queryClient';
import * as billingApi from '../api/billing';
import * as financialsApi from '../api/financials';
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

vi.mock('../api/financials', () => ({
    getPatientsReport: vi.fn(),
    getFinanceSummary: vi.fn(),
    getPatientReportDetails: vi.fn(),
}));

vi.mock('../api/billing', () => ({
    createPayment: vi.fn(),
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

const accountRow = {
    patient_id: 7,
    file_number: 7,
    patient_name: 'يوسف محمود',
    patient_phone: '01234567890',
    total_invoiced: 6000,
    total_paid: 4500,
    all_time_outstanding: 1500,
};

const statementPayload = {
    patient_id: 7,
    file_number: 7,
    patient_name: 'يوسف محمود',
    patient_phone: '01234567890',
    total_invoiced: 2000,
    total_paid: 500,
    period_balance: 1500,
    payment_history: [
        { id: 71, date: '2026-08-10T10:00:00', amount: 500, notes: 'دفعة الفترة' },
    ],
    treatment_history: [
        { id: 72, date: '2026-08-08T10:00:00', procedure: 'Crown', diagnosis: 'Missing tooth', cost: 2200, discount: 200, net: 2000 },
    ],
};

describe('Finance Patient Accounts & Receivables V2', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        financialsApi.getFinanceSummary.mockResolvedValue({
            data: { data: { income: { all_time_outstanding: 85000 } } },
        });
    });

    describe('<PatientAccountsPage />', () => {
        it('renders headline debt summary and paginated patient accounts table', async () => {
            financialsApi.getPatientsReport.mockResolvedValueOnce({
                data: {
                    data: {
                        total: 2,
                        patients: [
                            {
                                patient_id: 1,
                                file_number: 101,
                                patient_name: 'طارق علي',
                                patient_phone: '01012345678',
                                total_invoiced: 5000,
                                total_paid: 3000,
                                outstanding_balance: 2000,
                                all_time_outstanding: 2000,
                            },
                            {
                                patient_id: 2,
                                file_number: 102,
                                patient_name: 'فاطمة أحمد',
                                patient_phone: '01198765432',
                                total_invoiced: 4000,
                                total_paid: 4000,
                                outstanding_balance: 0,
                                all_time_outstanding: 0,
                            },
                        ],
                    },
                },
            });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter>
                        <PatientAccountsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('إجمالي الديون التراكمية على المرضى')).toBeDefined();
                expect(screen.getAllByText('طارق علي').length).toBeGreaterThan(0);
                expect(screen.getAllByText('فاطمة أحمد').length).toBeGreaterThan(0);
            });
            expect(screen.getAllByLabelText('2000 EGP').length).toBeGreaterThan(0);
            expect(screen.getByText('المدينون فقط')).toBeDefined();
        });

        it('opens a direct patientId route and loads the real period statement', async () => {
            financialsApi.getPatientsReport.mockImplementation(async (params) => ({
                data: {
                    data: params?.patient_id
                        ? { total: 1, patients: [accountRow] }
                        : { total: 1, patients: [accountRow] },
                },
            }));
            financialsApi.getPatientReportDetails.mockResolvedValue({
                data: { data: statementPayload },
            });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter initialEntries={['/finance/patient-accounts/7?from=2026-08-01&to=2026-08-15']}>
                        <Routes>
                            <Route path="/finance/patient-accounts/:patientId" element={<PatientAccountsPage />} />
                        </Routes>
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('دفعة الفترة')).toBeDefined();
                expect(screen.getByText('Crown')).toBeDefined();
                expect(screen.getByText('2026-08-01 – 2026-08-15')).toBeDefined();
            });
            expect(financialsApi.getPatientReportDetails).toHaveBeenCalledWith(7, {
                start_date: '2026-08-01',
                end_date: '2026-08-15',
            });
            expect(financialsApi.getPatientsReport).toHaveBeenCalledWith(expect.objectContaining({
                patient_id: 7,
                skip: 0,
                limit: 1,
            }));
            expect(screen.getAllByLabelText('1500 EGP').length).toBeGreaterThan(0);
        });

        it('normalizes a file_number URL filter to the explicit patient_id server filter', async () => {
            financialsApi.getPatientsReport.mockResolvedValue({
                data: { data: { total: 1, patients: [accountRow] } },
            });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter initialEntries={['/finance/patient-accounts?file_number=7']}>
                        <PatientAccountsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(financialsApi.getPatientsReport).toHaveBeenCalledWith(expect.objectContaining({
                    patient_id: 7,
                }));
            });
        });

        it('uses summary.total_outstanding directly even if getFinanceSummary fails and displays account count without currency', async () => {
            financialsApi.getPatientsReport.mockResolvedValueOnce({
                data: {
                    data: {
                        total: 3,
                        summary: { total_outstanding: 4250 },
                        patients: [
                            { ...accountRow, patient_id: 1, all_time_outstanding: 1500 },
                            { ...accountRow, patient_id: 2, all_time_outstanding: 2500 },
                            { ...accountRow, patient_id: 3, all_time_outstanding: 250 },
                        ],
                    },
                },
            });
            financialsApi.getFinanceSummary.mockRejectedValueOnce({ response: { status: 403 } });

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter>
                        <PatientAccountsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByLabelText('4250 EGP')).toBeInTheDocument();
            });
            const countMetric = screen.getByLabelText('3');
            expect(countMetric).toBeInTheDocument();
            expect(countMetric.textContent).not.toMatch(/EGP|جنيه|ج\.م/);
        });

        it('invalidates patient and dashboardStats queries when recording a payment from PatientAccountsPage', async () => {
            financialsApi.getPatientsReport.mockResolvedValue({
                data: {
                    data: {
                        total: 1,
                        summary: { total_outstanding: 1500 },
                        patients: [accountRow],
                    },
                },
            });
            patientsApi.getPatients.mockResolvedValue({
                data: { data: [{ id: 7, name: 'يوسف محمود', file_number: 7 }] },
            });
            billingApi.createPayment.mockResolvedValue({ data: { data: { id: 888 } } });

            const queryClient = createTestQueryClient();
            const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter>
                        <PatientAccountsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => expect(screen.getAllByText('يوسف محمود').length).toBeGreaterThan(0));
            fireEvent.click(screen.getByTitle('تسجيل دفعة'));

            await waitFor(() => expect(screen.getByText('يوسف محمود (#7)')).toBeInTheDocument());
            fireEvent.change(screen.getByPlaceholderText('0.00'), { target: { value: '500' } });
            fireEvent.click(screen.getByText('تسجيل السند'));

            await waitFor(() => {
                expect(billingApi.createPayment).toHaveBeenCalledWith({
                    patient_id: 7,
                    amount: 500,
                    notes: undefined,
                });
            });

            expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: queryKeys.dashboardStats }));
            const predicateCall = invalidateSpy.mock.calls
                .map(([arg]) => arg)
                .find((arg) => typeof arg?.predicate === 'function');
            expect(predicateCall).toBeDefined();
            expect(predicateCall.predicate({ queryKey: ['patient', 7, 'payments'] })).toBe(true);
            expect(predicateCall.predicate({ queryKey: ['finance'] })).toBe(false);
        });
    });

    describe('<PatientStatementDrawer />', () => {
        it('renders server statement history in the canonical drawer and triggers record payment callback', async () => {
            financialsApi.getPatientsReport.mockResolvedValue({
                data: { data: { total: 1, patients: [accountRow] } },
            });
            financialsApi.getPatientReportDetails.mockResolvedValue({
                data: { data: statementPayload },
            });
            const onRecordPayment = vi.fn();

            render(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoryRouter>
                        <PatientStatementDrawer
                            patient={accountRow}
                            patientId={7}
                            from="2026-08-01"
                            to="2026-08-15"
                            isOpen={true}
                            onClose={vi.fn()}
                            onRecordPayment={onRecordPayment}
                        />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => expect(screen.getByText('دفعة الفترة')).toBeDefined());
            expect(screen.getByText('يوسف محمود')).toBeDefined();
            expect(screen.getByText('01234567890')).toBeDefined();
            expect(screen.getAllByLabelText('1500 EGP').length).toBeGreaterThan(0);
            expect(document.querySelector('[data-dentix-overlay="drawer"]')).not.toBeNull();
            expect(document.querySelector('[data-dentix-overlay="backdrop"]')).not.toBeNull();
            expect(screen.getByTestId('patient-statement-panel')).toBeDefined();

            fireEvent.click(screen.getByText('تسجيل دفعة لهذا المريض'));
            expect(onRecordPayment).toHaveBeenCalledWith(expect.objectContaining({ patient_id: 7 }));
        });
    });
});
