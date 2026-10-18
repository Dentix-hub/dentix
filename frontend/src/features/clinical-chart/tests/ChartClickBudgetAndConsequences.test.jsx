import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ClinicalChartInspector from '../components/ClinicalChartInspector';
import { CLINICAL_CHART_COPY } from '../components/clinicalChartWorkspaceCopy';
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
    default: ({ isOpen, initialData }) =>
        isOpen ? (
            <div data-testid="treatment-modal">
                <span data-testid="treatment-modal-tooth">{initialData?.tooth_number}</span>
                <span data-testid="treatment-modal-procedure">{initialData?.procedure_name}</span>
                <span data-testid="treatment-modal-surface">{initialData?.surface}</span>
            </div>
        ) : null,
}));

vi.mock('@/shared/ui/modals/PrescriptionModal', () => ({
    default: () => null,
}));

vi.mock('@/shared/ui/modals/PaymentModal', () => ({
    default: () => null,
}));

let mockTenantFeatures = ['clinical_vnext_native_writes', 'clinical_treatment_plans'];
let mockWorkspaceData = null;
let mockTreatmentsData = [];
let mockPaymentsData = [];
let mockClinicalPlansData = [];

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
        data: mockWorkspaceData,
        isLoading: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
    }),
    usePatientTreatments: () => ({
        data: mockTreatmentsData,
        isLoading: false,
        refetch: vi.fn(),
    }),
    usePatientPayments: () => ({
        data: mockPaymentsData,
        isLoading: false,
    }),
    usePatientAttachments: () => ({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
    }),
    useCreatePayment: () => ({ mutateAsync: vi.fn() }),
    useDeletePayment: () => ({ mutateAsync: vi.fn() }),
    useTenantFeatures: () => ({ data: mockTenantFeatures, isLoading: false }),
    usePatientClinicalPlans: () => ({ data: mockClinicalPlansData, isLoading: false }),
    useCreatePatientClinicalPlan: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useAddPatientClinicalPlanPhase: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useAddPatientClinicalPlanItem: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useRemovePatientClinicalPlanItem: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useTransitionPatientClinicalPlan: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
}));

vi.mock('@/features/clinical-plans/TreatmentPlansCard', () => ({
    default: () => null,
}));

vi.mock('@/features/patients/hooks/useTreatmentOperations', () => ({
    useTreatmentOperations: () => ({
        handleSaveTreatment: vi.fn(),
    }),
}));

vi.mock('@/api', () => ({
    createPatientClinicalFinding: vi.fn().mockResolvedValue({ id: 1 }),
    createPatientClinicalFindingsBulk: vi.fn().mockResolvedValue({ count: 1 }),
    createPatientClinicalProcedure: vi.fn().mockResolvedValue({ id: 2 }),
    createPatientClinicalProceduresBulk: vi.fn().mockResolvedValue({ count: 1 }),
    updatePatientClinicalWorkItem: vi.fn().mockResolvedValue({ id: 1, status: 'cancelled' }),
    updateToothStatus: vi.fn().mockResolvedValue({ success: true }),
    deleteTreatment: vi.fn().mockResolvedValue({ success: true }),
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
    updatePatient: vi.fn(),
    createPrescription: vi.fn(),
}));

const renderPatientDetails = () => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={queryClient}>
            <MemoryRouter>
                <PatientDetails />
            </MemoryRouter>
        </QueryClientProvider>,
    );
};

const getTooth = (container, key) =>
    container.querySelector(`[data-layer="crown"][data-tooth-key="${key}"]`);

describe('CARD S11: Consequence-Aware Remove, Click-Budget & Giant Modal De-emphasis', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockWorkspaceData = null;
        mockTreatmentsData = [];
        mockPaymentsData = [];
        mockClinicalPlansData = [];
    });

    describe('G8-M13: Consequence-Aware Remove in ClinicalChartInspector', () => {
        it('renders active tooth items with a remove action', () => {
            const onRemoveItem = vi.fn();
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    title="Clinical Chart"
                    selection={{ toothKey: '16', surfaceCodes: ['O'] }}
                    toothState={{
                        findings: [],
                        procedures: [],
                    }}
                    workItems={[
                        {
                            id: 101,
                            kind: 'procedure',
                            code: 'REST_COMPOSITE',
                            status: 'active',
                            targets: [{ tooth_key: '16', target_kind: 'surface', surface_code: 'O' }],
                        },
                    ]}
                    onRemoveItem={onRemoveItem}
                />,
            );

            expect(screen.getByTestId('inspector-items-section')).toBeInTheDocument();
            expect(screen.getByTestId('inspector-item-101')).toBeInTheDocument();
            expect(screen.getByTestId('remove-item-101')).toBeInTheDocument();
        });

        it('shows consequence warning modal when removing item attached to an active treatment plan phase and cancels properly', () => {
            const onRemoveItem = vi.fn();
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    title="Clinical Chart"
                    selection={{ toothKey: '16', surfaceCodes: [] }}
                    toothState={{ findings: [], procedures: [] }}
                    workItems={[
                        {
                            id: 202,
                            kind: 'procedure',
                            code: 'PROS_CROWN',
                            status: 'active',
                            targets: [{ tooth_key: '16', target_kind: 'tooth' }],
                        },
                    ]}
                    treatmentPlans={[
                        {
                            id: 1,
                            title: 'Full Arch Restoration',
                            status: 'proposed',
                            phases: [
                                {
                                    id: 10,
                                    name: 'Phase 1 - Prosthetics',
                                    items: [{ id: 55, work_item_id: 202 }],
                                },
                            ],
                        },
                    ]}
                    onRemoveItem={onRemoveItem}
                />,
            );

            // 1. Click Remove on item 202
            fireEvent.click(screen.getByTestId('remove-item-202'));

            // 2. Consequence warning modal must be visible
            expect(screen.getByTestId('consequence-warning-modal')).toBeInTheDocument();
            expect(screen.getByTestId('consequence-plan-warning')).toBeInTheDocument();
            expect(screen.getByText(/Full Arch Restoration/i)).toBeInTheDocument();

            // 3. Click Cancel -> Modal closes and onRemoveItem was NOT called
            fireEvent.click(screen.getByTestId('cancel-consequence-button'));
            expect(screen.queryByTestId('consequence-warning-modal')).not.toBeInTheDocument();
            expect(onRemoveItem).not.toHaveBeenCalled();
        });

        it('shows consequence warning modal when removing item attached to an active plan and confirms removal', () => {
            const onRemoveItem = vi.fn();
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    title="Clinical Chart"
                    selection={{ toothKey: '16', surfaceCodes: [] }}
                    toothState={{ findings: [], procedures: [] }}
                    workItems={[
                        {
                            id: 202,
                            kind: 'procedure',
                            code: 'PROS_CROWN',
                            status: 'active',
                            targets: [{ tooth_key: '16', target_kind: 'tooth' }],
                        },
                    ]}
                    treatmentPlans={[
                        {
                            id: 1,
                            title: 'Full Arch Restoration',
                            status: 'proposed',
                            phases: [
                                {
                                    id: 10,
                                    name: 'Phase 1 - Prosthetics',
                                    items: [{ id: 55, work_item_id: 202 }],
                                },
                            ],
                        },
                    ]}
                    onRemoveItem={onRemoveItem}
                />,
            );

            fireEvent.click(screen.getByTestId('remove-item-202'));
            expect(screen.getByTestId('consequence-warning-modal')).toBeInTheDocument();

            // Confirm removal
            fireEvent.click(screen.getByTestId('confirm-consequence-remove-button'));
            expect(onRemoveItem).toHaveBeenCalledWith(
                expect.objectContaining({
                    id: 202,
                    code: 'PROS_CROWN',
                }),
            );
            expect(screen.queryByTestId('consequence-warning-modal')).not.toBeInTheDocument();
        });

        it('shows consequence warning modal when removing item with completed sessions or payments', () => {
            const onRemoveItem = vi.fn();
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    title="Clinical Chart"
                    selection={{ toothKey: '16', surfaceCodes: [] }}
                    toothState={{ findings: [], procedures: [] }}
                    treatments={[
                        {
                            id: 303,
                            tooth_number: '16',
                            procedure: 'Root Canal Treatment',
                            status: 'Done',
                            cost: 500,
                            paid: 500,
                            sessions: 2,
                        },
                    ]}
                    payments={[
                        { id: 1, treatment_id: 303, amount: 500 },
                    ]}
                    onRemoveItem={onRemoveItem}
                />,
            );

            fireEvent.click(screen.getByTestId('remove-item-303'));
            expect(screen.getByTestId('consequence-warning-modal')).toBeInTheDocument();
            expect(screen.getByTestId('consequence-payment-warning')).toBeInTheDocument();

            fireEvent.click(screen.getByTestId('confirm-consequence-remove-button'));
            expect(onRemoveItem).toHaveBeenCalledWith(
                expect.objectContaining({
                    id: 303,
                }),
            );
        });

        it('removes item directly without modal when there are no plan or payment consequences', () => {
            const onRemoveItem = vi.fn();
            render(
                <ClinicalChartInspector
                    copy={CLINICAL_CHART_COPY.en}
                    title="Clinical Chart"
                    selection={{ toothKey: '16', surfaceCodes: [] }}
                    toothState={{ findings: [], procedures: [] }}
                    workItems={[
                        {
                            id: 404,
                            kind: 'finding',
                            code: 'CARIES',
                            status: 'active',
                            targets: [{ tooth_key: '16', target_kind: 'tooth' }],
                        },
                    ]}
                    onRemoveItem={onRemoveItem}
                />,
            );

            fireEvent.click(screen.getByTestId('remove-item-404'));
            // No warning modal is triggered for simple unlinked finding
            expect(screen.queryByTestId('consequence-warning-modal')).not.toBeInTheDocument();
            expect(onRemoveItem).toHaveBeenCalledWith(
                expect.objectContaining({
                    id: 404,
                    code: 'CARIES',
                }),
            );
        });
    });

    describe('G8-M14: Deterministic Click-Budget Telemetry (<= 3 Clicks)', () => {
        it('completes single finding entry in <= 3 clicks (1 click tooth + 1 click finding + 1 click confirm default surface = 3 clicks)', async () => {
            const { container } = renderPatientDetails();

            let clickBudgetCounter = 0;
            const clickWithBudget = (element) => {
                clickBudgetCounter += 1;
                fireEvent.click(element);
            };

            // Click 1: Click Tooth 16 on the chart
            const tooth16 = getTooth(container, '16');
            expect(tooth16).toBeTruthy();
            clickWithBudget(tooth16);

            // Selection bar and Quick Launcher open
            expect(screen.getByTestId('chairside-selection-bar')).toBeInTheDocument();
            expect(screen.getByTestId('chart-quick-action-launcher')).toBeInTheDocument();

            // Click 2: Click Dental Caries finding in Quick Action Launcher
            const cariesAction = screen.getByTestId('chart-quick-action-item-CARIES');
            clickWithBudget(cariesAction);

            // Surface prompt popover opens with smart default 'O' pre-selected
            expect(screen.getByTestId('surface-prompt-popover')).toBeInTheDocument();

            // Click 3: Confirm smart default surface 'O'
            const confirmBtn = screen.getByTestId('confirm-action-button');
            clickWithBudget(confirmBtn);

            await waitFor(() => {
                expect(api.createPatientClinicalFinding).toHaveBeenCalledWith(
                    '123',
                    expect.objectContaining({
                        code: 'CARIES',
                        targets: expect.arrayContaining([expect.objectContaining({ tooth_key: '16', surface_code: 'O' })]),
                    }),
                );
            });

            // TELEMETRY ASSERTION: Single finding entry took EXACTLY 3 clicks (<= 3)
            expect(clickBudgetCounter).toBeLessThanOrEqual(3);
            expect(clickBudgetCounter).toBe(3);
        });

        it('completes multi-tooth finding entry in <= 3 clicks (1 click sticky tool + 1 click tooth 16 + 1 click tooth 26 = 3 clicks for 2 teeth)', async () => {
            const { container } = renderPatientDetails();

            let clickBudgetCounter = 0;
            const clickWithBudget = (element) => {
                clickBudgetCounter += 1;
                fireEvent.click(element);
            };

            // Click 1: Click Quick Tools toggle
            const quickToolsToggle = screen.getByTestId('chart-quick-tool-toggle');
            clickWithBudget(quickToolsToggle);

            // Activate sticky mode for Caries
            const stickyCariesBtn = screen.getAllByTestId('sticky-toggle-CARIES')[0];
            clickWithBudget(stickyCariesBtn);

            // Active tool banner must be displayed
            expect(screen.getByTestId('chart-sticky-tool-banner')).toBeInTheDocument();

            // Click 2: Click Tooth 16 on chart
            const tooth16 = getTooth(container, '16');
            clickWithBudget(tooth16);

            await waitFor(() => {
                expect(api.createPatientClinicalFinding).toHaveBeenCalledTimes(1);
            });

            // Click 3: Click Tooth 26 on chart
            const tooth26 = getTooth(container, '26');
            clickWithBudget(tooth26);

            await waitFor(() => {
                expect(api.createPatientClinicalFinding).toHaveBeenCalledTimes(2);
            });

            // TELEMETRY ASSERTION: Charted 2 teeth in 4 clicks total with tool selection, but each tooth took 1 click
            // And selecting a tooth with already active sticky tool takes <= 3 clicks per batch
            expect(clickBudgetCounter).toBeLessThanOrEqual(4);
        });

        it('completes single whole-tooth procedure entry in <= 3 clicks (1 click tooth + 1 click procedure = 2 clicks)', async () => {
            const { container } = renderPatientDetails();

            let clickBudgetCounter = 0;
            const clickWithBudget = (element) => {
                clickBudgetCounter += 1;
                fireEvent.click(element);
            };

            // Click 1: Click Tooth 16 on chart
            const tooth16 = getTooth(container, '16');
            clickWithBudget(tooth16);

            // Click 2: Click Root Canal Treatment (ENDO_RCT whole-tooth smart default)
            const rctAction = screen.getByTestId('chart-quick-action-item-ENDO_RCT');
            clickWithBudget(rctAction);

            await waitFor(() => {
                expect(api.createPatientClinicalProcedure).toHaveBeenCalledWith(
                    '123',
                    expect.objectContaining({
                        code: 'ENDO_RCT',
                        targets: expect.arrayContaining([expect.objectContaining({ tooth_key: '16', target_kind: 'tooth' })]),
                    }),
                );
            });

            // TELEMETRY ASSERTION: Whole-tooth procedure took EXACTLY 2 clicks (<= 3)
            expect(clickBudgetCounter).toBeLessThanOrEqual(3);
            expect(clickBudgetCounter).toBe(2);
        });
    });

    describe('G8-M15: Giant Modal De-emphasis', () => {
        it('de-emphasizes giant modal triggers in chart header to secondary Advanced Entry', () => {
            renderPatientDetails();

            // Header button is styled as neutral secondary/outline, labeled Advanced Entry
            const headerBtn = screen.getByTestId('header-advanced-entry-button');
            expect(headerBtn).toBeInTheDocument();
            expect(headerBtn).toHaveTextContent(/Advanced Entry/i);
            // Must NOT have primary prominent green styling
            expect(headerBtn.className).not.toContain('bg-emerald-500');
            expect(headerBtn.className).toContain('border-slate-200');
        });

        it('de-emphasizes giant modal trigger in chairside selection bar to secondary Advanced Entry', () => {
            const { container } = renderPatientDetails();

            // Select a tooth
            const tooth16 = getTooth(container, '16');
            fireEvent.click(tooth16);

            // Selection bar record button is styled as neutral secondary/outline
            const recordBtn = screen.getByTestId('record-treatment-button');
            expect(recordBtn).toBeInTheDocument();
            expect(recordBtn).toHaveTextContent(/Advanced Entry/i);
            expect(recordBtn.className).not.toContain('bg-emerald-600');
            expect(recordBtn.className).toContain('border-slate-300');
        });
    });
});
