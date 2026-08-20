import { beforeEach, describe, expect, it, vi } from 'vitest';

const { axiosMock, apiClientMock, responseUseMock } = vi.hoisted(() => {
    const responseUseMock = vi.fn();
    const apiClientMock = vi.fn();

    Object.assign(apiClientMock, {
        interceptors: {
            request: { use: vi.fn() },
            response: { use: responseUseMock },
        },
    });

    return {
        responseUseMock,
        apiClientMock,
        axiosMock: {
            create: vi.fn(() => apiClientMock),
            post: vi.fn(),
        },
    };
});

vi.mock('axios', () => ({ default: axiosMock }));

vi.mock('@/utils/logger', () => ({
    logger: {
        log: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
    },
}));

const refreshMismatchError = () => ({
    response: {
        status: 401,
        data: { detail: 'Session Mismatch: active on another device' },
    },
});

const originalUnauthorizedError = () => ({
    config: { url: '/api/v1/patients' },
    response: { status: 401 },
});

async function loadMismatchHandler() {
    const { API_URL } = await import('@/api/apiClient');
    const { useAuthStore } = await import('@/store/auth.store');
    const { useTenantStore } = await import('@/store/tenant.store');
    const { queryClient } = await import('@/lib/queryClient');
    const onRejected = responseUseMock.mock.calls.at(-1)[1];

    return { API_URL, onRejected, queryClient, useAuthStore, useTenantStore };
}

async function runMismatch(onRejected, logout = () => Promise.reject(new Error('logout endpoint unavailable'))) {
    const mismatchError = refreshMismatchError();
    axiosMock.post
        .mockRejectedValueOnce(mismatchError)
        .mockImplementationOnce(logout);

    return {
        mismatchError,
        result: onRejected(originalUnauthorizedError()),
    };
}

const settleWithin = (result) => Promise.race([
    result.then(
        () => 'resolved',
        (error) => error,
    ),
    new Promise((resolve) => setTimeout(() => resolve('timeout'), 100)),
]);

const createDeferred = () => {
    let resolve;
    const promise = new Promise((resolvePromise) => {
        resolve = resolvePromise;
    });
    return { promise, resolve };
};

function seedSensitiveState({ queryClient, useAuthStore, useTenantStore }) {
    useAuthStore.setState({
        user: { id: 7, username: 'dentist' },
        isAuthenticated: true,
        isAuthLoading: false,
        is2faPending: true,
        tempToken: 'temporary-token',
    });
    useTenantStore.setState({
        tenant: { id: 11, name: 'Sensitive Clinic' },
        loading: true,
        error: new Error('sensitive tenant error'),
        features: { BILLING: true },
    });
    queryClient.setQueryData(['sensitive-patient'], { id: 42, name: 'Private Patient' });
    sessionStorage.setItem('admin_token', 'sensitive-admin-token');
    sessionStorage.setItem('print_rx_data', 'sensitive-prescription');
}

function expectSensitiveStateCleared({ queryClient, useAuthStore, useTenantStore }) {
    expect(queryClient.getQueryData(['sensitive-patient'])).toBeUndefined();
    expect(useTenantStore.getState()).toMatchObject({
        tenant: null,
        loading: false,
        error: null,
        features: {},
    });
    expect(sessionStorage.getItem('admin_token')).toBeNull();
    expect(sessionStorage.getItem('print_rx_data')).toBeNull();
    expect(useAuthStore.getState()).toMatchObject({
        user: null,
        isAuthenticated: false,
        isAuthLoading: false,
        is2faPending: false,
        tempToken: null,
    });
}

describe('API session mismatch handling', () => {
    const replace = vi.fn();

    beforeEach(() => {
        vi.resetModules();
        vi.clearAllMocks();
        axiosMock.post.mockReset();
        sessionStorage.clear();
        vi.stubGlobal('location', {
            hostname: 'localhost',
            protocol: 'http:',
            origin: 'http://localhost:5173',
            replace,
        });
    });

    it('sets blocking auth loading immediately while best-effort logout is pending', async () => {
        const dependencies = await loadMismatchHandler();
        const logout = createDeferred();
        seedSensitiveState(dependencies);

        const { mismatchError, result } = await runMismatch(
            dependencies.onRejected,
            () => logout.promise,
        );
        await vi.waitFor(() => expect(axiosMock.post).toHaveBeenCalledTimes(2));

        expect(dependencies.useAuthStore.getState().isAuthLoading).toBe(true);
        expect(dependencies.useAuthStore.getState().user).toMatchObject({ id: 7 });
        expect(dependencies.queryClient.getQueryData(['sensitive-patient'])).toBeDefined();
        expect(replace).not.toHaveBeenCalled();

        logout.resolve({ data: {} });
        await expect(result).rejects.toBe(mismatchError);
    });

    it('best-effort calls logout with direct axios so the API interceptor cannot recurse', async () => {
        const { API_URL, onRejected } = await loadMismatchHandler();

        const { result } = await runMismatch(onRejected);
        await settleWithin(result);

        expect(axiosMock.post).toHaveBeenNthCalledWith(
            2,
            `${API_URL}/api/v1/auth/logout`,
            null,
            { withCredentials: true, timeout: 5000 },
        );
        expect(apiClientMock).not.toHaveBeenCalledWith(
            expect.objectContaining({ url: '/api/v1/auth/logout' }),
        );
    });

    it('cleans all sensitive client state after best-effort logout succeeds', async () => {
        const dependencies = await loadMismatchHandler();
        seedSensitiveState(dependencies);
        const cancelQueries = vi.spyOn(dependencies.queryClient, 'cancelQueries');
        const clearQueries = vi.spyOn(dependencies.queryClient, 'clear');

        const { mismatchError, result } = await runMismatch(
            dependencies.onRejected,
            () => Promise.resolve({ data: {} }),
        );
        const settled = await settleWithin(result);

        expect(settled).toBe(mismatchError);
        expect(cancelQueries).toHaveBeenCalledOnce();
        expect(clearQueries).toHaveBeenCalledOnce();
        expect(cancelQueries.mock.invocationCallOrder[0]).toBeLessThan(clearQueries.mock.invocationCallOrder[0]);
        expectSensitiveStateCleared(dependencies);
        expect(replace).toHaveBeenCalledWith('/login?reason=session_mismatch');
    });

    it('still cleans sensitive state, replaces, and rejects when best-effort logout fails', async () => {
        const dependencies = await loadMismatchHandler();
        seedSensitiveState(dependencies);

        const { mismatchError, result } = await runMismatch(dependencies.onRejected);
        const settled = await settleWithin(result);

        expect(settled).toBe(mismatchError);
        expectSensitiveStateCleared(dependencies);
        expect(replace).toHaveBeenCalledWith('/login?reason=session_mismatch');
    });
});
