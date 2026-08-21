import { beforeEach, describe, expect, it, vi } from 'vitest';

const axiosState = vi.hoisted(() => ({
    responseErrorHandler: null,
    post: vi.fn(),
    client: null,
}));

vi.mock('axios', () => {
    const client = vi.fn();
    axiosState.client = client;
    client.interceptors = {
        request: { use: vi.fn() },
        response: {
            use: vi.fn((_success, error) => {
                axiosState.responseErrorHandler = error;
            }),
        },
    };

    const axios = {
        create: vi.fn(() => client),
        post: axiosState.post,
    };

    return { default: axios };
});

describe('API client authentication recovery', () => {
    let authStore;

    beforeEach(async () => {
        vi.resetModules();
        axiosState.responseErrorHandler = null;
        axiosState.post.mockReset();
        axiosState.client?.mockReset();
        ({ useAuthStore: authStore } = await import('@/store/auth.store'));
        authStore.getState().clearAuth();
        await import('./apiClient');
    });

    it('clears stale client auth when token refresh fails', async () => {
        authStore.getState().setUser({ id: 2, role: 'admin', tenant_id: 7 });
        const refreshError = {
            response: { status: 401, data: { detail: 'Could not validate credentials' } },
        };
        axiosState.post.mockRejectedValue(refreshError);

        await expect(axiosState.responseErrorHandler({
            config: { url: '/api/v1/notifications' },
            response: { status: 401 },
        })).rejects.toBe(refreshError);

        expect(authStore.getState().user).toBeNull();
        expect(authStore.getState().isAuthenticated).toBe(false);
    });

    it('refreshes an expired access cookie during silent startup auth', async () => {
        axiosState.post.mockResolvedValue({ data: { access_token: 'rotated' } });
        const originalRequest = {
            url: '/api/auth/session',
            _silentAuth: true,
        };

        await axiosState.responseErrorHandler({
            config: originalRequest,
            response: { status: 401 },
        });

        expect(axiosState.post).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/auth/refresh'),
            null,
            expect.objectContaining({ withCredentials: true }),
        );
        expect(axiosState.client).toHaveBeenCalledWith(
            expect.objectContaining({ url: '/api/auth/session', _retry: true }),
        );
    });

    it('clears stale auth when a request is still unauthorized after refresh', async () => {
        authStore.getState().setUser({ id: 2, role: 'super_admin', tenant_id: 7 });
        const terminalUnauthorized = {
            config: { url: '/api/v1/notifications', _retry: true, _silentAuth: true },
            response: { status: 401 },
        };

        await expect(
            axiosState.responseErrorHandler(terminalUnauthorized),
        ).rejects.toBe(terminalUnauthorized);

        expect(axiosState.post).not.toHaveBeenCalled();
        expect(authStore.getState().user).toBeNull();
        expect(authStore.getState().isAuthenticated).toBe(false);
    });
});
