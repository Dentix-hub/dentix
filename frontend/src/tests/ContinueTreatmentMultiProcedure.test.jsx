import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ContinueTreatmentCard from '@/features/care-sessions/ContinueTreatmentCard';
import PatientDetails from '@/pages/PatientDetails';

const {
    mockStartSession,
    mockApplyTemplate,
    mockUseResumableCareSession,
    mockUseActiveCareSession,
} = vi.hoisted(() => ({
    mockStartSession: vi.fn(),
    mockApplyTemplate: vi.fn(),
    mockUseResumableCareSession: vi.fn(),
    mockUseActiveCareSession: vi.fn(() => ({ data: null, isLoading: false, refetch: vi.fn() })),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 1, role: 'doctor', permissions: ['clinical:write'] },
    }),
}));

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

vi.mock('@/features/patients/hooks/useTreatmentOperations', () => ({
    useTreatmentOperations: () => ({
        handleSaveTreatment: vi.fn(),
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
        data: { read_mode: 'LEGACY_ONLY', domain_coverage: {}, warnings: [], visual_rules: [] },
        isLoading: false,
        isError: false,
        error: null,
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
    usePatientLabOrders: () => ({
        data: [],
        isLoading: false,
    }),
    useCreatePayment: () => ({ mutate: vi.fn() }),
    useDeletePayment: () => ({ mutate: vi.fn() }),
    useTenantFeatures: () => ({
        data: [{ feature_key: 'clinical_vnext_native_writes', is_enabled: true }],
        isLoading: false,
    }),
    usePatientClinicalPlans: () => ({ data: [], isLoading: false }),
    useActiveCareSession: (...args) => mockUseActiveCareSession(...args),
    useResumableCareSession: (...args) => mockUseResumableCareSession(...args),
    useStartCareSession: () => ({
        mutateAsync: mockStartSession,
        isPending: false,
    }),
    useFinishCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useTransitionCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useApplyCareSessionTemplate: () => ({
        mutateAsync: mockApplyTemplate,
        isPending: false,
    }),
    useRecordCareObservation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('Slice S25 / Defect 3: Multi-Procedure Continuation Card', () => {
    const mockMultiResumableContext = {
        has_resumable: true,
        paused_session: null,
        items: [
            {
                work_item_id: 101,
                procedure_code: 'ENDO_RCT',
                tooth_key: '16',
                title: 'ENDO_RCT',
                status: 'active',
                total_steps: 6,
                completed_steps_count: 2,
                next_step_title: 'Working Length',
                last_session_id: 1,
                observations: [
                    {
                        id: 11,
                        observation_code: 'working_length',
                        tooth_key: '16',
                        canal_id: 'MB1',
                        structured_value: { length_mm: 20.0, maf: 25 },
                    },
                ],
            },
            {
                work_item_id: 102,
                procedure_code: 'SURG_EXTRACT',
                tooth_key: '26',
                title: 'SURG_EXTRACT',
                status: 'active',
                total_steps: 4,
                completed_steps_count: 1,
                next_step_title: 'Luxation',
                last_session_id: 1,
                observations: [],
            },
        ],
    };

    it('renders multi-procedure tabs when items.length > 1', () => {
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={vi.fn()}
            />
        );

        expect(screen.getByTestId('multi-procedure-selector')).toBeInTheDocument();
        expect(screen.getByTestId('select-procedure-0')).toHaveTextContent(/Tooth 16/);
        expect(screen.getByTestId('select-procedure-1')).toHaveTextContent(/Tooth 26/);
        expect(screen.getByTestId('resume-all-procedures-btn')).toHaveTextContent(/Resume All \(2\)/);
    });

    it('switches between procedures and updates active card content', () => {
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={vi.fn()}
            />
        );

        // Initially tooth 16 is displayed
        expect(screen.getByTestId('continue-card-tooth-badge')).toHaveTextContent('Tooth 16');
        expect(screen.getByTestId('canal-measurements-preview')).toHaveTextContent(/MB1.*20mm/);

        // Switch to tooth 26 procedure
        fireEvent.click(screen.getByTestId('select-procedure-1'));

        expect(screen.getByTestId('continue-card-tooth-badge')).toHaveTextContent('Tooth 26');
        expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent('SURG_EXTRACT');
        expect(screen.queryByTestId('canal-measurements-preview')).not.toBeInTheDocument();
    });

    it('resumes only selected procedure when standard resume button is clicked', () => {
        const resumeSpy = vi.fn();
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={resumeSpy}
            />
        );

        // Switch to tooth 26
        fireEvent.click(screen.getByTestId('select-procedure-1'));
        fireEvent.click(screen.getByTestId('resume-treatment-btn'));

        expect(resumeSpy).toHaveBeenCalledTimes(1);
        expect(resumeSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                workItemId: 102,
                workItemIds: [102],
                toothKey: '26',
                procedureCode: 'SURG_EXTRACT',
                resumeAll: false,
            })
        );
    });

    it('resumes all procedures when Resume All is clicked', () => {
        const resumeSpy = vi.fn();
        render(
            <ContinueTreatmentCard
                resumableContext={mockMultiResumableContext}
                onResumeTreatment={resumeSpy}
            />
        );

        fireEvent.click(screen.getByTestId('resume-all-procedures-btn'));

        expect(resumeSpy).toHaveBeenCalledTimes(1);
        expect(resumeSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                workItemIds: [101, 102],
                resumeAll: true,
            })
        );
    });

    it('exercises real PatientDetails: passes plural workItemIds and evaluates template requirements independently for each selected procedure', async () => {
        // Setup: Procedure 101 already has carried-over steps in session; Procedure 102 does NOT.
        mockStartSession.mockResolvedValue({
            data: {
                id: 77,
                steps: [
                    { id: 1, work_item_id: 101, title: 'Carried Step for RCT' },
                ],
            },
        });
        mockApplyTemplate.mockResolvedValue({ data: [] });
        mockUseResumableCareSession.mockReturnValue({
            data: mockMultiResumableContext,
            isLoading: false,
            refetch: vi.fn(),
        });

        const queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });

        render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter>
                    <PatientDetails />
                </MemoryRouter>
            </QueryClientProvider>
        );

        // Resume All button on ContinueTreatmentCard rendered inside PatientDetails
        const resumeAllBtn = await screen.findByTestId('resume-all-procedures-btn');
        fireEvent.click(resumeAllBtn);

        // 1. PatientDetails.handleResumeTreatment calls startCareSession with plural resume_work_item_ids
        await waitFor(() => {
            expect(mockStartSession).toHaveBeenCalledWith(
                expect.objectContaining({
                    patientId: '123',
                    data: expect.objectContaining({
                        resume_work_item_ids: [101, 102],
                        resume_work_item_id: 101,
                    }),
                })
            );
        });

        // 2. Evaluate template requirements independently:
        // Procedure 102 had NO steps, so its workflow template is applied!
        // Procedure 101 ALREADY had steps, so it was not re-templated!
        await waitFor(() => {
            expect(mockApplyTemplate).toHaveBeenCalledTimes(1);
        });
        expect(mockApplyTemplate).toHaveBeenCalledWith({
            patientId: '123',
            sessionId: 77,
            data: {
                template_code: 'SURG_EXTRACT',
                work_item_id: 102,
            },
        });
    });
});
