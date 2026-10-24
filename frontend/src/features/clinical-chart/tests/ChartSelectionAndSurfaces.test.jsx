import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from '@/pages/PatientDetails';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
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

vi.mock('@/features/clinical-chart/components/QuickTreatmentSheet', () => ({
    default: ({ isOpen, initialData }) => (
        isOpen ? (
            <div data-testid="treatment-modal">
                <span data-testid="treatment-modal-tooth">{initialData?.tooth_number}</span>
                <span data-testid="treatment-modal-surfaces">{(initialData?.surfaces || []).join(',')}</span>
                <span data-testid="treatment-modal-surface">{initialData?.surface}</span>
                <span data-testid="treatment-modal-target-kind">{initialData?.target_kind}</span>
            </div>
        ) : null
    ),
}));

vi.mock('@/shared/ui/modals/PrescriptionModal', () => ({
    default: () => null,
}));

vi.mock('@/shared/ui/modals/PaymentModal', () => ({
    default: () => null,
}));

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
    useCreatePayment: () => ({ mutate: vi.fn() }),
    useDeletePayment: () => ({ mutate: vi.fn() }),
    useTenantFeatures: () => ({ data: [], isLoading: false }),
    usePatientClinicalPlans: () => ({ data: [], isLoading: false }),
    useActiveCareSession: () => ({ data: null, isLoading: false, refetch: vi.fn() }),
    useResumableCareSession: () => ({ data: { has_resumable: false, items: [] }, isLoading: false, refetch: vi.fn() }),
    useStartCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useFinishCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useTransitionCareSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateCareSessionStep: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useApplyCareSessionTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRecordCareObservation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/features/patients/hooks/useTreatmentOperations', () => ({
    useTreatmentOperations: () => ({
        handleSaveTreatment: vi.fn(),
    }),
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

describe('Chart Selection, Multi-Select, and Direct Surface Interaction (S08)', () => {
    it('selects Tooth 16 visually with aria-pressed and data-selected="true" and displays chairside inspector', () => {
        const { container } = renderPatientDetails();

        const tooth16 = container.querySelector('[data-layer="crown"][data-tooth-key="16"]');
        expect(tooth16).toBeInTheDocument();
        expect(tooth16).toHaveAttribute('data-selected', 'false');

        // Click tooth 16
        fireEvent.click(tooth16);

        // Visually selected with data-selected="true" and aria-pressed="true"
        expect(tooth16).toHaveAttribute('data-selected', 'true');
        expect(tooth16).toHaveAttribute('aria-pressed', 'true');

        // Chairside selection bar and inspector are rendered
        expect(screen.getByTestId('chairside-selection-bar')).toBeInTheDocument();
        const inspector = screen.getByTestId('clinical-chart-inspector');
        expect(inspector).toBeInTheDocument();
        expect(inspector).toHaveTextContent('16');
    });

    it('accumulates surfaces M and O on Tooth 16 and opens QuickTreatmentSheet pre-populated upon Record Treatment', () => {
        const { container } = renderPatientDetails();

        // 1. Select tooth 16
        const tooth16 = container.querySelector('[data-layer="crown"][data-tooth-key="16"]');
        fireEvent.click(tooth16);

        // 2. Toggle surfaces M and O via surface pill bar
        const pillM = screen.getByTestId('surface-pill-M');
        const pillO = screen.getByTestId('surface-pill-O');

        fireEvent.click(pillM);
        fireEvent.click(pillO);

        expect(pillM).toHaveAttribute('aria-pressed', 'true');
        expect(pillO).toHaveAttribute('aria-pressed', 'true');

        // Surfaces on SVG crown should also reflect selection
        const crownM = container.querySelector('[data-tooth-key="16"] [data-surface-code="M"]');
        const crownO = container.querySelector('[data-tooth-key="16"] [data-surface-code="O"]');
        expect(crownM).toHaveAttribute('data-selected', 'true');
        expect(crownO).toHaveAttribute('data-selected', 'true');

        // 3. Click Record Treatment
        const recordBtn = screen.getByTestId('record-treatment-button');
        fireEvent.click(recordBtn);

        // QuickTreatmentSheet is open and pre-populated with Tooth 16 (Palmer UR6) and surfaces M, O
        expect(screen.getByTestId('treatment-modal')).toBeInTheDocument();
        expect(screen.getByTestId('treatment-modal-tooth')).toHaveTextContent('UR6');
        expect(screen.getByTestId('treatment-modal-surfaces')).toHaveTextContent('M,O');
        expect(screen.getByTestId('treatment-modal-surface')).toHaveTextContent('MO');
        expect(screen.getByTestId('treatment-modal-target-kind')).toHaveTextContent('surface');
    });

    it('selects multiple teeth (14, 15, 16) in multi-select mode and clears cleanly', () => {
        const { container } = renderPatientDetails();

        // Turn on multi-select
        const multiToggle = screen.getByTestId('chart-multi-select-toggle');
        fireEvent.click(multiToggle);
        expect(multiToggle).toHaveAttribute('aria-pressed', 'true');

        // Click teeth 14, 15, 16
        const tooth14 = container.querySelector('[data-layer="crown"][data-tooth-key="14"]');
        const tooth15 = container.querySelector('[data-layer="crown"][data-tooth-key="15"]');
        const tooth16 = container.querySelector('[data-layer="crown"][data-tooth-key="16"]');

        fireEvent.click(tooth14);
        fireEvent.click(tooth15);
        fireEvent.click(tooth16);

        // All 3 teeth are selected
        expect(tooth14).toHaveAttribute('data-selected', 'true');
        expect(tooth15).toHaveAttribute('data-selected', 'true');
        expect(tooth16).toHaveAttribute('data-selected', 'true');

        // Badges are present
        expect(screen.getByTestId('selected-tooth-badge-14')).toBeInTheDocument();
        expect(screen.getByTestId('selected-tooth-badge-15')).toBeInTheDocument();
        expect(screen.getByTestId('selected-tooth-badge-16')).toBeInTheDocument();

        // Clear selection
        const clearBtn = screen.getByTestId('clear-selection-button');
        fireEvent.click(clearBtn);

        // Selection bar is hidden and all teeth unselected
        expect(screen.queryByTestId('chairside-selection-bar')).not.toBeInTheDocument();
        expect(tooth14).toHaveAttribute('data-selected', 'false');
        expect(tooth15).toHaveAttribute('data-selected', 'false');
        expect(tooth16).toHaveAttribute('data-selected', 'false');
    });

    it('directly clicking surfaces on the SVG crown selects the tooth and toggles surface', () => {
        const { container } = renderPatientDetails();

        // Click surface M on tooth 16 directly on crown
        const crownM = container.querySelector('[data-tooth-key="16"] [data-surface-code="M"]');
        expect(crownM).not.toBeNull();
        fireEvent.click(crownM);

        const tooth16 = container.querySelector('[data-layer="crown"][data-tooth-key="16"]');
        expect(tooth16).toHaveAttribute('data-selected', 'true');
        expect(crownM).toHaveAttribute('data-selected', 'true');

        // Chairside selection bar is open with Tooth 16 active and surface M active
        expect(screen.getByTestId('chairside-selection-bar')).toBeInTheDocument();
        expect(screen.getByTestId('surface-pill-M')).toHaveAttribute('aria-pressed', 'true');
    });

    it('supports Shift+click desktop modifier for multi-tooth selection', () => {
        const { container } = renderPatientDetails();

        const tooth11 = container.querySelector('[data-layer="crown"][data-tooth-key="11"]');
        const tooth12 = container.querySelector('[data-layer="crown"][data-tooth-key="12"]');

        fireEvent.click(tooth11);
        expect(tooth11).toHaveAttribute('data-selected', 'true');

        // Hold Shift and click tooth 12
        fireEvent.keyDown(window, { key: 'Shift', shiftKey: true });
        fireEvent.click(tooth12);
        fireEvent.keyUp(window, { key: 'Shift' });

        expect(tooth11).toHaveAttribute('data-selected', 'true');
        expect(tooth12).toHaveAttribute('data-selected', 'true');
    });
});
