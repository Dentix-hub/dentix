import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from '@/pages/PatientDetails';
import { useAuthStore } from '@/store/auth.store';
import { getPatientClinicalWorkItems } from '@/api/patients';

const {
    mockRecord, mockFinish, mockFlush, mockDiscard,
    mockStartSession,
    mockApplyTemplate,
    mockUpdateStep,
    mockUseResumableCareSession,
    mockUseActiveCareSession,
    mockUseTenantFeatures,
    mockToastError,
} = vi.hoisted(() => ({
    mockRecord: vi.fn(), mockFinish: vi.fn(), mockFlush: vi.fn(), mockDiscard: vi.fn(),
    mockStartSession: vi.fn(),
    mockApplyTemplate: vi.fn(),
    mockUpdateStep: vi.fn(),
    mockUseResumableCareSession: vi.fn(),
    mockUseActiveCareSession: vi.fn(() => ({ data: null, isLoading: false, refetch: vi.fn() })),
    mockUseTenantFeatures: vi.fn(),
    mockToastError: vi.fn(),
}));

vi.mock('@/shared/ui', async (original) => {
    const actual = await original();
    return {
        ...actual,
        toast: Object.assign(vi.fn(), actual.toast || {}, {
            error: mockToastError,
            success: vi.fn(),
            info: vi.fn(),
        }),
    };
});

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 1, role: 'doctor', permissions: ['clinical:write'] },
    }),
}));

vi.mock('@/api/patients', async (original) => ({
    ...await original(),
    getPatientCareSessions: vi.fn().mockResolvedValue({ data: [] }),
    getPatientClinicalWorkItems: vi.fn(),
}));

vi.mock('@/api/labs', async (original) => ({
    ...await original(),
    getLaboratories: vi.fn().mockResolvedValue({ data: [] }),
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
    useTenantFeatures: (...args) => mockUseTenantFeatures(...args),
    usePatientClinicalPlans: () => ({ data: [], isLoading: false }),
    useActiveCareSession: (...args) => mockUseActiveCareSession(...args),
    useResumableCareSession: (...args) => mockUseResumableCareSession(...args),
    useStartCareSession: () => ({
        mutateAsync: mockStartSession,
        isPending: false,
    }),
    useFinishCareSession: () => ({ mutateAsync: mockFinish, isPending: false }),
    useTransitionCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: mockUpdateStep, isPending: false }),
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

function renderActivePatient(session = {}) {
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
            ...session,
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
    beforeEach(() => {
        Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() });
        getPatientClinicalWorkItems.mockResolvedValue({
            data: [{
                id: 101, kind: 'procedure', code: 'ENDO_RCT', status: 'active',
                targets: [{ target_kind: 'canal', tooth_key: '46', root_id: 'mesial', canal_id: 'MB' }],
            }],
        });
        useAuthStore.setState({ user: { id: 1, role: 'doctor', permissions: ['clinical:write'] } });
        mockUseTenantFeatures.mockReturnValue({ data: ['clinical_vnext_native_writes'], refetch: vi.fn(), isLoading: false });
    });

    it.each([false, true])('passes effective native availability (%s) to the history recording entry point', async (enabled) => {
        mockUseTenantFeatures.mockReturnValue({ data: enabled ? ['clinical_vnext_native_writes'] : [], refetch: vi.fn(), isLoading: false });
        renderActivePatient();
        fireEvent.click(screen.getByRole('tab', { name: /patients.tabs.history/ }));
        const record = await screen.findByTestId('record-past-visit-btn');
        if (enabled) expect(record).toBeEnabled();
        else expect(record).toBeDisabled();
    });

    it('persists the selected procedure and measured length through real workspace and patient handler', async () => {
        renderActivePatient();
        fireEvent.click(await screen.findByTestId('btn-open-active-workflow'));
        fireEvent.change(await screen.findByTestId('input-length-MB'), { target: { value: '21.5' } });
        fireEvent.change(screen.getByTestId('input-taper-MB'), { target: { value: '0.06' } });
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        await waitFor(() => expect(mockRecord).toHaveBeenCalledTimes(1));
        expect(mockRecord.mock.calls[0][0].data).toMatchObject({
            work_item_id: 101,
            structured_value: { length_mm: 21.5, taper: 0.06 },
        });
    });

    it('loads the linked lab procedure when the chart projection lacks that procedure', async () => {
        getPatientClinicalWorkItems.mockResolvedValueOnce({
            data: [{
                id: 202, kind: 'procedure', code: 'PROS_CROWN', status: 'active',
                targets: [{ target_kind: 'tooth', tooth_key: '21' }],
            }],
        });
        renderActivePatient({
            procedures: [{ id: 12, work_item_id: 202, work_item_status: 'active' }],
            steps: [{ id: 5, work_item_id: 202, step_code: 'impression_scan', status: 'completed' }],
        });
        fireEvent.click(await screen.findByTestId('btn-banner-finish-session'));
        await waitFor(() => expect(screen.getByTestId('open-lab-handoff-button')).toBeEnabled());
        expect(getPatientClinicalWorkItems).toHaveBeenCalledWith('123');
        fireEvent.click(screen.getByTestId('open-lab-handoff-button'));
        expect(await screen.findByTestId('tooth-number-input')).toHaveValue('21');
    });

    it('keeps the finish sheet and typed notes when draft flushing fails', async () => {
        renderActivePatient();
        mockFlush.mockRejectedValueOnce(new Error('Network unavailable'));
        fireEvent.click(await screen.findByTestId('btn-banner-finish-session'));
        fireEvent.change(screen.getByTestId('finish-session-notes-input'), { target: { value: 'Keep these clinical notes' } });
        fireEvent.click(screen.getByTestId('confirm-finish-session-button'));
        await waitFor(() => expect(mockFlush).toHaveBeenCalledTimes(1));
        expect(mockFinish).not.toHaveBeenCalled();
        expect(mockDiscard).not.toHaveBeenCalled();
        expect(screen.getByTestId('finish-session-notes-input')).toHaveValue('Keep these clinical notes');
    });

    it('keeps measurement notes available to retry after the server rejects a save', async () => {
        renderActivePatient();
        mockRecord.mockRejectedValueOnce(new Error('Network unavailable'));
        fireEvent.click(await screen.findByTestId('btn-open-active-workflow'));
        fireEvent.change(screen.getByTestId('input-length-MB'), { target: { value: '21.5' } });
        fireEvent.change(screen.getByTestId('input-notes-MB'), { target: { value: 'Calcified canal' } });
        fireEvent.click(screen.getByTestId('save-canal-measurements'));
        await waitFor(() => expect(mockRecord).toHaveBeenCalledTimes(1));
        expect(screen.getByTestId('input-notes-MB')).toHaveValue('Calcified canal');
    });

    it('flushes unsaved documentation before requesting finalization and draft deletion', async () => {
        renderActivePatient();
        fireEvent.click(await screen.findByTestId('btn-banner-finish-session'));
        fireEvent.click(await screen.findByTestId('confirm-finish-session-button'));
        await waitFor(() => expect(mockFinish).toHaveBeenCalledTimes(1));
        expect(mockFlush).toHaveBeenCalledTimes(1);
        expect(mockFlush.mock.invocationCallOrder[0]).toBeLessThan(mockFinish.mock.invocationCallOrder[0]);
    });

    it('sends object payload on Confirm Skip and safely formats FastAPI 422 array errors without crashing', async () => {
        mockUpdateStep.mockReset();
        mockToastError.mockReset();
        mockUpdateStep
            .mockRejectedValueOnce({
                response: {
                    status: 422,
                    data: {
                        detail: [
                            { type: 'model_attributes_type', loc: ['body'], msg: 'Input should be a valid dictionary', input: 'skipped' },
                        ],
                    },
                },
            })
            .mockResolvedValueOnce({ data: { id: 501, status: 'skipped' } });

        renderActivePatient({
            steps: [
                { id: 501, work_item_id: 101, title: 'Rubber Dam Placement', status: 'pending' },
            ],
        });

        fireEvent.click(await screen.findByTestId('btn-open-active-workflow'));
        fireEvent.click(await screen.findByTestId('btn-skip-step-501'));
        fireEvent.change(screen.getByTestId('input-skip-step-reason'), {
            target: { value: 'Teeth isolation modified' },
        });

        // First attempt rejects with FastAPI 422 array -> toast receives formatted string and page remains interactive
        fireEvent.click(screen.getByTestId('btn-confirm-skip-step'));
        await waitFor(() => expect(mockUpdateStep).toHaveBeenCalledTimes(1));
        expect(mockUpdateStep.mock.calls[0][0].data).toEqual({
            status: 'skipped',
            notes: 'Teeth isolation modified',
        });
        await waitFor(() => {
            expect(mockToastError).toHaveBeenCalledWith('Input should be a valid dictionary');
        });
        expect(screen.getByTestId('input-skip-step-reason')).toHaveValue('Teeth isolation modified');

        // Retry succeeds cleanly
        fireEvent.click(screen.getByTestId('btn-confirm-skip-step'));
        await waitFor(() => expect(mockUpdateStep).toHaveBeenCalledTimes(2));
    });
});
