import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TreatmentPlansCard from '@/features/clinical-plans/TreatmentPlansCard';
import PatientDetails from '@/pages/PatientDetails';
import { MemoryRouter } from 'react-router-dom';

const {
    mockUsePatientClinicalPlans,
    mockUseCreatePatientClinicalPlan,
    mockUsePatientClinicalPlanCandidates,
    mockUseAddPatientClinicalPlanPhase,
    mockUseUpdatePatientClinicalPlanPhase,
    mockUseReorderPatientClinicalPlanPhases,
    mockUseDeletePatientClinicalPlanPhase,
    mockUseAddPatientClinicalPlanItem,
    mockUseRemovePatientClinicalPlanItem,
    mockUseTransitionPatientClinicalPlan,
    mockUseTenantFeatures,
    mockCreateMutateAsync,
    mockAddPhaseMutateAsync,
    mockUpdatePhaseMutateAsync,
    mockReorderPhasesMutateAsync,
    mockDeletePhaseMutateAsync,
    mockAddItemMutateAsync,
    mockRemoveItemMutateAsync,
    mockTransitionMutateAsync,
} = vi.hoisted(() => ({
    mockUsePatientClinicalPlans: vi.fn(),
    mockUseCreatePatientClinicalPlan: vi.fn(),
    mockUsePatientClinicalPlanCandidates: vi.fn(),
    mockUseAddPatientClinicalPlanPhase: vi.fn(),
    mockUseUpdatePatientClinicalPlanPhase: vi.fn(),
    mockUseReorderPatientClinicalPlanPhases: vi.fn(),
    mockUseDeletePatientClinicalPlanPhase: vi.fn(),
    mockUseAddPatientClinicalPlanItem: vi.fn(),
    mockUseRemovePatientClinicalPlanItem: vi.fn(),
    mockUseTransitionPatientClinicalPlan: vi.fn(),
    mockUseTenantFeatures: vi.fn(),
    mockCreateMutateAsync: vi.fn(),
    mockAddPhaseMutateAsync: vi.fn(),
    mockUpdatePhaseMutateAsync: vi.fn(),
    mockReorderPhasesMutateAsync: vi.fn(),
    mockDeletePhaseMutateAsync: vi.fn(),
    mockAddItemMutateAsync: vi.fn(),
    mockRemoveItemMutateAsync: vi.fn(),
    mockTransitionMutateAsync: vi.fn(),
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
    useUpdatePatientClinicalPlanPhase: () => mockUseUpdatePatientClinicalPlanPhase(),
    useReorderPatientClinicalPlanPhases: () => mockUseReorderPatientClinicalPlanPhases(),
    useDeletePatientClinicalPlanPhase: () => mockUseDeletePatientClinicalPlanPhase(),
    useAddPatientClinicalPlanItem: () => mockUseAddPatientClinicalPlanItem(),
    useRemovePatientClinicalPlanItem: () => mockUseRemovePatientClinicalPlanItem(),
    useTransitionPatientClinicalPlan: () => mockUseTransitionPatientClinicalPlan(),
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
        mockUseUpdatePatientClinicalPlanPhase.mockReturnValue({
            mutateAsync: mockUpdatePhaseMutateAsync,
            isPending: false,
        });
        mockUseReorderPatientClinicalPlanPhases.mockReturnValue({
            mutateAsync: mockReorderPhasesMutateAsync,
            isPending: false,
        });
        mockUseDeletePatientClinicalPlanPhase.mockReturnValue({
            mutateAsync: mockDeletePhaseMutateAsync,
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
        mockUseTransitionPatientClinicalPlan.mockReturnValue({
            mutateAsync: mockTransitionMutateAsync,
            isPending: false,
        });
        mockUsePatientClinicalPlanCandidates.mockReturnValue({
            data: [],
            isLoading: false,
        });
    });

    const renderCard = (patientId = 101, props = {}) => {
        return render(
            <QueryClientProvider client={queryClient}>
                <TreatmentPlansCard patientId={patientId} {...props} />
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

    it('renders status badges for each plan status', () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                { id: 1, patient_id: 101, title: 'Plan Draft', status: 'draft', phases: [] },
                { id: 2, patient_id: 101, title: 'Plan Proposed', status: 'proposed', phases: [] },
                { id: 3, patient_id: 101, title: 'Plan Accepted', status: 'accepted', phases: [] },
                { id: 4, patient_id: 101, title: 'Plan Completed', status: 'completed', phases: [] },
                { id: 5, patient_id: 101, title: 'Plan Cancelled', status: 'cancelled', phases: [] },
            ],
            isLoading: false,
            isError: false,
        });

        renderCard();

        expect(screen.getByTestId('clinical-plan-status-1')).toHaveTextContent('draft');
        expect(screen.getByTestId('clinical-plan-status-2')).toHaveTextContent('proposed');
        expect(screen.getByTestId('clinical-plan-status-3')).toHaveTextContent('accepted');
        expect(screen.getByTestId('clinical-plan-status-4')).toHaveTextContent('completed');
        expect(screen.getByTestId('clinical-plan-status-5')).toHaveTextContent('cancelled');
    });

    it('shows allowed transition buttons per status and triggers transition mutation', async () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                { id: 1, patient_id: 101, title: 'Draft Plan', status: 'draft', phases: [] },
                { id: 2, patient_id: 101, title: 'Proposed Plan', status: 'proposed', phases: [] },
                { id: 3, patient_id: 101, title: 'Accepted Plan', status: 'accepted', phases: [] },
                { id: 4, patient_id: 101, title: 'Completed Plan', status: 'completed', phases: [] },
            ],
            isLoading: false,
            isError: false,
        });
        mockTransitionMutateAsync.mockResolvedValueOnce({ id: 1, status: 'proposed' });

        renderCard();

        // Draft plan allows propose and cancel
        expect(screen.getByTestId('plan-transition-proposed-1')).toBeInTheDocument();
        expect(screen.getByTestId('plan-transition-cancelled-1')).toBeInTheDocument();

        // Proposed plan allows accept and cancel
        expect(screen.getByTestId('plan-transition-accepted-2')).toBeInTheDocument();
        expect(screen.getByTestId('plan-transition-cancelled-2')).toBeInTheDocument();

        // Accepted plan allows complete and cancel
        expect(screen.getByTestId('plan-transition-completed-3')).toBeInTheDocument();
        expect(screen.getByTestId('plan-transition-cancelled-3')).toBeInTheDocument();

        // Completed plan has no transition buttons
        expect(screen.queryByTestId('plan-transition-proposed-4')).toBeNull();
        expect(screen.queryByTestId('plan-transition-accepted-4')).toBeNull();
        expect(screen.queryByTestId('plan-transition-completed-4')).toBeNull();
        expect(screen.queryByTestId('plan-transition-cancelled-4')).toBeNull();

        // Click Propose on draft plan
        fireEvent.click(screen.getByTestId('plan-transition-proposed-1'));

        await waitFor(() => {
            expect(mockTransitionMutateAsync).toHaveBeenCalledWith({
                patientId: 101,
                planId: 1,
                data: { to_status: 'proposed' },
            });
        });
    });

    it('hides add phase, add procedure, and delete procedure controls when plan is in accepted, completed, or cancelled status', () => {
        mockUsePatientClinicalPlans.mockReturnValue({
            data: [
                {
                    id: 3,
                    patient_id: 101,
                    title: 'Accepted Plan',
                    status: 'accepted',
                    phases: [
                        {
                            id: 31,
                            phase_order: 0,
                            name: 'Phase 1',
                            status: 'draft',
                            items: [
                                {
                                    id: 301,
                                    work_item_id: 501,
                                    item_order: 0,
                                    work_item: {
                                        id: 501,
                                        procedure_code: 'D2391',
                                        display_name: 'Composite',
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

        renderCard();

        // In accepted plan, canModifyPlan is false
        // + Add Phase button should be hidden
        expect(screen.queryByTestId('add-phase-button-3')).toBeNull();

        // + Add Procedure button should be hidden
        expect(screen.queryByTestId('add-procedure-button-31')).toBeNull();

        // Remove item button should be hidden
        expect(screen.queryByTestId('remove-phase-item-301')).toBeNull();
    });

    describe('CARD S12: Phase Reorder, Edit, Delete, and Chart Plan Overlay', () => {
        const mockPlanWithPhases = {
            id: 1,
            patient_id: 101,
            title: 'Multi-Phase Plan',
            status: 'draft',
            phases: [
                {
                    id: 11,
                    phase_order: 0,
                    name: 'Phase 1 - Endo',
                    notes: 'Root canal treatment',
                    items: [
                        {
                            id: 101,
                            work_item_id: 201,
                            item_order: 0,
                            work_item: {
                                id: 201,
                                procedure_code: 'D3310',
                                display_name: 'Root Canal',
                                status: 'planned',
                                targets: [{ tooth_key: '16' }],
                            },
                        },
                    ],
                },
                {
                    id: 12,
                    phase_order: 1,
                    name: 'Phase 2 - Crown',
                    notes: 'Porcelain crown',
                    items: [
                        {
                            id: 102,
                            work_item_id: 202,
                            item_order: 0,
                            work_item: {
                                id: 202,
                                procedure_code: 'D2740',
                                display_name: 'Crown',
                                status: 'planned',
                                targets: [{ tooth_key: '16' }],
                            },
                        },
                    ],
                },
            ],
        };

        it('disables Move Up on first phase and Move Down on last phase, and triggers reorder on click', async () => {
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithPhases],
                isLoading: false,
                isError: false,
            });
            mockReorderPhasesMutateAsync.mockResolvedValueOnce({
                ...mockPlanWithPhases,
                phases: [mockPlanWithPhases.phases[1], mockPlanWithPhases.phases[0]],
            });

            renderCard();

            const moveUpFirst = screen.getByTestId('move-up-phase-11');
            const moveDownFirst = screen.getByTestId('move-down-phase-11');
            const moveUpSecond = screen.getByTestId('move-up-phase-12');
            const moveDownSecond = screen.getByTestId('move-down-phase-12');

            // Boundary constraints: first phase cannot move up, last phase cannot move down
            expect(moveUpFirst).toBeDisabled();
            expect(moveDownFirst).not.toBeDisabled();
            expect(moveUpSecond).not.toBeDisabled();
            expect(moveDownSecond).toBeDisabled();

            // Click move down on first phase
            fireEvent.click(moveDownFirst);

            await waitFor(() => {
                expect(mockReorderPhasesMutateAsync).toHaveBeenCalledWith({
                    patientId: 101,
                    planId: 1,
                    phaseIds: [12, 11],
                });
            });
        });

        it('opens edit phase dialog, allows renaming and updating notes, and submits update mutation', async () => {
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithPhases],
                isLoading: false,
                isError: false,
            });
            mockUpdatePhaseMutateAsync.mockResolvedValueOnce({
                id: 11,
                name: 'Phase 1 - Revised',
                notes: 'Updated clinical notes',
            });

            renderCard();

            // Click Edit Phase button
            fireEvent.click(screen.getByTestId('edit-phase-button-11'));

            // Dialog should be open with current values
            expect(screen.getByTestId('edit-phase-dialog')).toBeInTheDocument();
            const nameInput = screen.getByTestId('edit-phase-name-input');
            const notesInput = screen.getByTestId('edit-phase-notes-input');

            expect(nameInput).toHaveValue('Phase 1 - Endo');
            expect(notesInput).toHaveValue('Root canal treatment');

            // Change values
            fireEvent.change(nameInput, { target: { value: 'Phase 1 - Revised' } });
            fireEvent.change(notesInput, { target: { value: 'Updated clinical notes' } });

            // Submit
            fireEvent.click(screen.getByTestId('submit-edit-phase-button'));

            await waitFor(() => {
                expect(mockUpdatePhaseMutateAsync).toHaveBeenCalledWith({
                    patientId: 101,
                    planId: 1,
                    phaseId: 11,
                    data: {
                        name: 'Phase 1 - Revised',
                        notes: 'Updated clinical notes',
                    },
                });
            });
        });

        it('opens delete phase dialog and submits delete mutation when confirmed', async () => {
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithPhases],
                isLoading: false,
                isError: false,
            });
            mockDeletePhaseMutateAsync.mockResolvedValueOnce({ success: true });

            renderCard();

            // Click Delete Phase button
            fireEvent.click(screen.getByTestId('delete-phase-button-11'));

            // Delete confirmation dialog is open
            const dialog = screen.getByTestId('delete-phase-dialog');
            expect(dialog).toBeInTheDocument();
            expect(within(dialog).getByText('Phase 1 - Endo')).toBeInTheDocument();

            // Confirm delete
            fireEvent.click(screen.getByTestId('confirm-delete-phase-button'));

            await waitFor(() => {
                expect(mockDeletePhaseMutateAsync).toHaveBeenCalledWith({
                    patientId: 101,
                    planId: 1,
                    phaseId: 11,
                });
            });
        });

        it('calls onToggleOverlay callback with correct plan and phase arguments and reflects active state', () => {
            const onToggleOverlay = vi.fn();
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithPhases],
                isLoading: false,
                isError: false,
            });

            const { rerender } = render(
                <QueryClientProvider client={queryClient}>
                    <TreatmentPlansCard
                        patientId={101}
                        activeOverlayPlanId={null}
                        activeOverlayPhaseId={null}
                        onToggleOverlay={onToggleOverlay}
                    />
                </QueryClientProvider>
            );

            // Toggle whole plan overlay
            const planOverlayBtn = screen.getByTestId('overlay-plan-button-1');
            expect(planOverlayBtn).toHaveAttribute('aria-pressed', 'false');
            fireEvent.click(planOverlayBtn);
            expect(onToggleOverlay).toHaveBeenCalledWith(1, null);

            // Toggle specific phase overlay
            const phaseOverlayBtn = screen.getByTestId('overlay-phase-button-11');
            expect(phaseOverlayBtn).toHaveAttribute('aria-pressed', 'false');
            fireEvent.click(phaseOverlayBtn);
            expect(onToggleOverlay).toHaveBeenCalledWith(1, 11);

            // Rerender with active plan overlay
            rerender(
                <QueryClientProvider client={queryClient}>
                    <TreatmentPlansCard
                        patientId={101}
                        activeOverlayPlanId={1}
                        activeOverlayPhaseId={null}
                        onToggleOverlay={onToggleOverlay}
                    />
                </QueryClientProvider>
            );
            expect(screen.getByTestId('overlay-plan-button-1')).toHaveAttribute('aria-pressed', 'true');

            // Rerender with active phase overlay
            rerender(
                <QueryClientProvider client={queryClient}>
                    <TreatmentPlansCard
                        patientId={101}
                        activeOverlayPlanId={1}
                        activeOverlayPhaseId={11}
                        onToggleOverlay={onToggleOverlay}
                    />
                </QueryClientProvider>
            );
            expect(screen.getByTestId('overlay-phase-button-11')).toHaveAttribute('aria-pressed', 'true');
        });

        it('shows overlay active banner on PatientDetails when plan overlay is toggled and clears on click', async () => {
            mockUseTenantFeatures.mockReturnValue({
                data: ['clinical_treatment_plans'],
                isLoading: false,
            });
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithPhases],
                isLoading: false,
                isError: false,
            });

            renderPatientDetails();

            // Initially no overlay active banner
            expect(screen.queryByTestId('plan-overlay-active-banner')).toBeNull();

            // Click plan overlay button in TreatmentPlansCard
            const planOverlayBtn = screen.getByTestId('overlay-plan-button-1');
            fireEvent.click(planOverlayBtn);

            // Now banner should appear above chart
            await waitFor(() => {
                expect(screen.getByTestId('plan-overlay-active-banner')).toBeInTheDocument();
            });
            const banner = screen.getByTestId('plan-overlay-active-banner');
            expect(within(banner).getByText('Multi-Phase Plan')).toBeInTheDocument();

            // Clear overlay
            const clearBtn = screen.getByTestId('clear-plan-overlay-button');
            fireEvent.click(clearBtn);

            await waitFor(() => {
                expect(screen.queryByTestId('plan-overlay-active-banner')).toBeNull();
            });
        });
    });

    describe('Treatment Plan Dynamic Estimate Projection (G9-M10 / S13)', () => {
        const mockPlanWithEstimates = {
            id: 201,
            patient_id: 101,
            title: 'Rehabilitation Estimate Plan',
            status: 'draft',
            notes: 'Estimate test plan',
            version_id: 1,
            created_at: '2026-10-18T10:00:00Z',
            plan_estimated_total: 2500.0,
            unpriced_items_count: 1,
            phases: [
                {
                    id: 211,
                    phase_order: 0,
                    name: 'Phase 1 - Endo',
                    status: 'draft',
                    notes: null,
                    phase_estimated_total: 2500.0,
                    unpriced_items_count: 0,
                    items: [
                        {
                            id: 301,
                            phase_id: 211,
                            work_item_id: 401,
                            item_order: 0,
                            estimated_fee: 2500.0,
                            unpriced: false,
                            work_item: {
                                id: 401,
                                procedure_code: 'ENDO_RCT',
                                display_name: 'Root Canal Treatment',
                                status: 'active',
                                targets: [{ tooth_key: '16', surface: null }],
                            },
                        },
                    ],
                },
                {
                    id: 212,
                    phase_order: 1,
                    name: 'Phase 2 - Consult',
                    status: 'draft',
                    notes: null,
                    phase_estimated_total: 0.0,
                    unpriced_items_count: 1,
                    items: [
                        {
                            id: 302,
                            phase_id: 212,
                            work_item_id: 402,
                            item_order: 0,
                            estimated_fee: 0.0,
                            unpriced: true,
                            work_item: {
                                id: 402,
                                procedure_code: 'DIAG_CONSULT',
                                display_name: 'Consultation',
                                status: 'active',
                                targets: [],
                            },
                        },
                    ],
                },
            ],
        };

        it('renders plan estimate badge with formatted currency and unpriced indicator when items are unpriced', () => {
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithEstimates],
                isLoading: false,
                isError: false,
            });

            renderCard();

            const planBadge = screen.getByTestId('plan-estimate-badge-201');
            expect(planBadge).toBeInTheDocument();
            expect(planBadge).toHaveTextContent('Estimate:');
            expect(planBadge).toHaveTextContent('2,500 EGP');

            const unpricedIndicator = screen.getByTestId('plan-unpriced-indicator-201');
            expect(unpricedIndicator).toBeInTheDocument();
            expect(unpricedIndicator).toHaveTextContent('*');
        });

        it('renders phase estimate badges and phase unpriced indicators appropriately', () => {
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithEstimates],
                isLoading: false,
                isError: false,
            });

            renderCard();

            // Phase 1: priced
            const phase1Badge = screen.getByTestId('phase-estimate-badge-211');
            expect(phase1Badge).toHaveTextContent('Estimate:');
            expect(phase1Badge).toHaveTextContent('2,500 EGP');
            expect(screen.queryByTestId('phase-unpriced-indicator-211')).toBeNull();

            // Phase 2: has unpriced item
            const phase2Badge = screen.getByTestId('phase-estimate-badge-212');
            expect(phase2Badge).toHaveTextContent('Estimate:');
            expect(phase2Badge).toHaveTextContent('0 EGP');
            const phase2Indicator = screen.getByTestId('phase-unpriced-indicator-212');
            expect(phase2Indicator).toBeInTheDocument();
            expect(phase2Indicator).toHaveTextContent('*');
        });

        it('renders item estimate fee for priced items and unpriced badge for unpriced items', () => {
            mockUsePatientClinicalPlans.mockReturnValue({
                data: [mockPlanWithEstimates],
                isLoading: false,
                isError: false,
            });

            renderCard();

            // Item 301 is priced
            const item301Estimate = screen.getByTestId('item-estimate-301');
            expect(item301Estimate).toBeInTheDocument();
            expect(item301Estimate).toHaveTextContent('Est:');
            expect(item301Estimate).toHaveTextContent('2,500 EGP');
            expect(screen.queryByTestId('item-unpriced-badge-301')).toBeNull();

            // Item 302 is unpriced
            const item302Unpriced = screen.getByTestId('item-unpriced-badge-302');
            expect(item302Unpriced).toBeInTheDocument();
            expect(item302Unpriced).toHaveTextContent('Unpriced');
            expect(screen.queryByTestId('item-estimate-302')).toBeNull();
        });
    });
});
