import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TreatmentPlansCard from '@/features/clinical-plans/TreatmentPlansCard';
import PatientDetails from '@/pages/PatientDetails';
import { MemoryRouter } from 'react-router-dom';

const {
    mockUsePatientClinicalPlans,
    mockUseCreatePatientClinicalPlan,
    mockUseTenantFeatures,
    mockMutateAsync,
} = vi.hoisted(() => ({
    mockUsePatientClinicalPlans: vi.fn(),
    mockUseCreatePatientClinicalPlan: vi.fn(),
    mockUseTenantFeatures: vi.fn(),
    mockMutateAsync: vi.fn(),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'en' },
    }),
}));

vi.mock('@/hooks/usePatientDetails', () => ({
    usePatient: () => ({
        data: { id: 101, name: 'Test Patient', default_price_list_id: null },
        isLoading: false,
    }),
    usePatientTeeth: () => ({
        data: {},
        isLoading: false,
        refetch: vi.fn(),
    }),
    usePatientClinicalWorkspace: () => ({
        data: { read_mode: 'LEGACY_ONLY', domain_coverage: {}, warnings: [], visual_rules: [] },
        isLoading: false,
        refetch: vi.fn(),
    }),
    usePatientTreatments: () => ({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
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
    usePatientClinicalPlans: (...args) => mockUsePatientClinicalPlans(...args),
    useCreatePatientClinicalPlan: () => mockUseCreatePatientClinicalPlan(),
    useTenantFeatures: () => mockUseTenantFeatures(),
}));

vi.mock('@/shared/context/ProceduresContext', () => ({
    useProcedures: () => ({ procedures: [] }),
}));

vi.mock('@/features/clinical-chart/components/ClinicalChartRenderer', () => ({
    default: () => <div data-testid="mock-chart-renderer">Mock Chart</div>,
}));

vi.mock('react-router-dom', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useParams: () => ({ id: '101' }),
        useSearchParams: () => [new URLSearchParams({ tab: 'chart' }), vi.fn()],
        useNavigate: () => vi.fn(),
    };
});

describe('TreatmentPlansCard & Feature Gating', () => {
    let queryClient;

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });
        mockUseCreatePatientClinicalPlan.mockReturnValue({
            mutateAsync: mockMutateAsync,
            isPending: false,
        });
    });

    const renderCard = (patientId = 101) => {
        return render(
            <QueryClientProvider client={queryClient}>
                <TreatmentPlansCard patientId={patientId} />
            </QueryClientProvider>
        );
    };

    const renderPatientDetails = () => {
        return render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter initialEntries={['/patients/101?tab=chart']}>
                    <PatientDetails />
                </MemoryRouter>
            </QueryClientProvider>
        );
    };

    it('flag-off: TreatmentPlansCard is hidden when clinical_treatment_plans is disabled', () => {
        mockUseTenantFeatures.mockReturnValue({
            data: [], // Feature not present
            isLoading: false,
        });
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [],
            isLoading: false,
        });

        renderPatientDetails();

        // Card should NOT be present in document
        expect(screen.queryByTestId('clinical-treatment-plans-card')).toBeNull();
    });

    it('flag-on: TreatmentPlansCard is visible when clinical_treatment_plans is enabled', () => {
        mockUseTenantFeatures.mockReturnValue({
            data: ['clinical_treatment_plans'],
            isLoading: false,
        });
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [],
            isLoading: false,
        });

        renderPatientDetails();

        // Card should be rendered
        expect(screen.getByTestId('clinical-treatment-plans-card')).toBeInTheDocument();
    });

    it('empty state: displays empty state message and CTA when plans list is empty', () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [],
            isLoading: false,
            isError: false,
        });

        renderCard();

        expect(screen.getByTestId('clinical-plans-empty')).toBeInTheDocument();
        expect(screen.getByText('No treatment plans created yet.')).toBeInTheDocument();
        expect(screen.getByTestId('empty-cta-create-plan')).toBeInTheDocument();
    });

    it('renders plans list when plans exist', () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                {
                    id: 1,
                    patient_id: 101,
                    title: 'Full Rehab Plan',
                    status: 'draft',
                    notes: 'Needs 4 veneers and cleaning',
                    version_id: 1,
                    created_at: '2026-10-16T10:00:00Z',
                    phases: [
                        { id: 11, phase_order: 0, name: 'Phase 1', status: 'draft' },
                    ],
                },
            ],
            isLoading: false,
            isError: false,
        });

        renderCard();

        expect(screen.getByTestId('clinical-plan-item-1')).toBeInTheDocument();
        expect(screen.getByText('Full Rehab Plan')).toBeInTheDocument();
        expect(screen.getByTestId('clinical-plan-status-1')).toHaveTextContent(/draft/i);
        expect(screen.getByText('Needs 4 veneers and cleaning')).toBeInTheDocument();

        expect(screen.getByText(/Phase 1/)).toBeInTheDocument();
        expect(screen.getByTestId('clinical-plans-count-badge')).toHaveTextContent('1');
    });

    it('create plan flow: opens dialog, submits title/notes, triggers mutation', async () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [],
            isLoading: false,
            isError: false,
        });
        mockMutateAsync.mockResolvedValueOnce({
            id: 2,
            title: 'Orthodontic Alignment',
            status: 'draft',
        });

        renderCard();

        // Click New Plan
        const newPlanBtn = screen.getByTestId('new-clinical-plan-button');
        fireEvent.click(newPlanBtn);

        // Dialog should be visible
        expect(screen.getByTestId('create-clinical-plan-dialog')).toBeInTheDocument();

        // Enter Title and Notes
        const titleInput = screen.getByTestId('clinical-plan-title-input');
        const notesInput = screen.getByTestId('clinical-plan-notes-input');
        fireEvent.change(titleInput, { target: { value: 'Orthodontic Alignment' } });
        fireEvent.change(notesInput, { target: { value: 'Upper arch clear aligners' } });

        // Submit form
        const submitBtn = screen.getByTestId('submit-create-clinical-plan');
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(mockMutateAsync).toHaveBeenCalledWith({
                patientId: 101,
                data: {
                    title: 'Orthodontic Alignment',
                    notes: 'Upper arch clear aligners',
                },
            });
        });
    });

    it('collapsible toggle: hides content when collapsed and restores on click', () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [],
            isLoading: false,
            isError: false,
        });

        renderCard();

        expect(screen.getByTestId('clinical-plans-empty')).toBeInTheDocument();

        // Collapse
        const toggleBtn = screen.getByTestId('toggle-clinical-plans-collapse');
        fireEvent.click(toggleBtn);

        expect(screen.queryByTestId('clinical-plans-empty')).toBeNull();

        // Expand
        fireEvent.click(toggleBtn);
        expect(screen.getByTestId('clinical-plans-empty')).toBeInTheDocument();
    });
});
