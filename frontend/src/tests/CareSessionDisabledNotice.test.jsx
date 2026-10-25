import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from '@/pages/PatientDetails';
const { mockToastError, mockToastSuccess } = vi.hoisted(() => ({
    mockToastError: vi.fn(),
    mockToastSuccess: vi.fn(),
}));

vi.mock('@/shared/ui', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        toast: {
            error: mockToastError,
            success: mockToastSuccess,
        },
    };
});

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => {
            if (key === 'care_session.disabled_message') return 'ميزة الجلسات الجديدة غير مفعّلة لهذه العيادة';
            return fallback || key;
        },
        i18n: { language: 'ar' },
    }),
}));

vi.mock('react-router-dom', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useParams: () => ({ id: '123' }),
        useSearchParams: () => [new URLSearchParams(), vi.fn()],
        useNavigate: () => vi.fn(),
    };
});

vi.mock('@/shared/context/ProceduresContext', () => ({
    useProcedures: () => ({ procedures: [] }),
}));

vi.mock('@/features/patients/modals/EditPatientModal.jsx', () => ({
    default: () => null,
}));

vi.mock('@/features/clinical-chart/components/QuickTreatmentSheet', () => ({
    default: () => null,
}));

vi.mock('@/shared/ui/modals/PrescriptionModal', () => ({
    default: () => null,
}));

vi.mock('@/shared/ui/modals/PaymentModal', () => ({
    default: () => null,
}));

const mockMutateAsync = vi.fn();

vi.mock('@/hooks/usePatientDetails', () => ({
    usePatient: () => ({
        data: { id: 123, name: 'Test Patient', default_price_list_id: null },
        isLoading: false,
    }),
    usePatientTeeth: () => ({
        data: {},
        isLoading: false,
        refetch: vi.fn(),
    }),
    usePatientClinicalWorkspace: () => ({
        data: null,
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
    }),
    usePatientTreatments: () => ({
        data: [],
        isLoading: false,
    }),
    usePatientPayments: () => ({
        data: [],
        isLoading: false,
    }),
    usePatientAttachments: () => ({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
    }),
    usePatientLabOrders: () => ({
        data: [],
        isLoading: false,
    }),
    useCreatePayment: () => ({ mutate: vi.fn() }),
    useDeletePayment: () => ({ mutate: vi.fn() }),
    useTenantFeatures: () => ({ data: [], isLoading: false }),
    usePatientClinicalPlans: () => ({ data: [], isLoading: false }),
    useActiveCareSession: () => ({ data: null, isLoading: false, refetch: vi.fn() }),
    useResumableCareSession: () => ({
        data: {
            has_resumable: true,
            active_or_paused_session: null,
            items: [
                {
                    work_item_id: 10,
                    tooth_key: '46',
                    canonical_code: 'ENDO_RCT',
                    resumable_status: 'paused',
                    last_session_id: 5,
                    last_step_code: 'ACCESS_OPENING',
                },
            ],
        },
        isLoading: false,
        refetch: vi.fn(),
    }),
    useStartCareSession: () => ({
        mutateAsync: mockMutateAsync,
        isPending: false,
    }),
    useFinishCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useTransitionCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useApplyCareSessionTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRecordCareObservation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/features/patients/hooks/useTreatmentOperations', () => ({
    useTreatmentOperations: () => ({
        handleSaveTreatment: vi.fn(),
    }),
}));

describe('Care Session 404 Disabled State UI Handling', () => {
    it('shows Arabic notice and toast when starting a care session fails with 404', async () => {
        mockMutateAsync.mockRejectedValueOnce({
            response: {
                status: 404,
                data: { detail: 'Clinical native writes are disabled' },
            },
        });

        const queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <PatientDetails />
                </MemoryRouter>
            </QueryClientProvider>,
        );

        // Click resume treatment on the resumable card
        const resumeBtn = screen.getByRole('button', { name: /استئناف العلاج|Resume Treatment/i });
        fireEvent.click(resumeBtn);

        await waitFor(() => {
            expect(mockToastError).toHaveBeenCalledWith('ميزة الجلسات الجديدة غير مفعّلة لهذه العيادة');
        });

        // The banner should also be rendered in the DOM
        expect(screen.getByTestId('care-session-disabled-notice')).toHaveTextContent(
            'ميزة الجلسات الجديدة غير مفعّلة لهذه العيادة',
        );
    });

    it('does NOT show the disabled notice when 404 has a different detail', async () => {
        mockToastError.mockClear();
        mockMutateAsync.mockRejectedValueOnce({
            response: {
                status: 404,
                data: { detail: 'Patient or session not found' },
            },
        });

        const queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <PatientDetails />
                </MemoryRouter>
            </QueryClientProvider>,
        );

        const resumeBtn = screen.getByRole('button', { name: /استئناف العلاج|Resume Treatment/i });
        fireEvent.click(resumeBtn);

        await waitFor(() => {
            expect(mockToastError).toHaveBeenCalledWith('Patient or session not found');
        });

        // The banner should NOT be rendered in the DOM
        expect(screen.queryByTestId('care-session-disabled-notice')).toBeNull();
    });
});
