import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from '@/pages/PatientDetails';
import * as api from '@/api';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback, options) => {
            let str = (typeof fallback === 'string')
                ? fallback
                : (fallback && typeof fallback === 'object' && fallback.defaultValue)
                    ? fallback.defaultValue
                    : key;
            const params = (options && typeof options === 'object')
                ? options
                : (fallback && typeof fallback === 'object' ? fallback : null);
            if (params && typeof str === 'string') {
                Object.entries(params).forEach(([k, v]) => {
                    str = str.replace(new RegExp(`{{${k}}}`, 'g'), String(v));
                });
            }
            return str;
        },
        i18n: { language: 'en' },
    }),
}));

vi.mock('react-router-dom', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useParams: () => ({ id: '101' }),
        useSearchParams: () => [new URLSearchParams(), vi.fn()],
        useNavigate: () => vi.fn(),
    };
});

const mockProcedures = [
    {
        id: 1,
        name: 'حشو كومبوزيت -- Composite Filling Class I',
        canonical_code: 'REST_COMPOSITE',
        price: 600,
        suggestedMaterials: [
            { id: 201, name: 'Composite Tube', quantity: 1, unit: 'pc' },
        ],
    },
    {
        id: 2,
        name: 'Custom Whitening Procedure',
        canonical_code: null,
        price: 800,
        suggestedMaterials: [],
    },
];

vi.mock('@/shared/context/ProceduresContext', () => ({
    useProcedures: () => ({
        procedures: mockProcedures,
        loading: false,
    }),
}));

vi.mock('@/api', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        createPatientClinicalProcedure: vi.fn().mockResolvedValue({ id: 10 }),
        createPatientClinicalProceduresBulk: vi.fn().mockResolvedValue({}),
        createPatientClinicalFinding: vi.fn().mockResolvedValue({ id: 11 }),
        createPatientClinicalFindingsBulk: vi.fn().mockResolvedValue({}),
        updateToothStatus: vi.fn().mockResolvedValue({}),
        createTreatment: vi.fn().mockResolvedValue({ id: 12 }),
        getProcedurePrices: vi.fn().mockResolvedValue({
            data: {
                price_lists: [
                    { price_list_id: 5, final_price: 550 },
                ],
            },
        }),
    };
});

let mockTenantFeatures = [];

vi.mock('@/hooks/usePatientDetails', () => ({
    usePatient: () => ({
        data: { id: 101, name: 'Ahmad Test', default_price_list_id: 5 },
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
        refetch: vi.fn(),
    }),
    useCreatePayment: () => ({ mutateAsync: vi.fn() }),
    useDeletePayment: () => ({ mutateAsync: vi.fn() }),
    useTenantFeatures: () => ({ data: mockTenantFeatures, isLoading: false }),
    usePatientClinicalPlans: () => ({ data: [], isLoading: false }),
    useCreatePatientClinicalPlan: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useAddPatientClinicalPlanPhase: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useAddPatientClinicalPlanItem: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useRemovePatientClinicalPlanItem: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useTransitionPatientClinicalPlan: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useActiveCareSession: () => ({ data: null, isLoading: false, refetch: vi.fn() }),
    useResumableCareSession: () => ({ data: { has_resumable: false, items: [] }, isLoading: false, refetch: vi.fn() }),
    useStartCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useFinishCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useTransitionCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useApplyCareSessionTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRecordCareObservation: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useStartRctSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useResumableContext: () => ({ data: null, isLoading: false }),
    useResumeTreatment: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useDeleteClinicalAttachment: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUploadClinicalAttachment: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRefetchClinicalAttachments: () => vi.fn(),
}));

vi.mock('@/features/clinical-plans/TreatmentPlansCard', () => ({
    default: () => null,
}));

const renderPatientDetails = () => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={queryClient}>
            <MemoryRouter initialEntries={['/patients/101']}>
                <PatientDetails />
            </MemoryRouter>
        </QueryClientProvider>
    );
};

const getTooth = (container, key) =>
    container.querySelector(`[data-layer="crown"][data-tooth-key="${key}"]`);

describe('U1 & S36: Chart Quick Entry Hand-off & Multi-State Flows', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        mockTenantFeatures = [];
    });

    it('5. Flow B Hand-off: opens QuickTreatmentSheet with exact clinic name, price list resolved, and BOM loaded', async () => {
        // Native writes OFF (default)
        mockTenantFeatures = [];
        const { container } = renderPatientDetails();

        // Click Tooth 16
        const tooth16 = getTooth(container, '16');
        fireEvent.click(tooth16);

        // Click Composite procedure card
        const compositeCard = screen.getByTestId('chart-quick-action-item-REST_COMPOSITE');
        fireEvent.click(compositeCard);

        // Surface prompt opens -> confirm default 'O'
        expect(screen.getByTestId('surface-prompt-popover')).toBeInTheDocument();
        fireEvent.click(screen.getByTestId('confirm-action-button'));

        // QuickTreatmentSheet is now open with exact clinic name
        await waitFor(() => {
            expect(screen.getByTestId('quick-treatment-sheet')).toBeInTheDocument();
            expect(screen.getByTestId('quick-treatment-sheet-procedure-name')).toHaveTextContent(
                'حشو كومبوزيت -- Composite Filling Class I'
            );
        });

        // Price list resolved via resolver (patient default_price_list_id=5 -> 550)
        await waitFor(() => {
            const costInput = screen.getByTestId('quick-treatment-cost-input');
            expect(costInput.value).toBe('550');
        });

        // Tooth chip shows FDI '16' and Palmer 'UR6'
        const toothChip = screen.getByTestId('quick-treatment-tooth-chip');
        expect(toothChip).toHaveAttribute('data-palmer-tooth', 'UR6');
        expect(toothChip).toHaveAttribute('data-fdi-tooth', '16');

        // Surface chip shows 'O'
        expect(screen.getByTestId('quick-treatment-surface-chip-O')).toBeInTheDocument();

        // BOM summary shows 1 material will be deducted
        expect(screen.getByTestId('quick-treatment-bom-summary')).toHaveTextContent(/1 materials will be deducted/i);

        // Save treatment directly from sheet
        const saveBtn = screen.getByTestId('quick-treatment-save-button');
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(api.createTreatment).toHaveBeenCalledTimes(1);
        });

        const postBody = api.createTreatment.mock.calls[0][0];
        // Invariant: prefill_source is stripped from the POST body
        expect(postBody).not.toHaveProperty('prefill_source');
        expect(postBody.procedure).toBe('حشو كومبوزيت -- Composite Filling Class I');
        expect(postBody.cost).toBe(550);
        expect(postBody.tooth_number).toBe(16);
    });

    it('6. Flow A: with canonical code dispatches to G7 endpoint; with code=null falls back to Flow B QuickTreatmentSheet', async () => {
        // Native writes ON
        mockTenantFeatures = ['clinical_vnext_native_writes'];
        const { container } = renderPatientDetails();

        // 6a: Canonical code item -> dispatches to G7 native endpoint
        const tooth16 = getTooth(container, '16');
        fireEvent.click(tooth16);

        const compositeCard = screen.getByTestId('chart-quick-action-item-REST_COMPOSITE');
        fireEvent.click(compositeCard);

        // Confirm surface prompt
        fireEvent.click(screen.getByTestId('confirm-action-button'));

        await waitFor(() => {
            expect(api.createPatientClinicalProcedure).toHaveBeenCalledWith(
                '101',
                expect.objectContaining({
                    code: 'REST_COMPOSITE',
                    targets: expect.arrayContaining([
                        expect.objectContaining({ tooth_key: '16', target_kind: 'surface', surface_code: 'O' }),
                    ]),
                })
            );
        });

        // 6b: Custom procedure with code=null -> falls back to Flow B QuickTreatmentSheet (R01/PD02)
        const customCard = screen.getByTestId('chart-quick-action-item-proc:2');
        fireEvent.click(customCard);

        await waitFor(() => {
            expect(screen.getByTestId('quick-treatment-sheet')).toBeInTheDocument();
            expect(screen.getByTestId('quick-treatment-sheet-procedure-name')).toHaveTextContent(
                'Custom Whitening Procedure'
            );
        });
    });

    it('7. Launcher renders and functions in all 4 rollout states: native OFF, native ON, shadow ON, legacy-only', () => {
        const states = [
            [], // native OFF, shadow OFF (legacy only)
            ['clinical_vnext_shadow'], // shadow ON
            ['clinical_vnext_native_writes'], // native ON
            ['clinical_vnext_shadow', 'clinical_vnext_native_writes'], // shadow ON, native ON
        ];

        for (const featureState of states) {
            mockTenantFeatures = featureState;
            const { unmount } = renderPatientDetails();

            // Quick launcher must render properly in every state
            const quickToolsToggle = screen.getByTestId('chart-quick-tool-toggle');
            expect(quickToolsToggle).toBeInTheDocument();
            fireEvent.click(quickToolsToggle);

            expect(screen.getByTestId('chart-quick-action-launcher')).toBeInTheDocument();
            expect(screen.getByTestId('chart-quick-action-item-REST_COMPOSITE')).toBeInTheDocument();
            unmount();
        }
    });
});
