import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from '@/pages/PatientDetails';
import { useAuthStore } from '@/store/auth.store';
import { toast } from '@/shared/ui';

const { mockAddCareSessionProcedure } = vi.hoisted(() => ({
    mockAddCareSessionProcedure: vi.fn(),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 1, role: 'doctor', permissions: ['clinical:write'] },
    }),
}));

vi.mock('@/api/patients', async (original) => ({
    ...(await original()),
    addCareSessionProcedure: (...args) => mockAddCareSessionProcedure(...args),
    getPatientCareSessions: vi.fn().mockResolvedValue({ data: [] }),
    getPatientClinicalWorkItems: vi.fn().mockResolvedValue({ data: [] }),
}));

vi.mock('@/shared/context/ProceduresContext', () => ({
    useProcedures: () => ({ procedures: [] }),
}));

vi.mock('@/features/patients/modals/EditPatientModal.jsx', () => ({ default: () => null }));
vi.mock('@/shared/ui/modals/PrescriptionModal', () => ({ default: () => null }));
vi.mock('@/shared/ui/modals/PaymentModal', () => ({ default: () => null }));
vi.mock('@/features/clinical-plans/TreatmentPlansCard', () => ({
    default: ({ onPerformItem }) => (
        <button
            type="button"
            data-testid="trigger-plan-item-sheet"
            onClick={() =>
                onPerformItem({
                    item: { work_item_id: 202, work_item: { id: 202, code: 'PROS_CROWN', display_name: 'Crown' } },
                    plan: { id: 1, title: 'Plan A' },
                    toothKey: '21',
                    surfaces: [],
                })
            }
        >
            Perform Plan Item
        </button>
    ),
}));

vi.mock('@/features/clinical-chart/components/QuickTreatmentSheet', () => ({
    default: ({ isOpen, onOpenCareSessions }) =>
        isOpen ? (
            <button type="button" data-testid="mock-open-care-sessions" onClick={onOpenCareSessions}>
                Open Care Sessions
            </button>
        ) : null,
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
    usePatient: () => ({ data: { id: 123, name: 'Synthetic Patient', default_price_list_id: null }, isLoading: false }),
    usePatientTeeth: () => ({ data: {}, isLoading: false, refetch: vi.fn() }),
    usePatientClinicalWorkspace: () => ({
        data: {
            read_mode: 'VNEXT_PRIMARY',
            domain_coverage: {},
            warnings: [],
            visual_rules: [],
            work_items: [
                { id: 101, kind: 'procedure', code: 'ENDO_RCT', status: 'active', targets: [{ tooth_key: '46' }] },
                { id: 202, kind: 'procedure', code: 'PROS_CROWN', status: 'active', targets: [{ tooth_key: '21' }] },
            ],
        },
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
    }),
    usePatientTreatments: () => ({ data: [], isLoading: false, refetch: vi.fn() }),
    usePatientPayments: () => ({ data: [], isLoading: false }),
    usePatientAttachments: () => ({ data: [], isLoading: false, refetch: vi.fn() }),
    usePatientLabOrders: () => ({ data: [], isLoading: false }),
    useCreatePayment: () => ({ mutateAsync: vi.fn() }),
    useDeletePayment: () => ({ mutateAsync: vi.fn() }),
    useTenantFeatures: () => ({
        data: ['clinical_vnext_native_writes', 'clinical_treatment_plans'],
        refetch: vi.fn(),
        isLoading: false,
    }),
    usePatientClinicalPlans: () => ({ data: [], isLoading: false }),
    useActiveCareSession: () => ({
        data: {
            id: 77,
            patient_id: 123,
            status: 'in_progress',
            procedures: [{ id: 1, work_item_id: 101, template_snapshot: { custom_fields: [] } }],
            steps: [],
            observations: [],
        },
        isLoading: false,
        refetch: vi.fn(),
    }),
    useResumableCareSession: () => ({ data: { has_resumable: false, items: [] }, isLoading: false, refetch: vi.fn() }),
    useStartCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useFinishCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useTransitionCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useApplyCareSessionTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRecordCareObservation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/features/care-sessions/useCareSessionDraft', () => ({
    useCareSessionDraft: () => ({
        draftData: {},
        updateDraft: vi.fn(),
        discardDraft: vi.fn(),
        status: 'idle',
        hasUnsavedChanges: false,
        resolveConflict: vi.fn(),
        saveNow: vi.fn(),
    }),
}));

describe('Finding 1 (Entry Point B): PatientDetails QuickTreatmentSheet -> active session Add Procedure error safety', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAuthStore.setState({ user: { id: 1, role: 'doctor', permissions: ['clinical:write'] } });
    });

    it('emits a readable string toast instead of raw 422 array when adding a procedure to active session fails', async () => {
        const toastErrorSpy = vi.spyOn(toast, 'error').mockImplementation(() => {});
        mockAddCareSessionProcedure.mockRejectedValueOnce({
            response: {
                status: 422,
                data: {
                    detail: [
                        { type: 'int_parsing', loc: ['path', 'work_item_id'], msg: 'Input should be a valid integer' },
                    ],
                },
            },
        });

        render(
            <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
                <MemoryRouter>
                    <PatientDetails />
                </MemoryRouter>
            </QueryClientProvider>
        );

        fireEvent.click(screen.getByTestId('trigger-plan-item-sheet'));
        fireEvent.click(await screen.findByTestId('mock-open-care-sessions'));

        await waitFor(() => expect(mockAddCareSessionProcedure).toHaveBeenCalledWith('123', 77, 202));
        await waitFor(() => expect(toastErrorSpy).toHaveBeenCalledTimes(1));
        const toastArg = toastErrorSpy.mock.calls[0][0];
        expect(typeof toastArg).toBe('string');
        expect(toastArg).toContain('Input should be a valid integer');
    });
});
