import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TreatmentPlansCard from '@/features/clinical-plans/TreatmentPlansCard';
import PatientDetails from '@/pages/PatientDetails';
import { MemoryRouter } from 'react-router-dom';

const {
    mockUsePatientClinicalPlans,
    mockUseCreatePatientClinicalPlan,
    mockUsePatientClinicalPlanCandidates,
    mockUseAddPatientClinicalPlanPhase,
    mockUseAddPatientClinicalPlanItem,
    mockUseRemovePatientClinicalPlanItem,
    mockUseTenantFeatures,
    mockCreateMutateAsync,
    mockAddPhaseMutateAsync,
    mockAddItemMutateAsync,
    mockRemoveItemMutateAsync,
} = vi.hoisted(() => ({
    mockUsePatientClinicalPlans: vi.fn(),
    mockUseCreatePatientClinicalPlan: vi.fn(),
    mockUsePatientClinicalPlanCandidates: vi.fn(),
    mockUseAddPatientClinicalPlanPhase: vi.fn(),
    mockUseAddPatientClinicalPlanItem: vi.fn(),
    mockUseRemovePatientClinicalPlanItem: vi.fn(),
    mockUseTenantFeatures: vi.fn(),
    mockCreateMutateAsync: vi.fn(),
    mockAddPhaseMutateAsync: vi.fn(),
    mockAddItemMutateAsync: vi.fn(),
    mockRemoveItemMutateAsync: vi.fn(),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback, options) => {
            if (options && options.n !== undefined) {
                return (fallback || key).replace('{{n}}', options.n);
            }
            if (options && options.number !== undefined) {
                return (fallback || key).replace('{{number}}', options.number);
            }
            return typeof fallback === 'string' ? fallback : key;
        },
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
    usePatientClinicalPlanCandidates: (...args) => mockUsePatientClinicalPlanCandidates(...args),
    useAddPatientClinicalPlanPhase: () => mockUseAddPatientClinicalPlanPhase(),
    useAddPatientClinicalPlanItem: () => mockUseAddPatientClinicalPlanItem(),
    useRemovePatientClinicalPlanItem: () => mockUseRemovePatientClinicalPlanItem(),
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
            mutateAsync: mockCreateMutateAsync,
            isPending: false,
        });
        mockUseAddPatientClinicalPlanPhase.mockReturnValue({
            mutateAsync: mockAddPhaseMutateAsync,
            isPending: false,
        });
        mockUseAddPatientClinicalPlanItem.mockReturnValue({
            mutateAsync: mockAddItemMutateAsync,
            isPending: false,
        });
        mockUseRemovePatientClinicalPlanItem.mockReturnValue({
            mutateAsync: mockRemoveItemMutateAsync,
            isPending: false,
        });
        mockUsePatientClinicalPlanCandidates.mockReturnValue({
            data: [],
            isLoading: false,
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
                        { id: 11, phase_order: 0, name: 'Phase 1', status: 'draft', items: [] },
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
        mockCreateMutateAsync.mockResolvedValueOnce({
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
            expect(mockCreateMutateAsync).toHaveBeenCalledWith({
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

    it('renders phases with items: displays phase order, phase name, items with targets and status', () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                {
                    id: 1,
                    patient_id: 101,
                    title: 'Comprehensive Plan',
                    status: 'draft',
                    phases: [
                        {
                            id: 11,
                            phase_order: 0,
                            name: 'Phase 1: Urgent',
                            status: 'draft',
                            items: [
                                {
                                    id: 21,
                                    work_item_id: 501,
                                    item_order: 0,
                                    work_item: {
                                        id: 501,
                                        procedure_code: 'D2150',
                                        display_name: 'Amalgam 2 Surfaces',
                                        status: 'planned',
                                        targets: [
                                            { tooth_key: '16', surface: 'MO' },
                                        ],
                                    },
                                },
                            ],
                        },
                        {
                            id: 12,
                            phase_order: 1,
                            name: 'Phase 2: Restorative',
                            status: 'draft',
                            items: [],
                        },
                    ],
                },
            ],
            isLoading: false,
            isError: false,
        });

        renderCard();

        // Check phase 1 rendered
        expect(screen.getByTestId('clinical-phase-item-11')).toBeInTheDocument();
        expect(screen.getByText('Phase 1: Urgent')).toBeInTheDocument();
        expect(screen.getByTestId('phase-item-21')).toBeInTheDocument();
        expect(screen.getByText('Amalgam 2 Surfaces')).toBeInTheDocument();
        expect(screen.getByText('16 (MO)')).toBeInTheDocument();

        // Check phase 2 rendered with empty state
        expect(screen.getByTestId('clinical-phase-item-12')).toBeInTheDocument();
        expect(screen.getByText('Phase 2: Restorative')).toBeInTheDocument();
        expect(screen.getByTestId('phase-empty-12')).toBeInTheDocument();
    });

    it('adding a phase: triggers mutation with auto-assigned localized phase name', async () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                {
                    id: 1,
                    patient_id: 101,
                    title: 'Plan A',
                    status: 'draft',
                    phases: [
                        { id: 11, phase_order: 0, name: 'Phase 1', status: 'draft', items: [] },
                    ],
                },
            ],
            isLoading: false,
            isError: false,
        });
        mockAddPhaseMutateAsync.mockResolvedValueOnce({
            id: 12,
            phase_order: 1,
            name: 'Phase 2',
            status: 'draft',
            items: [],
        });

        renderCard();

        const addPhaseBtn = screen.getByTestId('add-phase-button-1');
        fireEvent.click(addPhaseBtn);

        await waitFor(() => {
            expect(mockAddPhaseMutateAsync).toHaveBeenCalledWith({
                patientId: 101,
                planId: 1,
                data: { name: 'Phase 2' },
            });
        });
    });

    it('attaching an item to a phase: opens selector modal, selects candidate, triggers mutation', async () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                {
                    id: 1,
                    patient_id: 101,
                    title: 'Plan A',
                    status: 'draft',
                    phases: [
                        { id: 11, phase_order: 0, name: 'Phase 1', status: 'draft', items: [] },
                    ],
                },
            ],
            isLoading: false,
            isError: false,
        });
        mockUsePatientClinicalPlanCandidates.mockReturnValue({
            data: [
                {
                    id: 501,
                    procedure_code: 'D2391',
                    display_name: 'Composite 1 Surface',
                    status: 'planned',
                    targets: [{ tooth_key: '24', surface: 'O' }],
                },
            ],
            isLoading: false,
        });
        mockAddItemMutateAsync.mockResolvedValueOnce({
            id: 31,
            phase_id: 11,
            work_item_id: 501,
            item_order: 0,
        });

        renderCard();

        // Open procedure modal on phase 11
        const addProcBtn = screen.getByTestId('add-procedure-button-11');
        fireEvent.click(addProcBtn);

        // Dialog should be open
        expect(screen.getByTestId('add-procedure-dialog')).toBeInTheDocument();

        // Select candidate procedure
        const select = screen.getByTestId('candidate-procedure-select');
        fireEvent.change(select, { target: { value: '501' } });

        // Submit form
        const submitBtn = screen.getByTestId('submit-add-procedure');
        fireEvent.click(submitBtn);

        await waitFor(() => {
            expect(mockAddItemMutateAsync).toHaveBeenCalledWith({
                patientId: 101,
                planId: 1,
                phaseId: 11,
                data: { work_item_id: 501 },
            });
        });
    });

    it('removing an item from a phase: triggers remove item mutation', async () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                {
                    id: 1,
                    patient_id: 101,
                    title: 'Plan A',
                    status: 'draft',
                    phases: [
                        {
                            id: 11,
                            phase_order: 0,
                            name: 'Phase 1',
                            status: 'draft',
                            items: [
                                {
                                    id: 21,
                                    work_item_id: 501,
                                    item_order: 0,
                                    work_item: {
                                        id: 501,
                                        procedure_code: 'D2150',
                                        display_name: 'Amalgam 2 Surfaces',
                                        status: 'planned',
                                        targets: [],
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
            isLoading: false,
            isError: false,
        });
        mockRemoveItemMutateAsync.mockResolvedValueOnce({});

        renderCard();

        const removeBtn = screen.getByTestId('remove-phase-item-21');
        fireEvent.click(removeBtn);

        await waitFor(() => {
            expect(mockRemoveItemMutateAsync).toHaveBeenCalledWith({
                patientId: 101,
                planId: 1,
                phaseId: 11,
                itemId: 21,
            });
        });
    });
});
