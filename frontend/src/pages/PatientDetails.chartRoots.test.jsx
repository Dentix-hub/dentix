import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from './PatientDetails';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'en' },
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

vi.mock('@/shared/ui/modals/TreatmentModal', () => ({
    default: () => null,
}));

vi.mock('@/shared/ui/modals/PrescriptionModal', () => ({
    default: () => null,
}));

vi.mock('@/shared/ui/modals/PaymentModal', () => ({
    default: () => null,
}));

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
    useCreatePayment: () => ({ mutate: vi.fn() }),
    useDeletePayment: () => ({ mutate: vi.fn() }),
}));

vi.mock('@/features/patients/hooks/useTreatmentOperations', () => ({
    useTreatmentOperations: () => ({
        handleSaveTreatment: vi.fn(),
    }),
}));

describe('PatientDetails chart integration', () => {
    it('renders the main patient chart with roots enabled and anatomical crowns', () => {
        const queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });

        const { container } = render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <PatientDetails />
                </MemoryRouter>
            </QueryClientProvider>,
        );

        // The main chart tab should be active by default and have 32 root layers
        const rootLayers = container.querySelectorAll('svg[data-layer="roots"]');
        expect(rootLayers).toHaveLength(32);

        // Should have 32 crown layers
        const crownLayers = container.querySelectorAll('svg[data-layer="crown"]');
        expect(crownLayers).toHaveLength(32);

        // Representative permanent teeth 11, 14, 16, 46 should have roots and crowns
        ['11', '14', '16', '46'].forEach((toothKey) => {
            const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
            const crownSvg = container.querySelector(`svg[data-layer="crown"][data-tooth-key="${toothKey}"]`);

            expect(rootSvg).toBeInTheDocument();
            expect(crownSvg).toBeInTheDocument();
        });
    });

    it('keeps the modal tooth selection chart compact and crown-only for optimal dialog usability', () => {
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

        // Open the tooth-selection modal
        const newTreatmentButton = screen.getByText('patient_details.chart.new_treatment');
        fireEvent.click(newTreatmentButton);

        // Modal dialog should be rendered
        const modalContainer = document.body.querySelector('[role="dialog"]') ?? document.body;
        const modalCrowns = modalContainer.querySelectorAll('.space-y-4 svg[data-layer="crown"]');
        expect(modalCrowns.length).toBeGreaterThan(0);

        // The modal chart should NOT render root layers
        const modalRoots = modalContainer.querySelectorAll('.space-y-4 svg[data-layer="roots"]');
        expect(modalRoots).toHaveLength(0);
    });
});
