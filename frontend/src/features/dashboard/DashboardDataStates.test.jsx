import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '@/i18n';
import { api } from '@/api/apiClient';
import AuthContext from '@/auth/useAuth';
import { useTenantStore } from '@/store/tenant.store';
import Dashboard from '@/pages/Dashboard';

// Mock only PatientModal (unrelated modal closed by default) so tests focus on Dashboard data states.
vi.mock('@/features/patients/modals/PatientModal.jsx', () => ({
    default: () => null,
}));

function normalizeText(value) {
    return String(value).replace(/\s+/g, ' ').trim();
}

function formatExpectedEgp(amount, locale) {
    return normalizeText(
        new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: 'EGP',
            maximumFractionDigits: 0,
        }).format(amount),
    );
}

function makeAxiosError(status, message = 'Request failed') {
    const error = new Error(message);
    if (status !== null && status !== undefined) {
        error.response = {
            status,
            data: { detail: message },
        };
    } else {
        error.code = 'ERR_NETWORK';
    }
    return error;
}

const VALID_STATS = {
    new_patients_today: 4,
    total_appointments_today: 6,
    today_received: 1250.6,
    today_outstanding: 5000,
    revenue_chart: [
        { name: '2026-11-20', revenue: 1500 },
        { name: '2026-11-21', revenue: 2400 },
    ],
    business_date: '2026-11-22',
    tenant_timezone: 'Africa/Cairo',
};

const ZERO_STATS = {
    new_patients_today: 0,
    total_appointments_today: 0,
    today_received: 0,
    today_outstanding: 0,
    revenue_chart: [],
    business_date: '2026-11-22',
    tenant_timezone: 'Africa/Cairo',
};

const SAMPLE_APPOINTMENTS = [
    {
        id: 101,
        patient_name: 'Omar Hassan',
        date_time: '2026-11-22T14:00:00',
        status: 'Scheduled',
        notes: 'Crown fitting',
    },
    {
        id: 102,
        patient_name: 'Nadia Adel',
        date_time: '2026-11-22T09:30:00',
        status: 'Completed',
        notes: 'Cleaning',
    },
    {
        id: 103,
        patient_name: 'Tarek Cancelled',
        date_time: '2026-11-22T11:00:00',
        status: 'Cancelled',
        notes: 'Cancelled visit',
    },
    {
        id: 104,
        patient_name: 'Salma Yesterday',
        date_time: '2026-11-21T10:00:00',
        status: 'Waiting',
        notes: 'Previous day',
    },
    {
        id: 105,
        patient_name: 'Youssef Third',
        date_time: '2026-11-22T11:30:00',
        status: 'Waiting',
        notes: 'Checkup',
    },
];

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
                gcTime: 5 * 60 * 1000,
                staleTime: 30 * 1000,
            },
        },
    });
}

function renderDashboard({
    queryClient = createTestQueryClient(),
    user = { id: 1, username: 'dr_sara', role: 'admin', tenant_id: 10 },
    tenant = { id: 10, name: 'Clinic A', plan: 'premium' },
} = {}) {
    useTenantStore.setState({ tenant });

    const authValue = {
        user,
        loading: false,
        isBooting: false,
        isAuthenticated: Boolean(user),
        login: vi.fn(),
        verify2FA: vi.fn(),
        logout: vi.fn(),
        register: vi.fn(),
    };

    const ui = (
        <QueryClientProvider client={queryClient}>
            <AuthContext.Provider value={authValue}>
                <I18nextProvider i18n={i18n}>
                    <MemoryRouter>
                        <Dashboard />
                    </MemoryRouter>
                </I18nextProvider>
            </AuthContext.Provider>
        </QueryClientProvider>
    );

    const rendered = render(ui);
    return {
        ...rendered,
        queryClient,
        rerenderWithSession({ nextUser, nextTenant }) {
            useTenantStore.setState({ tenant: nextTenant });
            const nextAuthValue = {
                ...authValue,
                user: nextUser,
                isAuthenticated: Boolean(nextUser),
            };
            rendered.rerender(
                <QueryClientProvider client={queryClient}>
                    <AuthContext.Provider value={nextAuthValue}>
                        <I18nextProvider i18n={i18n}>
                            <MemoryRouter>
                                <Dashboard />
                            </MemoryRouter>
                        </I18nextProvider>
                    </AuthContext.Provider>
                </QueryClientProvider>,
            );
        },
    };
}

describe('Dashboard data states', () => {
    beforeEach(async () => {
        await i18n.changeLanguage('en');
        sessionStorage.clear();
        useTenantStore.getState().clearTenant();
        vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function () {
            const width = this.tagName === 'SPAN' ? this.textContent.length * 7 : 600;
            const height = this.tagName === 'SPAN' ? 14 : 260;
            return { width, height, top: 0, left: 0, bottom: height, right: width };
        });
        vi.stubGlobal('ResizeObserver', class {
            constructor(callback) { this.callback = callback; }
            observe() { this.callback([{ contentRect: { width: 600, height: 260 } }]); }
            unobserve() {}
            disconnect() {}
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        sessionStorage.clear();
    });

    it('isolates stats first failure from valid appointments, avoids fabricated zeros, and retries only stats', async () => {
        let statsAttempts = 0;
        let apptAttempts = 0;
        let failStats = true;

        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                statsAttempts += 1;
                if (failStats) {
                    throw makeAxiosError(500, 'Stats service unavailable');
                }
                return { data: VALID_STATS };
            }
            if (url === '/api/v1/appointments') {
                apptAttempts += 1;
                return { data: SAMPLE_APPOINTMENTS };
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        renderDashboard();

        // Stats sections show specific stats error and NO fabricated zeros or empty schedule/0%
        await waitFor(() => {
            expect(screen.getByTestId('dashboard-stats-error')).toBeInTheDocument();
        });
        expect(screen.getByTestId('dashboard-revenue-error')).toBeInTheDocument();
        expect(screen.getByTestId('dashboard-today-error')).toBeInTheDocument();
        expect(screen.getByTestId('dashboard-efficiency-error')).toBeInTheDocument();

        expect(screen.queryByText('EGP 0')).not.toBeInTheDocument();
        expect(screen.queryByText('0 Appointments')).not.toBeInTheDocument();
        expect(screen.queryByText('No remaining appointments today')).not.toBeInTheDocument();
        expect(screen.queryByText('0%')).not.toBeInTheDocument();

        // Status distribution chart depends ONLY on appointments and must still render!
        await waitFor(() => {
            expect(screen.getByText('Completed')).toBeInTheDocument();
        });

        // Retry only stats
        failStats = false;
        const retryStatsBtn = within(screen.getByTestId('dashboard-stats-error')).getByRole('button');
        fireEvent.click(retryStatsBtn);

        await waitFor(() => {
            expect(screen.getByText('Nadia Adel')).toBeInTheDocument();
        });

        expect(statsAttempts).toBe(2);
        expect(apptAttempts).toBe(1);
        // 1 completed out of 3 non-cancelled today (Nadia, Youssef, Omar) => Math.round(1/3 * 100) = 33%
        expect(screen.getByText('33%')).toBeInTheDocument();
        expect(screen.getByText('3 Appointments')).toBeInTheDocument();
    });

    it('isolates appointments first failure from valid stats and retries only appointments', async () => {
        let statsAttempts = 0;
        let apptAttempts = 0;
        let failAppts = true;

        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                statsAttempts += 1;
                return { data: VALID_STATS };
            }
            if (url === '/api/v1/appointments') {
                apptAttempts += 1;
                if (failAppts) {
                    throw makeAxiosError(503, 'Appointments temporarily unavailable');
                }
                return { data: SAMPLE_APPOINTMENTS };
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        renderDashboard();

        // Stats KPI cards render even though appointments failed
        const expectedIncome = formatExpectedEgp(VALID_STATS.today_received, 'en-EG');

        await waitFor(() => {
            expect(screen.getByText(expectedIncome)).toBeInTheDocument();
        });
        expect(screen.getByTestId('dashboard-status-error')).toBeInTheDocument();
        expect(screen.getByTestId('dashboard-today-error')).toBeInTheDocument();
        expect(screen.getByTestId('dashboard-efficiency-error')).toBeInTheDocument();

        expect(screen.queryByText('No Data')).not.toBeInTheDocument();
        expect(screen.queryByText('0 Appointments')).not.toBeInTheDocument();
        expect(screen.queryByText('No remaining appointments today')).not.toBeInTheDocument();
        expect(screen.queryByText('0%')).not.toBeInTheDocument();

        // Retry only appointments
        failAppts = false;
        const retryApptsBtn = within(screen.getByTestId('dashboard-today-error')).getByRole('button');
        fireEvent.click(retryApptsBtn);

        await waitFor(() => {
            expect(screen.getByText('Nadia Adel')).toBeInTheDocument();
        });

        expect(statsAttempts).toBe(1);
        expect(apptAttempts).toBe(2);
    });

    it('renders independent valid sections while the other request is still pending', async () => {
        let resolveAppts;
        const pendingApptsPromise = new Promise((resolve) => {
            resolveAppts = resolve;
        });

        vi.spyOn(api, 'get').mockImplementation((url) => {
            if (url === '/api/v1/stats/dashboard') {
                return Promise.resolve({ data: VALID_STATS });
            }
            if (url === '/api/v1/appointments') {
                return pendingApptsPromise;
            }
            return Promise.reject(new Error(`Unexpected GET ${url}`));
        });

        renderDashboard();

        const expectedIncome = formatExpectedEgp(VALID_STATS.today_received, 'en-EG');

        // Stats KPIs render immediately while appointments is still pending
        await waitFor(() => {
            expect(screen.getByText(expectedIncome)).toBeInTheDocument();
        });
        // Today's list and efficiency must NOT fabricate 0% or empty schedule while pending
        expect(screen.queryByText('0%')).not.toBeInTheDocument();
        expect(screen.queryByText('No remaining appointments today')).not.toBeInTheDocument();

        await act(async () => {
            resolveAppts({ data: SAMPLE_APPOINTMENTS });
        });

        await waitFor(() => {
            expect(screen.getByText('33%')).toBeInTheDocument();
        });
    });

    it('displays authoritative zeros and empty states when both requests succeed with zero/empty values', async () => {
        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                return { data: ZERO_STATS };
            }
            if (url === '/api/v1/appointments') {
                return { data: [] };
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        renderDashboard();

        const expectedZeroEgp = formatExpectedEgp(0, 'en-EG');

        await waitFor(() => {
            expect(screen.getAllByText(expectedZeroEgp).length).toBe(2);
        });
        expect(screen.getByText('Not enough financial data to display')).toBeInTheDocument();
        expect(screen.getByText('No Data')).toBeInTheDocument();
        expect(screen.getByText('0 Appointments')).toBeInTheDocument();
        expect(screen.getByText('No remaining appointments today')).toBeInTheDocument();
        expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('shows clear unavailable state in today schedule and efficiency when business_date is missing or invalid', async () => {
        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                return {
                    data: {
                        ...VALID_STATS,
                        business_date: '2026-02-30',
                    },
                };
            }
            if (url === '/api/v1/appointments') {
                return { data: SAMPLE_APPOINTMENTS };
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        renderDashboard();

        await waitFor(() => {
            expect(screen.getByTestId('dashboard-today-unavailable')).toBeInTheDocument();
        });
        expect(screen.getByTestId('dashboard-efficiency-unavailable')).toBeInTheDocument();
        expect(screen.getByTestId('dashboard-today-count')).toHaveTextContent('Unavailable');

        // Must never claim empty schedule or 0% due to missing/invalid business date
        expect(screen.queryByText('No remaining appointments today')).not.toBeInTheDocument();
        expect(screen.queryByText('0 Appointments')).not.toBeInTheDocument();
        expect(screen.queryByText('0%')).not.toBeInTheDocument();

        // Independent KPI cards and status distribution remain visible
        const expectedIncome = formatExpectedEgp(VALID_STATS.today_received, 'en-EG');
        expect(screen.getByText(expectedIncome)).toBeInTheDocument();
        await waitFor(() => {
            expect(screen.getByText('Completed')).toBeInTheDocument();
        });
    });

    it('preserves sorting, cancelled exclusion, and efficiency rounding when both sources are usable', async () => {
        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                return { data: VALID_STATS };
            }
            if (url === '/api/v1/appointments') {
                return { data: SAMPLE_APPOINTMENTS };
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        renderDashboard();

        await waitFor(() => {
            expect(screen.getByText('Nadia Adel')).toBeInTheDocument();
        });

        // Excluded: Tarek Cancelled (Cancelled) and Salma Yesterday (wrong date)
        expect(screen.queryByText('Tarek Cancelled')).not.toBeInTheDocument();
        expect(screen.queryByText('Salma Yesterday')).not.toBeInTheDocument();

        // Sorted chronologically: Nadia (09:30), Youssef (11:30), Omar (14:00)
        const list = screen.getByTestId('dashboard-today-list');
        const names = within(list)
            .getAllByRole('button')
            .map((btn) => btn.textContent);
        expect(names[0]).toContain('Nadia Adel');
        expect(names[1]).toContain('Youssef Third');
        expect(names[2]).toContain('Omar Hassan');
        expect(screen.getByText('33%')).toBeInTheDocument();
    });

    it('keeps previous same-clinic data on transient 5xx/network refresh failure with warning and clears it on independent retry', async () => {
        let statsMode = 'ok-v1';
        let apptMode = 'ok-v1';
        let statsCalls = 0;
        let apptCalls = 0;

        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                statsCalls += 1;
                if (statsMode === 'ok-v1') return { data: VALID_STATS };
                if (statsMode === 'fail-503') throw makeAxiosError(503, 'Transient outage');
                return {
                    data: {
                        ...VALID_STATS,
                        new_patients_today: 9,
                        today_received: 7500,
                    },
                };
            }
            if (url === '/api/v1/appointments') {
                apptCalls += 1;
                if (apptMode === 'ok-v1') return { data: SAMPLE_APPOINTMENTS };
                if (apptMode === 'fail-network') throw makeAxiosError(null, 'Network Error');
                return {
                    data: [
                        ...SAMPLE_APPOINTMENTS,
                        {
                            id: 106,
                            patient_name: 'Laila Recovered',
                            date_time: '2026-11-22T15:00:00',
                            status: 'Completed',
                            notes: 'Follow-up',
                        },
                    ],
                };
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        const { queryClient } = renderDashboard();

        const initialIncome = formatExpectedEgp(VALID_STATS.today_received, 'en-EG');

        await waitFor(() => {
            expect(screen.getByText(initialIncome)).toBeInTheDocument();
            expect(screen.getByText('Nadia Adel')).toBeInTheDocument();
        });
        expect(statsCalls).toBe(1);
        expect(apptCalls).toBe(1);

        // Trigger a transient 503 refresh failure for stats
        statsMode = 'fail-503';
        await act(async () => {
            await queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] });
        });

        await waitFor(() => {
            expect(screen.getByTestId('dashboard-stats-stale-warning')).toBeInTheDocument();
        });
        expect(screen.getByText(initialIncome)).toBeInTheDocument();
        expect(screen.getByText('Nadia Adel')).toBeInTheDocument();

        // Retry only stats and succeed with fresh data
        statsMode = 'ok-v2';
        fireEvent.click(within(screen.getByTestId('dashboard-stats-stale-warning')).getByRole('button'));

        const refreshedIncome = formatExpectedEgp(7500, 'en-EG');

        await waitFor(() => {
            expect(screen.getByText(refreshedIncome)).toBeInTheDocument();
        });
        expect(screen.queryByTestId('dashboard-stats-stale-warning')).not.toBeInTheDocument();
        expect(statsCalls).toBe(3);
        expect(apptCalls).toBe(1);

        // Trigger a transient network refresh failure for appointments
        apptMode = 'fail-network';
        await act(async () => {
            await queryClient.invalidateQueries({ queryKey: ['appointments'] });
        });

        await waitFor(() => {
            expect(screen.getByTestId('dashboard-appointments-stale-warning')).toBeInTheDocument();
        });
        expect(screen.getByText('Nadia Adel')).toBeInTheDocument();

        // Retry only appointments and succeed
        apptMode = 'ok-v2';
        fireEvent.click(within(screen.getByTestId('dashboard-appointments-stale-warning')).getByRole('button'));

        await waitFor(() => {
            expect(screen.getByText('Laila Recovered')).toBeInTheDocument();
        });
        expect(screen.queryByTestId('dashboard-appointments-stale-warning')).not.toBeInTheDocument();
        expect(statsCalls).toBe(3);
        expect(apptCalls).toBe(3);
    });

    it('never falls back to stale data on authorization failure (403) or clinic switch', async () => {
        let statsMode = 'clinic-a';
        let apptMode = 'clinic-a';

        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                if (statsMode === 'clinic-a') return { data: VALID_STATS };
                if (statsMode === 'forbidden') throw makeAxiosError(403, 'Forbidden');
                throw makeAxiosError(500, 'Clinic B failed');
            }
            if (url === '/api/v1/appointments') {
                if (apptMode === 'clinic-a') return { data: SAMPLE_APPOINTMENTS };
                throw makeAxiosError(500, 'Clinic B appointments failed');
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        const { queryClient, rerenderWithSession } = renderDashboard();

        const clinicAIncome = formatExpectedEgp(VALID_STATS.today_received, 'en-EG');

        await waitFor(() => {
            expect(screen.getByText(clinicAIncome)).toBeInTheDocument();
            expect(screen.getByText('Nadia Adel')).toBeInTheDocument();
        });

        // 403 refresh failure MUST NOT display stale Clinic A stats
        statsMode = 'forbidden';
        await act(async () => {
            await queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] });
        });

        await waitFor(() => {
            expect(screen.getByTestId('dashboard-stats-error')).toBeInTheDocument();
        });
        expect(screen.queryByTestId('dashboard-stats-stale-warning')).not.toBeInTheDocument();
        expect(screen.queryByText(clinicAIncome)).not.toBeInTheDocument();

        // Even a subsequent 500 after 403 must NOT resurrect pre-403 data
        statsMode = 'clinic-b-500';
        await act(async () => {
            await queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] });
        });
        await waitFor(() => {
            expect(screen.getByTestId('dashboard-stats-error')).toBeInTheDocument();
        });
        expect(screen.queryByTestId('dashboard-stats-stale-warning')).not.toBeInTheDocument();
        expect(screen.queryByText(clinicAIncome)).not.toBeInTheDocument();

        // Restore Clinic A, then switch to Clinic B whose fetches fail with 500
        statsMode = 'clinic-a';
        await act(async () => {
            await queryClient.invalidateQueries({ queryKey: ['dashboard', 'stats'] });
        });
        await waitFor(() => {
            expect(screen.getByText(clinicAIncome)).toBeInTheDocument();
        });

        statsMode = 'clinic-b-500';
        apptMode = 'clinic-b-500';
        rerenderWithSession({
            nextUser: { id: 2, username: 'dr_clinic_b', role: 'admin', tenant_id: 20 },
            nextTenant: { id: 20, name: 'Clinic B', plan: 'premium' },
        });

        await waitFor(() => {
            expect(screen.getByTestId('dashboard-stats-error')).toBeInTheDocument();
            expect(screen.getByTestId('dashboard-today-error')).toBeInTheDocument();
        });
        expect(screen.queryByTestId('dashboard-stats-stale-warning')).not.toBeInTheDocument();
        expect(screen.queryByTestId('dashboard-appointments-stale-warning')).not.toBeInTheDocument();
        expect(screen.queryByText(clinicAIncome)).not.toBeInTheDocument();
        expect(screen.queryByText('Nadia Adel')).not.toBeInTheDocument();
    });

    it('formats identical EGP amount using ar-EG in Arabic and en-EG in English with integer rounding', async () => {
        vi.spyOn(api, 'get').mockImplementation(async (url) => {
            if (url === '/api/v1/stats/dashboard') {
                return {
                    data: {
                        ...VALID_STATS,
                        today_received: 1250.6,
                        today_outstanding: 400.4,
                    },
                };
            }
            if (url === '/api/v1/appointments') {
                return { data: SAMPLE_APPOINTMENTS };
            }
            throw new Error(`Unexpected GET ${url}`);
        });

        const expectedEnIncome = formatExpectedEgp(1250.6, 'en-EG');
        const expectedArIncome = formatExpectedEgp(1250.6, 'ar-EG');
        const expectedArOutstanding = formatExpectedEgp(400.4, 'ar-EG');

        renderDashboard();

        await waitFor(() => {
            expect(screen.getByText(expectedEnIncome)).toBeInTheDocument();
        });

        await act(async () => {
            await i18n.changeLanguage('ar');
        });

        await waitFor(() => {
            expect(screen.getByText(expectedArIncome)).toBeInTheDocument();
            expect(screen.getByText(expectedArOutstanding)).toBeInTheDocument();
        });
        expect(screen.queryByText(expectedEnIncome)).not.toBeInTheDocument();
    });
});
