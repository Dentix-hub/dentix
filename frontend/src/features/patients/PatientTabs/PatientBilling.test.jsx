import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PatientBilling from './PatientBilling';
import * as clinicalChargesApi from '@/api/clinicalCharges';
import enTranslations from '@/locales/en/translation.json';
import arTranslations from '@/locales/ar/translation.json';

const { mockUseTenantFeatures } = vi.hoisted(() => ({
    mockUseTenantFeatures: vi.fn(),
}));

vi.mock('@/hooks/usePatientDetails', () => ({
    useTenantFeatures: () => mockUseTenantFeatures(),
}));

vi.mock('@/api/clinicalCharges', () => ({
    getPatientClinicalCharges: vi.fn(),
    invoiceClinicalCharge: vi.fn(),
    voidClinicalCharge: vi.fn(),
}));

vi.mock('@/shared/ui', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback, options) => {
            let res = typeof fallback === 'string' ? fallback : key;
            if (options && typeof options === 'object') {
                for (const [k, v] of Object.entries(options)) {
                    res = res.replaceAll(`{{${k}}}`, v);
                }
            }
            return res;
        },
        i18n: { language: 'en' },
    }),
}));

const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
    const Wrapper = ({ children }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
    Wrapper.displayName = 'TestQueryClientWrapper';
    return Wrapper;
};

describe('PatientBilling Component - Pending Clinical Charges', () => {
    const sampleCharges = [
        {
            id: 1,
            tenant_id: 1,
            patient_id: 101,
            work_item_id: 501,
            care_session_id: 201,
            doctor_id: 10,
            amount: '150.00',
            discount: '0.00',
            status: 'pending',
            version_id: 1,
            created_at: '2026-10-23T10:00:00Z',
        },
        {
            id: 2,
            tenant_id: 1,
            patient_id: 101,
            work_item_id: 502,
            care_session_id: 201,
            doctor_id: 10,
            amount: '200.00',
            discount: '0.00',
            status: 'invoiced',
            version_id: 2,
            created_at: '2026-10-23T10:05:00Z',
        },
        {
            id: 3,
            tenant_id: 1,
            patient_id: 101,
            work_item_id: 503,
            care_session_id: 201,
            doctor_id: 10,
            amount: '75.00',
            discount: '0.00',
            status: 'voided',
            version_id: 2,
            created_at: '2026-10-23T10:10:00Z',
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        mockUseTenantFeatures.mockReturnValue({ data: [] });
        clinicalChargesApi.getPatientClinicalCharges.mockResolvedValue({
            data: {
                data: {
                    charges: sampleCharges,
                    projection: [],
                },
            },
        });
        clinicalChargesApi.invoiceClinicalCharge.mockResolvedValue({
            data: {
                status: 'success',
                data: { ...sampleCharges[0], status: 'invoiced', version_id: 2 },
            },
        });
        clinicalChargesApi.voidClinicalCharge.mockResolvedValue({
            data: {
                status: 'success',
                data: { ...sampleCharges[0], status: 'voided', version_id: 2 },
            },
        });
    });

    it('does NOT render Pending Clinical Charges card when clinical_vnext_finance_read flag is OFF', () => {
        mockUseTenantFeatures.mockReturnValue({ data: [] });

        render(
            <PatientBilling
                patientId={101}
                tenantFeatures={[]}
            />,
            { wrapper: createWrapper() }
        );

        expect(screen.queryByTestId('pending-clinical-charges-card')).not.toBeInTheDocument();
        expect(clinicalChargesApi.getPatientClinicalCharges).not.toHaveBeenCalled();
    });

    it('renders Pending Clinical Charges card and rows when clinical_vnext_finance_read flag is ON', async () => {
        mockUseTenantFeatures.mockReturnValue({ data: ['clinical_vnext_finance_read'] });

        render(
            <PatientBilling
                patientId={101}
                tenantFeatures={['clinical_vnext_finance_read']}
            />,
            { wrapper: createWrapper() }
        );

        const card = screen.getByTestId('pending-clinical-charges-card');
        expect(card).toBeInTheDocument();

        await waitFor(() => {
            expect(within(card).getByText('#501')).toBeInTheDocument();
            expect(within(card).getByText('150.00')).toBeInTheDocument();
            expect(within(card).getByText('#502')).toBeInTheDocument();
            expect(within(card).getByText('#503')).toBeInTheDocument();
        });

        // Pending charge has Invoice and Void buttons inside the card
        expect(within(card).getByRole('button', { name: /^Invoice$/i })).toBeInTheDocument();
        expect(within(card).getByRole('button', { name: /^Void$/i })).toBeInTheDocument();
    });

    it('calls invoiceClinicalCharge with expected_version_id when Invoice button is clicked', async () => {
        mockUseTenantFeatures.mockReturnValue({ data: ['clinical_vnext_finance_read'] });

        render(
            <PatientBilling
                patientId={101}
                tenantFeatures={['clinical_vnext_finance_read']}
            />,
            { wrapper: createWrapper() }
        );

        const card = screen.getByTestId('pending-clinical-charges-card');
        await waitFor(() => {
            expect(within(card).getByText('#501')).toBeInTheDocument();
        });

        const invoiceBtn = within(card).getByRole('button', { name: /^Invoice$/i });
        fireEvent.click(invoiceBtn);

        await waitFor(() => {
            expect(clinicalChargesApi.invoiceClinicalCharge).toHaveBeenCalledWith(1, {
                expected_version_id: 1,
            });
        });
    });

    it('calls voidClinicalCharge with expected_version_id when Void button is clicked', async () => {
        mockUseTenantFeatures.mockReturnValue({ data: ['clinical_vnext_finance_read'] });

        render(
            <PatientBilling
                patientId={101}
                tenantFeatures={['clinical_vnext_finance_read']}
            />,
            { wrapper: createWrapper() }
        );

        const card = screen.getByTestId('pending-clinical-charges-card');
        await waitFor(() => {
            expect(within(card).getByText('#501')).toBeInTheDocument();
        });

        const voidBtn = within(card).getByRole('button', { name: /^Void$/i });
        fireEvent.click(voidBtn);

        await waitFor(() => {
            expect(clinicalChargesApi.voidClinicalCharge).toHaveBeenCalledWith(1, {
                expected_version_id: 1,
            });
        });
    });

    it('has required English and Arabic i18n keys configured', () => {
        const enPending = enTranslations.patientDetails?.billing?.pending_charges;
        const arPending = arTranslations.patientDetails?.billing?.pending_charges;

        expect(enPending).toBeDefined();
        expect(arPending).toBeDefined();

        expect(enPending.title).toBe('Pending Clinical Charges');
        expect(arPending.title).toBe('الرسوم السريرية المعلقة');

        expect(enPending.invoice_btn).toBe('Invoice');
        expect(arPending.invoice_btn).toBe('فوترة');

        expect(enPending.void_btn).toBe('Void');
        expect(arPending.void_btn).toBe('إلغاء');

        expect(enPending.status_pending).toBe('Pending');
        expect(arPending.status_pending).toBe('معلق');

        expect(enPending.status_invoiced).toBe('Invoiced');
        expect(arPending.status_invoiced).toBe('تمت الفوترة');

        expect(enPending.status_voided).toBe('Voided');
        expect(arPending.status_voided).toBe('ملغي');
    });
});
