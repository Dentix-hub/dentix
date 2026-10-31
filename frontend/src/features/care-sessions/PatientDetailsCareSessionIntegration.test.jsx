import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from '@/pages/PatientDetails';

const {
    mockRecord, mockFinish, mockFlush, mockDiscard,
    mockStartSession,
    mockApplyTemplate,
    mockUseResumableCareSession,
    mockUseActiveCareSession,
} = vi.hoisted(() => ({
    mockRecord: vi.fn(), mockFinish: vi.fn(), mockFlush: vi.fn(), mockDiscard: vi.fn(),
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
        data: {
            read_mode: 'LEGACY_ONLY',
            domain_coverage: {},
            warnings: [],
            visual_rules: [],
            work_items: [
                {
                    id: 101,
                    kind: 'procedure',
                    code: 'ENDO_RCT',
                    status: 'active',
                    targets: [{ target_kind: 'canal', tooth_key: '46', root_id: 'mesial', canal_id: 'MB' }],
                },
            ],
        },
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
    useFinishCareSession: () => ({ mutateAsync: mockFinish, isPending: false }),
    useTransitionCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useApplyCareSessionTemplate: () => ({
        mutateAsync: mockApplyTemplate,
        isPending: false,
    }),
    useRecordCareObservation: () => ({ mutateAsync: mockRecord, isPending: false }),
}));

vi.mock('@/features/care-sessions/useCareSessionDraft', () => ({
    useCareSessionDraft: () => ({
        draftData: { proc_notes_101: 'Latest unsaved clinical note' },
        updateDraft: vi.fn(),
        discardDraft: mockDiscard,
        status: 'saving',
        resolveConflict: vi.fn(),
        saveNow: mockFlush,
    }),
}));

function renderActivePatient() {
    mockRecord.mockClear();
    mockFinish.mockClear();
    mockFlush.mockClear();
    mockDiscard.mockClear();
    mockRecord.mockResolvedValue({ data: {} });
    mockFinish.mockResolvedValue({ data: {} });
    mockFlush.mockResolvedValue();
    mockUseActiveCareSession.mockReturnValue({
        data: {
            id: 77,
            patient_id: 123,
            status: 'in_progress',
            procedures: [
                {
                    id: 11,
                    work_item_id: 101,
                    work_item_version_id: 1,
                    work_item_status: 'active',
                    template_snapshot: { custom_fields: [] },
                },
            ],
            steps: [],
            observations: [],
        },
        isLoading: false,
        refetch: vi.fn(),
    });
    mockUseResumableCareSession.mockReturnValue({ data: { has_resumable: false, items: [] }, isLoading: false, refetch: vi.fn() });
    return render(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
            <MemoryRouter>
                <PatientDetails />
            </MemoryRouter>
        </QueryClientProvider>
    );
}

describe('PatientDetails Care Session Integration', () => {
    it('persists the selected procedure and measured length through real workspace and patient handler', async () => {
        renderActivePatient();
        fireEvent.click(await screen.findByTestId('btn-open-active-workflow'));
        fireEvent.change(await screen.findByTestId('input-length-MB'), { target: { value: '21.5' } });
        fireEvent.click(screen.getByTestId('btn-save-measurement-MB'));
        await waitFor(() => expect(mockRecord).toHaveBeenCalledTimes(1));
        expect(mockRecord.mock.calls[0][0].data).toMatchObject({
            work_item_id: 101,
            structured_value: { length_mm: 21.5 },
        });
    });

    it('flushes unsaved documentation before requesting finalization and draft deletion', async () => {
        renderActivePatient();
        fireEvent.click(await screen.findByTestId('btn-banner-finish-session'));
        fireEvent.click(await screen.findByTestId('confirm-finish-session-button'));
        await waitFor(() => expect(mockFinish).toHaveBeenCalledTimes(1));
        expect(mockFlush).toHaveBeenCalledTimes(1);
        expect(mockFlush.mock.invocationCallOrder[0]).toBeLessThan(mockFinish.mock.invocationCallOrder[0]);
    });
});
