import { selectAppointmentsForBusinessDate } from '@/utils/dateTime';

const BUSINESS_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

function resolveDashboardCurrencyLocale(language) {
    const normalized = String(language || '').toLowerCase();
    return normalized.startsWith('ar') ? 'ar-EG' : 'en-EG';
}

export function formatDashboardCurrency(amount, language) {
    const locale = resolveDashboardCurrencyLocale(language);
    return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: 'EGP',
        maximumFractionDigits: 0,
    }).format(amount);
}

function getQueryErrorStatus(error) {
    if (!error || typeof error !== 'object') return null;
    const status = error?.response?.status ?? error?.status ?? null;
    return typeof status === 'number' && Number.isFinite(status) ? status : null;
}

export function isAuthorizationError(error) {
    const status = getQueryErrorStatus(error);
    return status === 401 || status === 403;
}

function isTransientRefreshError(error) {
    if (!error) return false;
    const status = getQueryErrorStatus(error);
    if (status === 401 || status === 403) return false;
    if (status === null) return true;
    return (status >= 500 && status <= 599) || status === 408 || status === 429;
}

export function isUsableStatsData(data) {
    return ['new_patients_today', 'total_appointments_today', 'today_received', 'today_outstanding']
        .every((field) => Number.isFinite(data?.[field]));
}

export function isUsableAppointmentsData(data) {
    return Array.isArray(data);
}

export function isValidBusinessDate(value) {
    if (typeof value !== 'string') return false;
    const match = BUSINESS_DATE_PATTERN.exec(value);
    if (!match) return false;

    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    if (month < 1 || month > 12 || day < 1 || day > 31) return false;

    const parsed = new Date(Date.UTC(year, month - 1, day));
    return (
        parsed.getUTCFullYear() === year
        && parsed.getUTCMonth() === month - 1
        && parsed.getUTCDate() === day
    );
}

export function buildDashboardSessionScopeKey({ user, tenant }) {
    // Impersonation enters and exits with a full navigation, and auth clears the cache on logout.
    return JSON.stringify([user?.tenant_id, tenant?.id, user?.id, user?.role]);
}

export function discardDeniedData(queryClient, queryKey) {
    const query = queryClient.getQueryCache().find({ queryKey, exact: true });
    const state = query?.state;
    if (state?.data !== undefined && (isAuthorizationError(state.error) || isAuthorizationError(state.fetchFailureReason))) {
        // Retain the failed response while preventing a later network error from reusing denied data.
        query.setState({ data: undefined, dataUpdatedAt: 0 });
    }
}

export function resolveSourceState({
    data,
    isPending,
    isError,
    error,
    isFetching,
    isUsable,
    scopeMatches,
    isDataRevoked,
}) {
    const isAuthError = isAuthorizationError(error);
    const isRetrying = isFetching;
    if (!scopeMatches) {
        return { status: 'loading', data: null, isStale: false, isAuthError: false, isRetrying: true };
    }

    const hasData = !isDataRevoked && isUsable(data);
    if (hasData && !isError) {
        return { status: 'ready', data, isStale: false, isAuthError, isRetrying };
    }
    if (hasData && isTransientRefreshError(error)) {
        return { status: 'stale', data, isStale: true, isAuthError, isRetrying };
    }
    const status = !isError && (isPending || isFetching) ? 'loading' : 'error';
    return { status, data: null, isStale: false, isAuthError, isRetrying };
}

function computeTodayScheduleAndEfficiency(appointments, businessDate) {
    const todayAppts = selectAppointmentsForBusinessDate(appointments, businessDate);
    const visibleTodayAppts = todayAppts.filter((appointment) => appointment.status !== 'Cancelled');
    const completed = visibleTodayAppts.filter((appointment) => appointment.status === 'Completed').length;
    const efficiency = visibleTodayAppts.length > 0
        ? Math.round((completed / visibleTodayAppts.length) * 100)
        : 0;
    const todaysAppointments = [...visibleTodayAppts].sort((a, b) =>
        String(a.date_time || '').localeCompare(String(b.date_time || ''))
    );

    return {
        efficiency,
        todaysAppointments,
    };
}

export function resolveTodaySectionState({ statsState, appointmentsState }) {
    const statsFailed = statsState.status === 'error';
    const appointmentsFailed = appointmentsState.status === 'error';
    const dependencies = {
        statsFailed,
        appointmentsFailed,
        statsAuthError: statsState.isAuthError,
        appointmentsAuthError: appointmentsState.isAuthError,
    };

    if (statsFailed || appointmentsFailed) return { status: 'error', ...dependencies };

    const businessDate = statsState.data?.business_date;
    if (statsState.data && !isValidBusinessDate(businessDate)) {
        return { status: 'missing_business_date', ...dependencies };
    }

    if (!statsState.data || !appointmentsState.data) return { status: 'loading', ...dependencies };

    return {
        status: 'ready',
        ...dependencies,
        ...computeTodayScheduleAndEfficiency(appointmentsState.data, businessDate),
    };
}

export function computeStatusDistribution(appointments, t) {
    if (!Array.isArray(appointments)) return [];
    return [
        {
            name: t('appointments.status.completed'),
            value: appointments.filter((appointment) => appointment.status === 'Completed').length,
            fill: '#10b981',
        },
        {
            name: t('appointments.status.scheduled'),
            value: appointments.filter((appointment) => appointment.status === 'Scheduled').length,
            fill: '#0891B2',
        },
        {
            name: t('appointments.status.waiting'),
            value: appointments.filter((appointment) => appointment.status === 'Waiting').length,
            fill: '#f59e0b',
        },
        {
            name: t('appointments.status.cancelled'),
            value: appointments.filter(
                (appointment) => appointment.status === 'Cancelled' || appointment.status === 'No Show'
            ).length,
            fill: '#ef4444',
        },
    ].filter((item) => item.value > 0);
}
