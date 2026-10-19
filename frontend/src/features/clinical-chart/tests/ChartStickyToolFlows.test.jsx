import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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

let mockTenantFeatures = ['clinical_vnext_native_writes'];

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
    useCreatePayment: () => ({ mutateAsync: vi.fn() }),
    useDeletePayment: () => ({ mutateAsync: vi.fn() }),
    useTenantFeatures: () => ({ data: mockTenantFeatures, isLoading: false }),
    usePatientClinicalPlans: () => ({ data: [], isLoading: false }),
    useActiveCareSession: () => ({ data: null, isLoading: false, refetch: vi.fn() }),
    useStartCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useFinishCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useApplyCareSessionTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRecordCareObservation: () => ({ mutateAsync: vi.fn(), isPending: false }),
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
    updateToothStatus: vi.fn().mockResolvedValue({ success: true }),
    deleteTreatment: vi.fn().mockResolvedValue({ success: true }),
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
    createPrescription: vi.fn(),
    updatePatient: vi.fn(),
}));

import { MemoryRouter } from 'react-router-dom';

const renderPatientDetails = () => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={queryClient}>
            <MemoryRouter>
                <PatientDetails />
            </MemoryRouter>
        </QueryClientProvider>
    );
};

const getTooth = (container, key) =>
    container.querySelector(`[data-layer="crown"][data-tooth-key="${key}"]`);

describe('S10 — Tooth-First Flow, Procedure-First Flow & Sticky Tool Mode (G8-M03, G8-M04, G8-M05)', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        mockTenantFeatures = ['clinical_vnext_native_writes'];
    });

    it('G8-M03: Tooth-First Flow <= 2 clicks (select tooth -> click launcher action)', async () => {
        const { container } = renderPatientDetails();

        // 1. Click tooth 16 on chart to select it
        const tooth16 = getTooth(container, '16');
        expect(tooth16).toBeInTheDocument();
        fireEvent.click(tooth16);

        // Chairside selection bar and quick action launcher appear
        expect(screen.getByTestId('chairside-selection-bar')).toBeInTheDocument();
        expect(screen.getByTestId('chart-quick-action-launcher')).toBeInTheDocument();

        // 2. Click a whole-tooth procedure (e.g. Crown: PROS_CROWN)
        // With Tooth 16 selected, clicking Crown applies in 1 click (<= 2 clicks total)
        const crownCard = screen.getByTestId('chart-quick-action-item-PROS_CROWN');
        fireEvent.click(crownCard);

        await waitFor(() => {
            expect(api.createPatientClinicalProcedure).toHaveBeenCalledWith(
                '123',
                expect.objectContaining({
                    code: 'PROS_CROWN',
                    targets: [{ tooth_key: '16', target_kind: 'tooth' }],
                })
            );
        });
    });

    it('G8-M04: Procedure-First Flow (activate tool first -> click tooth on chart to apply)', async () => {
        const { container } = renderPatientDetails();

        // No tooth is selected yet.
        expect(screen.queryByTestId('chairside-selection-bar')).not.toBeInTheDocument();

        // Open quick tools using toolbar button
        const quickToolsToggle = screen.getByTestId('chart-quick-tool-toggle');
        fireEvent.click(quickToolsToggle);

        expect(screen.getByTestId('chart-quick-action-launcher')).toBeInTheDocument();

        // Click Dental Caries (finding) in launcher when no tooth is selected
        const cariesCard = screen.getByTestId('chart-quick-action-item-CARIES');
        fireEvent.click(cariesCard);

        // Sticky tool mode activates and banner appears above chart
        const banner = screen.getByTestId('chart-sticky-tool-banner');
        expect(banner).toBeInTheDocument();
        expect(banner).toHaveTextContent('Dental Caries');

        // Now click tooth 26 on chart -> Caries is applied immediately
        const tooth26 = getTooth(container, '26');
        expect(tooth26).toBeInTheDocument();
        fireEvent.click(tooth26);

        await waitFor(() => {
            expect(api.createPatientClinicalFinding).toHaveBeenCalledWith(
                '123',
                expect.objectContaining({
                    code: 'CARIES',
                    targets: expect.arrayContaining([
                        expect.objectContaining({ tooth_key: '26' }),
                    ]),
                })
            );
        });

        // Applied count reflects 1 applied action
        expect(screen.getByTestId('sticky-applied-count')).toHaveTextContent('1');
    });

    it('G8-M05: Sticky Tool Mode applies across 3 sequential tooth clicks (16, 26, 36) in 3 clicks', async () => {
        const { container } = renderPatientDetails();

        // Open quick tools and activate sticky mode via dedicated sticky toggle button
        fireEvent.click(screen.getByTestId('chart-quick-tool-toggle'));
        const stickyBtn = screen.getByTestId('sticky-toggle-CARIES');
        fireEvent.click(stickyBtn);

        // Banner visible
        expect(screen.getByTestId('chart-sticky-tool-banner')).toBeInTheDocument();

        // Click tooth 16
        fireEvent.click(getTooth(container, '16'));
        await waitFor(() => {
            expect(api.createPatientClinicalFinding).toHaveBeenCalledTimes(1);
        });

        // Click tooth 26
        fireEvent.click(getTooth(container, '26'));
        await waitFor(() => {
            expect(api.createPatientClinicalFinding).toHaveBeenCalledTimes(2);
        });

        // Click tooth 36
        fireEvent.click(getTooth(container, '36'));
        await waitFor(() => {
            expect(api.createPatientClinicalFinding).toHaveBeenCalledTimes(3);
        });

        // Applied count updates to 3
        expect(screen.getByTestId('sticky-applied-count')).toHaveTextContent('3');

        // Exit sticky mode via exit button
        const exitBtn = screen.getByTestId('exit-sticky-mode-button');
        fireEvent.click(exitBtn);

        expect(screen.queryByTestId('chart-sticky-tool-banner')).not.toBeInTheDocument();
    });

    it('G8-M05: Pressing Esc key immediately exits sticky mode', async () => {
        renderPatientDetails();

        // Open quick tools and activate sticky mode
        fireEvent.click(screen.getByTestId('chart-quick-tool-toggle'));
        fireEvent.click(screen.getByTestId('sticky-toggle-CARIES'));

        expect(screen.getByTestId('chart-sticky-tool-banner')).toBeInTheDocument();

        // Press Escape key
        fireEvent.keyDown(window, { key: 'Escape' });

        expect(screen.queryByTestId('chart-sticky-tool-banner')).not.toBeInTheDocument();
    });

    it('G8-M05: Mobile touch scroll safety suppresses accidental click during touchmove', async () => {
        const { container } = renderPatientDetails();

        // Activate sticky mode
        fireEvent.click(screen.getByTestId('chart-quick-tool-toggle'));
        fireEvent.click(screen.getByTestId('sticky-toggle-CARIES'));
        expect(screen.getByTestId('chart-sticky-tool-banner')).toBeInTheDocument();

        const tooth16 = getTooth(container, '16');

        // Simulate touch scroll (start -> move > 8px -> end -> synthesized click)
        fireEvent.touchStart(tooth16, {
            touches: [{ clientX: 100, clientY: 100 }],
        });
        fireEvent.touchMove(tooth16, {
            touches: [{ clientX: 100, clientY: 150 }], // 50px vertical scroll
        });
        fireEvent.touchEnd(tooth16);

        // Synthesized click should be ignored
        fireEvent.click(tooth16);

        expect(api.createPatientClinicalFinding).not.toHaveBeenCalled();

        // But a clean tap without scroll (move <= 8px or no move) works
        fireEvent.touchStart(tooth16, {
            touches: [{ clientX: 100, clientY: 100 }],
        });
        fireEvent.touchEnd(tooth16);
        fireEvent.click(tooth16);

        await waitFor(() => {
            expect(api.createPatientClinicalFinding).toHaveBeenCalledTimes(1);
        });
    });

    it('G8-M05: Banner surface toggle allows modifying surfaces for subsequent clicks', async () => {
        const { container } = renderPatientDetails();

        // Activate a surface-capable tool in sticky mode (REST_COMPOSITE)
        fireEvent.click(screen.getByTestId('chart-quick-tool-toggle'));
        fireEvent.click(screen.getByTestId('sticky-toggle-REST_COMPOSITE'));

        expect(screen.getByTestId('chart-sticky-tool-banner')).toBeInTheDocument();

        // Toggle M surface in banner
        const surfM = screen.getByTestId('sticky-surface-pill-M');
        fireEvent.click(surfM);

        // Click tooth 16
        fireEvent.click(getTooth(container, '16'));

        await waitFor(() => {
            expect(api.createPatientClinicalProcedure).toHaveBeenCalledWith(
                '123',
                expect.objectContaining({
                    code: 'REST_COMPOSITE',
                    targets: expect.arrayContaining([
                        expect.objectContaining({ tooth_key: '16', surface_code: 'M' }),
                    ]),
                })
            );
        });
    });

    it('Legacy compatibility: when native writes are disabled, finding uses updateToothStatus', async () => {
        mockTenantFeatures = []; // native writes OFF
        const { container } = renderPatientDetails();

        fireEvent.click(screen.getByTestId('chart-quick-tool-toggle'));
        fireEvent.click(screen.getByTestId('sticky-toggle-CARIES'));

        fireEvent.click(getTooth(container, '16'));

        await waitFor(() => {
            expect(api.updateToothStatus).toHaveBeenCalledWith(
                expect.objectContaining({
                    patient_id: 123,
                    tooth_number: 16,
                    condition: 'Decayed',
                })
            );
        });
    });
});
