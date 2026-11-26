import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import PatientDetails from './PatientDetails';

const {
    mockRoute,
    mockAuthState,
    mockUsePatient,
    mockUsePatientClinicalWorkspace,
    mockRefetchPatient,
    mockSetSearchParams,
} = vi.hoisted(() => ({
    mockRoute: { id: '123', tab: 'chart' },
    mockAuthState: { user: { id: 1, role: 'doctor', tenant_id: 101 } },
    mockUsePatient: vi.fn(),
    mockUsePatientClinicalWorkspace: vi.fn(),
    mockRefetchPatient: vi.fn(),
    mockSetSearchParams: vi.fn(),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback) => (typeof fallback === 'string' ? fallback : key),
        i18n: { language: 'en' },
    }),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({ user: mockAuthState.user }),
}));

vi.mock('@/store/auth.store', () => {
    const fn = (selector) => (selector ? selector({ user: mockAuthState.user }) : { user: mockAuthState.user });
    fn.getState = () => ({ user: mockAuthState.user });
    return { useAuthStore: fn };
});

vi.mock('react-router-dom', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useParams: () => ({ id: mockRoute.id }),
        useSearchParams: () => [new URLSearchParams({ tab: mockRoute.tab }), mockSetSearchParams],
        useNavigate: () => vi.fn(),
    };
});

vi.mock('@/shared/context/ProceduresContext', () => ({
    useProcedures: () => ({ procedures: [], loading: false }),
}));

vi.mock('@/features/patients/modals/EditPatientModal.jsx', () => ({ default: () => null }));
vi.mock('@/features/clinical-chart/components/QuickTreatmentSheet', () => ({ default: () => null }));
vi.mock('@/shared/ui/modals/PrescriptionModal', () => ({ default: () => null }));
vi.mock('@/shared/ui/modals/PaymentModal', () => ({ default: () => null }));

vi.mock('@/features/patients/hooks/useTreatmentOperations', () => ({
    useTreatmentOperations: () => ({ handleSaveTreatment: vi.fn() }),
}));

vi.mock('@/hooks/usePatientDetails', () => ({
    usePatient: (...args) => mockUsePatient(...args),
    usePatientTeeth: () => ({ data: {}, isLoading: false, refetch: vi.fn() }),
    usePatientClinicalWorkspace: (...args) => mockUsePatientClinicalWorkspace(...args),
    usePatientTreatments: () => ({ data: [], isLoading: false, refetch: vi.fn() }),
    usePatientPayments: () => ({ data: [], isLoading: false }),
    usePatientAttachments: () => ({ data: [], isLoading: false, refetch: vi.fn(), isPollingStalled: false }),
    usePatientLabOrders: () => ({ data: [], isLoading: false }),
    useCreatePayment: () => ({ mutateAsync: vi.fn() }),
    useDeletePayment: () => ({ mutateAsync: vi.fn() }),
    useTenantFeatures: () => ({ data: [], isLoading: false, refetch: vi.fn() }),
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

const patientResult = (patient) => ({
    data: patient,
    isLoading: false,
    isError: false,
    error: null,
    refetch: mockRefetchPatient,
});

const errorResult = (error) => ({
    data: undefined,
    isLoading: false,
    isError: true,
    error,
    refetch: mockRefetchPatient,
});

const networkError = { message: 'Network request failed' };
const deniedError = { response: { status: 403, data: { detail: 'Access denied' } } };

function makeQueryClient() {
    return new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: Infinity } },
    });
}

function renderPage(queryClient = makeQueryClient()) {
    const view = render(
        <QueryClientProvider client={queryClient}>
            <MemoryRouter>
                <PatientDetails />
            </MemoryRouter>
        </QueryClientProvider>,
    );
    return { ...view, queryClient };
}

function rerenderPage(rerender, queryClient) {
    rerender(
        <QueryClientProvider client={queryClient}>
            <MemoryRouter>
                <PatientDetails />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

describe('PatientDetails patient identity loading', () => {
    beforeEach(() => {
        mockRoute.id = '123';
        mockRoute.tab = 'chart';
        mockAuthState.user = { id: 1, role: 'doctor', tenant_id: 101 };
        mockRefetchPatient.mockReset();
        mockSetSearchParams.mockReset();
        mockUsePatient.mockReset();
        mockUsePatientClinicalWorkspace.mockReset();
        Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
            configurable: true,
            value: vi.fn(),
        });
        mockUsePatient.mockReturnValue(patientResult({ id: 123, name: 'Synthetic Baseline Patient' }));
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: null,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });
    });

    it('hides identity-dependent UI on direct-tab failure and restores the requested tab after retry', async () => {
        mockRoute.tab = 'history';
        let failed = true;
        mockRefetchPatient.mockImplementation(() => {
            failed = false;
        });
        mockUsePatient.mockImplementation(() => failed
            ? errorResult({ response: { status: 503, data: { detail: 'Synthetic outage' } } })
            : patientResult({ id: 123, name: 'Synthetic Recovered Patient' }));

        const queryClient = makeQueryClient();
        const { rerender } = renderPage(queryClient);

        expect(screen.getByTestId('patient-identity-error')).toBeInTheDocument();
        expect(screen.queryByRole('tab')).not.toBeInTheDocument();
        expect(screen.queryAllByText('Synthetic Recovered Patient')).toHaveLength(0);
        expect(JSON.parse(mockUsePatient.mock.calls.at(-1)?.[1].tenantKey)).toEqual([101, null, 1, 'doctor']);

        fireEvent.click(screen.getByRole('button', { name: /Retry/i }));
        expect(mockRefetchPatient).toHaveBeenCalledTimes(1);

        // The mocked hook has no React Query lifecycle, so refresh its result.
        rerenderPage(rerender, queryClient);

        expect(screen.getAllByText('Synthetic Recovered Patient').length).toBeGreaterThan(0);
        expect(screen.getByRole('tab', { name: 'patients.tabs.history' })).toHaveAttribute('aria-selected', 'true');
        expect(screen.queryByTestId('patient-identity-error')).not.toBeInTheDocument();
    });

    it('keeps valid prior context with localized stale feedback when the same patient refresh fails', async () => {
        mockUsePatient.mockReturnValue({
            ...patientResult({ id: 123, name: 'Synthetic Cached Patient' }),
            isError: true,
            error: networkError,
        });
        mockUsePatientClinicalWorkspace.mockReturnValue({
            data: null,
            isLoading: false,
            isError: true,
            error: { response: { data: { detail: 'Synthetic chart outage' } } },
            refetch: vi.fn(),
        });

        renderPage();

        expect(screen.getAllByText('Synthetic Cached Patient').length).toBeGreaterThan(0);
        const staleBanner = screen.getByTestId('patient-identity-stale');
        expect(staleBanner).toHaveTextContent('Showing previously loaded patient information');
        fireEvent.click(within(staleBanner).getByRole('button', { name: 'Retry' }));
        expect(mockRefetchPatient).toHaveBeenCalledTimes(1);

        expect(screen.getByTestId('clinical-workspace-error')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('tab', { name: 'patients.tabs.history' }));
        await waitFor(() => {
            expect(screen.getByRole('tab', { name: 'patients.tabs.history' })).toHaveAttribute('aria-selected', 'true');
        });
        // The chart error is isolated to the chart surface; the other tabs stay usable.
        expect(screen.queryByTestId('clinical-workspace-error')).not.toBeVisible();
    });

    it('drops prior clinical content immediately on patient and tenant transitions', () => {
        mockUsePatient.mockImplementation((patientId, options) => patientResult({
            id: Number(patientId),
            name: `Synthetic Patient ${patientId} Tenant ${JSON.parse(options.tenantKey)[0]}`,
        }));
        const queryClient = makeQueryClient();
        const { rerender } = renderPage(queryClient);

        expect(screen.getAllByText('Synthetic Patient 123 Tenant 101').length).toBeGreaterThan(0);

        // A route or tenant change restarts identity resolution; the previous
        // patient's chart and tabs must disappear before the new one resolves.
        const loadingResult = { data: undefined, isLoading: true, isError: false, error: null, refetch: mockRefetchPatient };
        mockRoute.id = '456';
        mockUsePatient.mockReturnValue(loadingResult);
        rerenderPage(rerender, queryClient);

        expect(screen.queryAllByText('Synthetic Patient 123 Tenant 101')).toHaveLength(0);
        expect(screen.queryByRole('tab')).not.toBeInTheDocument();
        expect(mockUsePatient.mock.calls.at(-1)?.[0]).toBe('456');

        mockAuthState.user = { id: 1, role: 'doctor', tenant_id: 202 };
        rerenderPage(rerender, queryClient);

        expect(screen.queryAllByText('Synthetic Patient 123 Tenant 101')).toHaveLength(0);
        expect(JSON.parse(mockUsePatient.mock.calls.at(-1)?.[1].tenantKey)[0]).toBe(202);

        mockUsePatient.mockReturnValue(patientResult({ id: 456, name: 'Synthetic Patient 456 Tenant 202' }));
        rerenderPage(rerender, queryClient);

        expect(screen.getAllByText('Synthetic Patient 456 Tenant 202').length).toBeGreaterThan(0);
        expect(screen.getByRole('tab', { name: 'patients.tabs.chart' })).toBeInTheDocument();
    });

    it('never restores denied clinical content after retry or remount', async () => {
        const stalePatient = { id: 123, name: 'Synthetic Denied Patient' };
        let phase = 'denied';
        mockRefetchPatient.mockImplementation(() => {
            phase = 'transient';
        });
        mockUsePatient.mockImplementation(() => (phase === 'denied'
            ? { ...errorResult(deniedError), data: stalePatient }
            : { ...errorResult(networkError), data: stalePatient }));

        const queryClient = makeQueryClient();
        const { unmount } = renderPage(queryClient);

        expect(screen.queryByText('Synthetic Denied Patient')).not.toBeInTheDocument();
        expect(screen.queryByRole('tab')).not.toBeInTheDocument();
        expect(screen.getByTestId('patient-identity-error')).toHaveTextContent('You no longer have access to this patient');

        fireEvent.click(screen.getByRole('button', { name: /Retry/i }));
        await waitFor(() => expect(mockRefetchPatient).toHaveBeenCalledTimes(1));
        expect(screen.queryByText('Synthetic Denied Patient')).not.toBeInTheDocument();
        expect(screen.getByTestId('patient-identity-error')).toBeInTheDocument();

        unmount();
        renderPage(queryClient);

        expect(screen.queryByText('Synthetic Denied Patient')).not.toBeInTheDocument();
        expect(screen.queryByRole('tab')).not.toBeInTheDocument();
        expect(screen.getByTestId('patient-identity-error')).toBeInTheDocument();
    });
});
