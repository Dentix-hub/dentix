import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import QuickTreatmentSheet from '../components/QuickTreatmentSheet';
import TreatmentModal from '@/shared/ui/modals/TreatmentModal';
import { buildTreatmentPayload } from '@/features/patients/utils/buildTreatmentPayload';
import { palmerToFdi } from '@/utils/toothUtils';
import PatientDetails from '@/pages/PatientDetails';
import * as api from '@/api';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => {
            if (typeof fallback === 'string') return fallback;
            if (fallback && typeof fallback === 'object' && fallback.defaultValue) {
                return fallback.defaultValue;
            }
            return key;
        },
        i18n: { language: 'ar' },
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
        chart_style: { template: 'REST_COMPOSITE', color_key: 'green' },
        suggestedMaterials: [
            { id: 201, name: 'Composite Tube', quantity: 1.5, unit: 'g' },
        ],
    },
    {
        id: 2,
        name: 'حشوة تجميلي خاص',
        canonical_code: null,
        price: 850,
        chart_style: { template: 'REST_COMPOSITE', color_key: 'orange' },
        suggestedMaterials: [],
    },
    {
        id: 3,
        name: 'طقم مرن غير مسعر',
        canonical_code: 'PROS_DENTURE',
        price: 0,
        chart_style: { template: 'MARKER', color_key: 'teal' },
        suggestedMaterials: [],
    },
];

vi.mock('@/shared/context/ProceduresContext', () => ({
    useProcedures: () => ({
        procedures: mockProcedures,
        loading: false,
    }),
}));

vi.mock('@/api/inventory', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getStockSummary: vi.fn().mockResolvedValue({ data: [] }),
        getMaterials: vi.fn().mockResolvedValue({ data: [] }),
        getActiveSessions: vi.fn().mockResolvedValue({ data: [] }),
    };
});

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
        updateTreatment: vi.fn().mockResolvedValue({ id: 12 }),
        getProcedurePrices: vi.fn().mockImplementation(async (procId) => {
            if (procId === 2) {
                return { data: { price_lists: [] } };
            }
            return {
                data: {
                    price_lists: [
                        { price_list_id: 5, final_price: 550 },
                    ],
                },
            };
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

/**
 * Reference implementation of the original inline payload construction in `TreatmentModal.handleSave`
 * (pre-U4D extraction) to verify 100% golden parity across >= 6 input shapes.
 */
function originalModalHandleSavePayload(
    treatment,
    { consumedMaterials = [], safeProcedures = [], isEditing = false, forceSkipStock = false } = {},
) {
    const cleanedMaterials = (consumedMaterials || [])
        .map((m) => ({
            material_id: m.material_id || m.id,
            quantity: Number.isFinite(parseFloat(m.quantity)) ? parseFloat(m.quantity) : 1,
            session_id: m.session_id || null,
            weight_score: Number.isFinite(parseFloat(m.weight_score))
                ? parseFloat(m.weight_score)
                : (Number.isFinite(parseFloat(m.weight)) ? parseFloat(m.weight) : 1.0),
            is_manual_override: m.is_manual_override || false,
            material_type: m.material_type || null,
            category_id: m.category_id || null,
        }))
        .filter((m) => m.quantity > 0 && m.material_id);

    const surfaceList = Array.isArray(treatment.surfaces) && treatment.surfaces.length > 0
        ? treatment.surfaces
        : (treatment.surface ? String(treatment.surface).replace(/[^A-Za-z]/g, '').toUpperCase().split('') : []);
    const surfaceStr = surfaceList.join('') || treatment.surface || null;
    const targetKind = surfaceList.length > 0 ? 'surface' : (treatment.target_kind || 'tooth');

    return {
        ...treatment,
        patient_id: treatment.patient_id,
        doctor_id: treatment.doctor_id,
        tooth_number: palmerToFdi(treatment.tooth_number) || null,
        surface: surfaceStr,
        surfaces: surfaceList.length > 0 ? surfaceList : undefined,
        target_kind: targetKind,
        clinical_work_item_id: !isEditing && treatment.clinical_work_item_id ? treatment.clinical_work_item_id : undefined,
        procedure_id: safeProcedures.find((p) => p.name === treatment.procedure)?.id,
        cost: parseFloat(treatment.cost) || 0,
        discount: parseFloat(treatment.discount) || 0,
        status: treatment.status || 'Done',
        notes: treatment.notes,
        canal_count: !isNaN(parseInt(treatment.canal_count)) ? parseInt(treatment.canal_count, 10) : null,
        sessions: treatment.sessions,
        complications: treatment.complications,
        consumedMaterials: cleanedMaterials,
        skip_stock_check: forceSkipStock,
    };
}

describe('U4D #1: buildTreatmentPayload Golden Contract Parity (7 Input Shapes + Sheet vs Modal)', () => {
    const inputShapes = [
        {
            label: '1. Surface restoration with array surfaces and numeric cost',
            treatment: {
                date: '2026-10-21',
                patient_id: 101,
                doctor_id: 7,
                tooth_number: 'UR6',
                surfaces: ['M', 'O'],
                surface: 'MO',
                target_kind: 'surface',
                procedure: 'حشو كومبوزيت -- Composite Filling Class I',
                cost: 550,
                discount: 0,
                status: 'Done',
                notes: 'Clean margins',
                canal_count: '',
                sessions: '',
                complications: '',
            },
            context: {
                consumedMaterials: [{ material_id: 201, quantity: 1.5, unit: 'g' }],
                procedures: mockProcedures,
                isEditing: false,
                forceSkipStock: false,
            },
        },
        {
            label: '2. Whole-tooth procedure without surfaces and string cost/discount',
            treatment: {
                date: '2026-10-21',
                patient_id: 101,
                doctor_id: 7,
                tooth_number: 'UL1',
                surfaces: [],
                surface: '',
                target_kind: 'tooth',
                procedure: 'حشوة تجميلي خاص',
                cost: '850.5',
                discount: '50',
                status: 'Pending',
                notes: '',
                canal_count: '3',
                sessions: '2',
                complications: 'None',
            },
            context: {
                consumedMaterials: [],
                procedures: mockProcedures,
                isEditing: false,
                forceSkipStock: false,
            },
        },
        {
            label: '3. String-only surface ("mod") without surfaces array + BOM weight fallback',
            treatment: {
                date: '2026-10-21',
                patient_id: 101,
                tooth_number: 'LL6',
                surface: 'mod',
                procedure: 'حشو كومبوزيت -- Composite Filling Class I',
                cost: '',
                discount: '',
                status: '',
            },
            context: {
                consumedMaterials: [
                    { id: 301, quantity: '2', weight: '0.75', is_manual_override: true },
                    { id: 302, quantity: 0 }, // filtered out
                ],
                procedures: mockProcedures,
                isEditing: false,
                forceSkipStock: false,
            },
        },
        {
            label: '4. Missing status and empty cost defaults to Done and 0',
            treatment: {
                date: '2026-10-21',
                tooth_number: '',
                procedure: 'Unknown Manual Procedure',
                cost: null,
                discount: undefined,
                status: undefined,
            },
            context: {
                consumedMaterials: [],
                procedures: mockProcedures,
                isEditing: false,
                forceSkipStock: false,
            },
        },
        {
            label: '5. Create mode with clinical_work_item_id present (U2 plan link)',
            treatment: {
                date: '2026-10-21',
                patient_id: 101,
                tooth_number: 'UR6',
                surfaces: ['O'],
                procedure: 'حشو كومبوزيت -- Composite Filling Class I',
                cost: 600,
                discount: 0,
                status: 'Done',
                clinical_work_item_id: 9001,
            },
            context: {
                consumedMaterials: [],
                procedures: mockProcedures,
                isEditing: false,
                forceSkipStock: false,
            },
        },
        {
            label: '6. Edit mode strips clinical_work_item_id and preserves skip_stock_check=true',
            treatment: {
                id: 55,
                date: '2026-10-21',
                patient_id: 101,
                tooth_number: 'UR6',
                surfaces: ['O'],
                procedure: 'حشو كومبوزيت -- Composite Filling Class I',
                cost: 600,
                discount: 25,
                status: 'Done',
                clinical_work_item_id: 9001,
            },
            context: {
                consumedMaterials: [{ material_id: 201, quantity: 1 }],
                procedures: mockProcedures,
                isEditing: true,
                forceSkipStock: true,
            },
        },
    ];

    it.each(inputShapes)('matches original TreatmentModal payload byte-for-byte for $label', ({ treatment, context }) => {
        const actual = buildTreatmentPayload(treatment, context);
        const expected = originalModalHandleSavePayload(treatment, {
            consumedMaterials: context.consumedMaterials,
            safeProcedures: context.procedures,
            isEditing: context.isEditing,
            forceSkipStock: context.forceSkipStock,
        });
        expect(actual).toEqual(expected);
    });

    it('produces deep-equal POST bodies when saving identical inputs through QuickTreatmentSheet vs TreatmentModal', async () => {
        const sheetSave = vi.fn().mockResolvedValue({});
        const modalSave = vi.fn().mockResolvedValue({});

        const sharedInitialData = {
            date: '2026-10-21',
            diagnosis: '',
            procedure: 'حشو كومبوزيت -- Composite Filling Class I',
            cost: '',
            discount: '',
            tooth_number: 'UR6',
            surface: 'MO',
            surfaces: ['M', 'O'],
            target_kind: 'surface',
            canal_count: '',
            canals: [{ name: '', length: '' }],
            sessions: '',
            complications: '',
            notes: '',
            default_price_list_id: 5,
            prefill_source: 'quick_launcher',
        };

        const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

        // 1. Save via QuickTreatmentSheet
        const { unmount: unmountSheet } = render(
            <QueryClientProvider client={queryClient}>
                <QuickTreatmentSheet
                    isOpen={true}
                    onClose={vi.fn()}
                    onSave={sheetSave}
                    onOpenDetails={vi.fn()}
                    initialData={sharedInitialData}
                    procedures={mockProcedures}
                />
            </QueryClientProvider>,
        );

        await waitFor(() => {
            expect(screen.getByTestId('quick-treatment-cost-input').value).toBe('550');
        });
        fireEvent.click(screen.getByTestId('quick-treatment-save-button'));
        await waitFor(() => {
            expect(sheetSave).toHaveBeenCalledTimes(1);
        });
        unmountSheet();

        // 2. Save via TreatmentModal
        const { unmount: unmountModal } = render(
            <QueryClientProvider client={queryClient}>
                <TreatmentModal
                    isOpen={true}
                    onClose={vi.fn()}
                    onSave={modalSave}
                    initialData={sharedInitialData}
                    isEditing={false}
                    procedures={mockProcedures}
                />
            </QueryClientProvider>,
        );

        await waitFor(() => {
            expect(screen.getByLabelText(/التكلفة/i).value).toBe('550');
        });
        fireEvent.click(screen.getByRole('button', { name: 'حفظ' }));
        await waitFor(() => {
            expect(modalSave).toHaveBeenCalledTimes(1);
        });
        unmountModal();

        expect(sheetSave.mock.calls[0][0]).toEqual(modalSave.mock.calls[0][0]);
    });
});

describe('U4D #2–#4: QuickTreatmentSheet — Editing, BOM Visibility, Double-Tap Guard & Escalation Paths', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('1. edits price and toggles status (Done / Pending), hides BOM when 0 materials, shows unpriced hint when price=0, and Cancel makes 0 requests', async () => {
        const onSave = vi.fn().mockResolvedValue({});
        const onClose = vi.fn();

        const initialUnpriced = {
            date: '2026-10-21',
            procedure: 'طقم مرن غير مسعر',
            cost: 0,
            discount: 0,
            tooth_number: 'UR6',
            surfaces: [],
            surface: '',
            target_kind: 'tooth',
            prefill_source: 'quick_launcher',
        };

        render(
            <QuickTreatmentSheet
                isOpen={true}
                onClose={onClose}
                onSave={onSave}
                onOpenDetails={vi.fn()}
                initialData={initialUnpriced}
                procedures={mockProcedures}
            />,
        );

        // Header shows procedure name + teal swatch
        expect(screen.getByTestId('quick-treatment-sheet-procedure-name')).toHaveTextContent('طقم مرن غير مسعر');
        expect(screen.getByTestId('quick-treatment-sheet-swatch')).toHaveAttribute('data-color-key', 'teal');

        // Price is 0 -> "غير مسعّر" hint is visible, and no BOM summary is rendered
        expect(screen.getByTestId('quick-treatment-unpriced-hint')).toBeInTheDocument();
        expect(screen.queryByTestId('quick-treatment-bom-summary')).not.toBeInTheDocument();

        // Cancel makes no save request
        fireEvent.click(screen.getByTestId('quick-treatment-cancel-button'));
        expect(onClose).toHaveBeenCalledTimes(1);
        expect(onSave).not.toHaveBeenCalled();

        // Edit price to 1250 -> unpriced hint disappears
        fireEvent.change(screen.getByTestId('quick-treatment-cost-input'), {
            target: { value: '1250' },
        });
        expect(screen.queryByTestId('quick-treatment-unpriced-hint')).not.toBeInTheDocument();

        // Toggle status to Pending (قيد التنفيذ)
        fireEvent.click(screen.getByTestId('quick-treatment-status-Pending'));
        expect(screen.getByTestId('quick-treatment-status-Pending')).toHaveAttribute('aria-pressed', 'true');

        // Save sends updated cost=1250 and status='Pending'
        fireEvent.click(screen.getByTestId('quick-treatment-save-button'));
        await waitFor(() => {
            expect(onSave).toHaveBeenCalledWith(
                expect.objectContaining({
                    procedure: 'طقم مرن غير مسعر',
                    cost: 1250,
                    status: 'Pending',
                    tooth_number: 16,
                }),
            );
        });
    });

    it('2. prevents duplicate submissions on rapid double-tap Save', async () => {
        let resolveSave;
        const onSave = vi.fn().mockImplementation(
            () => new Promise((resolve) => {
                resolveSave = resolve;
            }),
        );

        render(
            <QuickTreatmentSheet
                isOpen={true}
                onClose={vi.fn()}
                onSave={onSave}
                onOpenDetails={vi.fn()}
                initialData={{
                    date: '2026-10-21',
                    procedure: 'حشوة تجميلي خاص',
                    cost: 850,
                    tooth_number: 'UR6',
                    surfaces: ['M', 'O'],
                    surface: 'MO',
                    target_kind: 'surface',
                }}
                procedures={mockProcedures}
            />,
        );

        const saveBtn = screen.getByTestId('quick-treatment-save-button');
        fireEvent.click(saveBtn);
        fireEvent.click(saveBtn);

        expect(onSave).toHaveBeenCalledTimes(1);
        resolveSave({});
        await waitFor(() => {
            expect(onSave).toHaveBeenCalledTimes(1);
        });
    });

    it('3. "More details" opens TreatmentModal preserving edited price, status, and resolved BOM materials', async () => {
        const onOpenDetails = vi.fn();
        const onClose = vi.fn();

        render(
            <QuickTreatmentSheet
                isOpen={true}
                onClose={onClose}
                onSave={vi.fn()}
                onOpenDetails={onOpenDetails}
                initialData={{
                    date: '2026-10-21',
                    procedure: 'حشو كومبوزيت -- Composite Filling Class I',
                    cost: '',
                    tooth_number: 'UR6',
                    surfaces: ['M', 'O'],
                    surface: 'MO',
                    target_kind: 'surface',
                    default_price_list_id: 5,
                    prefill_source: 'quick_launcher',
                }}
                procedures={mockProcedures}
            />,
        );

        await waitFor(() => {
            expect(screen.getByTestId('quick-treatment-cost-input').value).toBe('550');
        });

        // Clinician overrides price to 620 and sets status to Pending before clicking More details
        fireEvent.change(screen.getByTestId('quick-treatment-cost-input'), {
            target: { value: '620' },
        });
        fireEvent.click(screen.getByTestId('quick-treatment-status-Pending'));

        fireEvent.click(screen.getByTestId('quick-treatment-more-details-button'));

        expect(onClose).toHaveBeenCalled();
        expect(onOpenDetails).toHaveBeenCalledWith(
            expect.objectContaining({
                procedure: 'حشو كومبوزيت -- Composite Filling Class I',
                cost: '620',
                status: 'Pending',
                surfaces: ['M', 'O'],
                escalated_from_quick_sheet: true,
                consumedMaterials: expect.arrayContaining([
                    expect.objectContaining({ material_id: 201, quantity: 1.5 }),
                ]),
            }),
        );
    });

    it.each([
        [
            'stock shortage error',
            {
                response: {
                    status: 400,
                    data: { detail: 'نقص في مخزون الكومبوزيت (Insufficient stock)' },
                },
                message: 'Stock shortage',
            },
        ],
        [
            'open-session conflict (CONFIRM_OPEN_REQUIRED)',
            {
                response: {
                    status: 409,
                    data: {
                        detail: {
                            code: 'CONFIRM_OPEN_REQUIRED',
                            stock_item_id: 44,
                            material_info: 'Composite Syringe',
                        },
                    },
                },
                message: 'CONFIRM_OPEN_REQUIRED',
            },
        ],
        [
            'clinical plan link error (CLINICAL_LINK_TARGET_MISMATCH)',
            {
                response: {
                    status: 422,
                    data: { detail: 'CLINICAL_LINK_TARGET_MISMATCH' },
                },
                message: 'CLINICAL_LINK_TARGET_MISMATCH',
            },
        ],
    ])('4. escalates %s to TreatmentModal with preserved edits and original error', async (_label, mockError) => {
        const onSave = vi.fn().mockRejectedValue(mockError);
        const onOpenDetails = vi.fn();
        const onClose = vi.fn();

        render(
            <QuickTreatmentSheet
                isOpen={true}
                onClose={onClose}
                onSave={onSave}
                onOpenDetails={onOpenDetails}
                initialData={{
                    date: '2026-10-21',
                    procedure: 'حشو كومبوزيت -- Composite Filling Class I',
                    cost: 550,
                    tooth_number: 'UR6',
                    surfaces: ['M', 'O'],
                    surface: 'MO',
                    target_kind: 'surface',
                }}
                procedures={mockProcedures}
            />,
        );

        // Edit price before saving
        fireEvent.change(screen.getByTestId('quick-treatment-cost-input'), {
            target: { value: '590' },
        });

        fireEvent.click(screen.getByTestId('quick-treatment-save-button'));

        await waitFor(() => {
            expect(onOpenDetails).toHaveBeenCalledWith(
                expect.objectContaining({
                    cost: '590',
                    status: 'Done',
                    escalated_from_quick_sheet: true,
                    escalation_error: mockError,
                }),
            );
        });
        expect(onClose).toHaveBeenCalled();
    });
});

describe('U4D Acceptance & Click-Budget: Tooth 16 Surfaces M+O -> "حشوة تجميلي خاص" -> QuickTreatmentSheet -> Save', () => {
    const renderPatientDetails = () => {
        const queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false } },
        });
        return render(
            <QueryClientProvider client={queryClient}>
                <MemoryRouter initialEntries={['/patients/101']}>
                    <PatientDetails />
                </MemoryRouter>
            </QueryClientProvider>,
        );
    };

    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        mockTenantFeatures = [];
    });

    it('completes surface selection (M, O) -> procedure ("حشوة تجميلي خاص") -> Save in QuickTreatmentSheet with orange swatch and preserves edits on escalation', async () => {
        const { container } = renderPatientDetails();

        // Select Tooth 16 and surfaces M and O on the chart
        const surfaceM = container.querySelector('[data-tooth-key="16"] [data-surface-code="M"]');
        const surfaceO = container.querySelector('[data-tooth-key="16"] [data-surface-code="O"]');
        expect(surfaceM).toBeTruthy();
        expect(surfaceO).toBeTruthy();

        fireEvent.click(surfaceM);
        fireEvent.click(surfaceO);

        // Tap "حشوة تجميلي خاص" (proc:2, chart_style: REST_COMPOSITE + orange)
        // Because surfaces M & O are already selected on Tooth 16, no surface prompt popover is needed!
        const cosmeticCard = screen.getByTestId('chart-quick-action-item-proc:2');
        expect(screen.getByTestId('procedure-color-swatch-proc:2')).toHaveAttribute('data-color-key', 'orange');
        fireEvent.click(cosmeticCard);

        // QuickTreatmentSheet opens immediately (NOT TreatmentModal)
        await waitFor(() => {
            expect(screen.getByTestId('quick-treatment-sheet')).toBeInTheDocument();
        });
        expect(screen.getByTestId('quick-treatment-sheet-swatch')).toHaveAttribute('data-color-key', 'orange');
        expect(screen.getByTestId('quick-treatment-surface-chip-M')).toBeInTheDocument();
        expect(screen.getByTestId('quick-treatment-surface-chip-O')).toBeInTheDocument();

        await waitFor(() => {
            expect(screen.getByTestId('quick-treatment-cost-input').value).toBe('850');
        });

        // Tap Save in the sheet (surfaces -> procedure -> Save = 1 tap after procedure selection)
        fireEvent.click(screen.getByTestId('quick-treatment-save-button'));

        await waitFor(() => {
            expect(api.createTreatment).toHaveBeenCalledTimes(1);
        });

        expect(api.createTreatment).toHaveBeenCalledWith(
            expect.objectContaining({
                patient_id: 101,
                tooth_number: 16,
                procedure: 'حشوة تجميلي خاص',
                procedure_id: 2,
                surface: 'MO',
                surfaces: ['M', 'O'],
                target_kind: 'surface',
                cost: 850,
                discount: 0,
                status: 'Done',
                skip_stock_check: false,
            }),
        );
    });
});
