import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import PatientAccountsPage from '../features/finance/pages/PatientAccountsPage';
import PatientStatementDrawer from '../features/finance/patient-accounts/components/PatientStatementDrawer';
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

vi.mock('../api/financials', () => ({
    getPatientsReport: vi.fn(),
    getFinanceSummary: vi.fn(),
}));

vi.mock('../api/billing', () => ({
    createPayment: vi.fn(),
}));

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
}

describe('Finance Patient Accounts & Receivables V2', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('<PatientAccountsPage />', () => {
        it('renders headline debt summary and paginated patient accounts table', async () => {
            financialsApi.getFinanceSummary.mockResolvedValueOnce({
                data: {
                    data: {
                        income: {
                            all_time_outstanding: 85000,
                        },
                    },
                },
            });

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

            const queryClient = createTestQueryClient();

            render(
                <QueryClientProvider client={queryClient}>
                    <MemoryRouter>
                        <PatientAccountsPage />
                    </MemoryRouter>
                </QueryClientProvider>
            );

            await waitFor(() => {
                expect(screen.getByText('إجمالي الديون التراكمية على المرضى')).toBeDefined();
                expect(screen.getByText('إجمالي حسابات المرضى المالية')).toBeDefined();
                expect(screen.getAllByText('طارق علي').length).toBeGreaterThan(0);
                expect(screen.getAllByText('فاطمة أحمد').length).toBeGreaterThan(0);
            });

            await waitFor(() => {
                expect(financialsApi.getFinanceSummary).toHaveBeenCalled();
            });
            const [statsFrom, statsTo] = financialsApi.getFinanceSummary.mock.calls[0];
            expect(statsFrom).toMatch(/^\d{4}-\d{2}-\d{2}$/);
            expect(statsTo).toMatch(/^\d{4}-\d{2}-\d{2}$/);
            expect(statsFrom).not.toBe('');
            expect(statsTo).not.toBe('');

            expect(screen.getAllByLabelText('2000 EGP').length).toBeGreaterThan(0);
            expect(screen.getByText('المدينون فقط')).toBeDefined();
        });
    });

    describe('<PatientStatementDrawer />', () => {
        it('renders patient debt breakdown and triggers record payment callback', () => {
            const patient = {
                patient_id: 1,
                file_number: 101,
                patient_name: 'يوسف محمود',
                patient_phone: '01234567890',
                total_invoiced: 6000,
                total_paid: 4500,
                all_time_outstanding: 1500,
            };

            const onRecordPayment = vi.fn();
            const onClose = vi.fn();

            render(
                <MemoryRouter>
                    <PatientStatementDrawer
                        patient={patient}
                        isOpen={true}
                        onClose={onClose}
                        onRecordPayment={onRecordPayment}
                    />
                </MemoryRouter>
            );

            expect(screen.getByText('#101')).toBeDefined();
            expect(screen.getByText('يوسف محمود')).toBeDefined();
            expect(screen.getByText('01234567890')).toBeDefined();
            expect(screen.getByLabelText('1500 EGP')).toBeDefined();
            expect(screen.getByLabelText('6000 EGP')).toBeDefined();
            expect(screen.getByLabelText('4500 EGP')).toBeDefined();

            const panel = screen.getByTestId('patient-statement-panel');
            expect(panel.className).toContain('bg-white');
            expect(panel.className).toContain('dark:bg-slate-950');
            expect(panel.className).not.toContain('bg-card');

            const recordBtn = screen.getByText('تسجيل دفعة لهذا المريض');
            fireEvent.click(recordBtn);

            expect(onClose).toHaveBeenCalled();
            expect(onRecordPayment).toHaveBeenCalledWith(patient);
        });
    });
});
