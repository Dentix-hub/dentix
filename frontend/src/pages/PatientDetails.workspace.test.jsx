import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from './PatientDetails';

const { mockDeleteTreatment, mockUsePatientTreatments } = vi.hoisted(() => ({
    mockDeleteTreatment: vi.fn(),
    mockUsePatientTreatments: vi.fn(),
}));

vi.mock('../api', async (importOriginal) => ({
    ...(await importOriginal()),
    deleteTreatment: mockDeleteTreatment,
}));

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

vi.mock('@/shared/ui/modals/TreatmentModal', () => ({
    default: ({ isOpen, initialData }) => (
        isOpen ? <div data-testid="treatment-modal-tooth">{initialData?.tooth_number}</div> : null
    ),
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

const mockUsePatientClinicalWorkspace = vi.fn();

vi.mock('@/hooks/usePatientDetails', () => ({
    usePatient: () => ({
        data: { id: 123, name: 'Alice Patient', default_price_list_id: null },
        isLoading: false,
    }),
    usePatientTeeth: () => ({
        data: {},
        isLoading: false,
        refetch: vi.fn(),
    }),
    usePatientClinicalWorkspace: (...args) => mockUsePatientClinicalWorkspace(...args),
    usePatientTreatments: (...args) => mockUsePatientTreatments(...args),
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

describe('PatientDetails Clinical Workspace Tab', () => {
    beforeEach(() => {
        Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
            configurable: true,
            value: vi.fn(),
        });
        mockDeleteTreatment.mockReset();
        mockUsePatientTreatments.mockReturnValue({
            data: [],
            isLoading: false,
            refetch: vi.fn(),
        });
    });

    it('renders loading skeleton when workspace snapshot is loading', () => {
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: null,
            isLoading: true,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        const { container } = renderPatientDetails();

        // Skeleton animation should be present, chart renderer absent
        const skeleton = container.querySelector('.animate-pulse');
        expect(skeleton).toBeInTheDocument();
        expect(container.querySelector('svg[data-layer="crown"]')).toBeNull();
    });

    it('renders error state with retry button and calls refetch on retry click', () => {
        const refetch = vi.fn();
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: null,
            isLoading: false,
            isError: true,
            error: { response: { data: { detail: 'Workspace service unavailable' } } },
            refetch,
        });

        renderPatientDetails();

        const errorBanner = screen.getByTestId('clinical-workspace-error');
        expect(errorBanner).toBeInTheDocument();
        expect(screen.getByText('Failed to load clinical workspace')).toBeInTheDocument();
        expect(screen.getByText('Workspace service unavailable')).toBeInTheDocument();

        const retryButton = screen.getByRole('button', { name: /Retry/i });
        fireEvent.click(retryButton);
        expect(refetch).toHaveBeenCalledTimes(1);
    });

    it('renders read mode badge, domain coverage tags, fallback banner, and empty state', () => {
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: {
                schema_version: 1,
                projection_id: 'cws-snap-123',
                patient_id: 123,
                tenant_id: 1,
                read_mode: 'VNEXT_PRIMARY',
                coverage: {
                    teeth: 'COMPLETE',
                    treatments: 'PARTIAL',
                    sessions: 'UNCOVERED',
                },
                warnings: [],
                teeth: {},
                work_items: [],
                generated_at: '2026-09-08T12:00:00Z',
                effective_at: '2026-09-08T12:00:00Z',
            },
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        renderPatientDetails();

        // Read mode badge
        const readModeBadge = screen.getByTestId('clinical-workspace-read-mode');
        expect(readModeBadge).toBeInTheDocument();
        expect(readModeBadge.textContent).toBe('VNEXT_PRIMARY');

        // Coverage tags
        const coverageContainer = screen.getByTestId('clinical-workspace-coverage');
        expect(coverageContainer).toBeInTheDocument();
        expect(coverageContainer.textContent).toContain('teeth:COMPLETE');
        expect(coverageContainer.textContent).toContain('treatments:PARTIAL');
        expect(coverageContainer.textContent).toContain('sessions:UNCOVERED');

        // Fallback notice banner (treatments is PARTIAL)
        const fallbackBanner = screen.getByTestId('clinical-workspace-fallback-banner');
        expect(fallbackBanner).toBeInTheDocument();
        expect(fallbackBanner.textContent).toContain('Displaying clinical records with legacy fallback contribution.');

        // Empty state banner
        const emptyBanner = screen.getByTestId('clinical-workspace-empty');
        expect(emptyBanner).toBeInTheDocument();
        expect(emptyBanner.textContent).toContain('No clinical events or work items recorded for this patient yet.');
    });

    it('renders clinical warnings panel when unclassified warnings are present', () => {
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: {
                schema_version: 1,
                projection_id: 'cws-snap-123',
                patient_id: 123,
                tenant_id: 1,
                read_mode: 'SHADOW',
                coverage: {
                    teeth: 'COMPLETE',
                    treatments: 'COMPLETE',
                    sessions: 'COMPLETE',
                },
                warnings: [
                    {
                        code: 'UNSUPPORTED_CLINICAL_CODE',
                        message: "Unsupported legacy procedure 'Complete Denture' preserved as unclassified warning.",
                        source_kind: 'treatment',
                        source_id: 88,
                    },
                ],
                teeth: {
                    '16': {
                        tooth_key: '16',
                        procedures: [
                            {
                                visual_id: 've-16-rest',
                                code: 'REST_COMPOSITE',
                                phase: 'completed',
                                targets: [{ kind: 'tooth', tooth_key: '16' }],
                            },
                        ],
                    },
                },
                work_items: [],
                generated_at: '2026-09-08T12:00:00Z',
                effective_at: '2026-09-08T12:00:00Z',
            },
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        const { container } = renderPatientDetails();

        // Read mode badge: SHADOW
        const readModeBadge = screen.getByTestId('clinical-workspace-read-mode');
        expect(readModeBadge.textContent).toBe('SHADOW');

        // Warnings panel
        const warningsPanel = screen.getByTestId('clinical-workspace-warnings');
        expect(warningsPanel).toBeInTheDocument();
        expect(warningsPanel.textContent).toContain('[UNSUPPORTED_CLINICAL_CODE]');
        expect(warningsPanel.textContent).toContain("Unsupported legacy procedure 'Complete Denture'");

        // Chart renderer renders the 32 teeth
        const crowns = container.querySelectorAll('svg[data-layer="crown"]');
        expect(crowns).toHaveLength(32);
    });

    it('renders LEGACY_ONLY read mode correctly', () => {
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: {
                schema_version: 1,
                projection_id: 'cws-snap-123',
                patient_id: 123,
                tenant_id: 1,
                read_mode: 'LEGACY_ONLY',
                coverage: {
                    teeth: 'UNCOVERED',
                    treatments: 'UNCOVERED',
                    sessions: 'UNCOVERED',
                },
                warnings: [],
                teeth: {},
                work_items: [],
            },
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        renderPatientDetails();

        const readModeBadge = screen.getByTestId('clinical-workspace-read-mode');
        expect(readModeBadge.textContent).toBe('LEGACY_ONLY');
    });

    it('opens treatment entry with the renderer FDI tooth unchanged', () => {
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: {
                schema_version: 1,
                projection_id: 'cws-snap-123',
                patient_id: 123,
                tenant_id: 1,
                read_mode: 'VNEXT_PRIMARY',
                coverage: { teeth: 'COMPLETE', treatments: 'PARTIAL', sessions: 'UNCOVERED' },
                warnings: [],
                teeth: {},
                work_items: [],
            },
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        const { container } = renderPatientDetails();
        const tooth16 = container.querySelector('svg[data-layer="crown"][data-tooth-key="16"]');
        expect(tooth16).not.toBeNull();

        fireEvent.click(tooth16);

        expect(screen.getByTestId('treatment-modal-tooth')).toHaveTextContent('UR6');
    });

    it('refreshes history and clinical workspace after deleting a treatment', async () => {
        const refetchWorkspace = vi.fn().mockResolvedValue({});
        const refetchHistory = vi.fn().mockResolvedValue({});
        mockDeleteTreatment.mockResolvedValue({});
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: {
                schema_version: 1,
                projection_id: 'cws-snap-123',
                patient_id: 123,
                tenant_id: 1,
                read_mode: 'VNEXT_PRIMARY',
                coverage: { teeth: 'COMPLETE', treatments: 'PARTIAL', sessions: 'UNCOVERED' },
                warnings: [],
                teeth: {},
                work_items: [],
            },
            isLoading: false,
            isError: false,
            error: null,
            refetch: refetchWorkspace,
        });
        mockUsePatientTreatments.mockReturnValue({
            data: [{
                id: 77,
                date: '2026-01-01T00:00:00Z',
                tooth_number: 16,
                diagnosis: 'Caries',
                procedure: 'Root canal',
                status: 'Done',
            }],
            isLoading: false,
            refetch: refetchHistory,
        });
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

        renderPatientDetails();
        fireEvent.click(screen.getByText('patients.tabs.history'));
        const procedure = await screen.findByText('Root canal');
        const rowButtons = within(procedure.closest('tr')).getAllByRole('button');
        fireEvent.click(rowButtons[1]);

        await waitFor(() => {
            expect(mockDeleteTreatment).toHaveBeenCalledWith(77);
            expect(refetchHistory).toHaveBeenCalledTimes(1);
            expect(refetchWorkspace).toHaveBeenCalledTimes(1);
        });
        confirmSpy.mockRestore();
    });
});
