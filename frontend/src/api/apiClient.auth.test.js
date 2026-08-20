import { beforeEach, describe, expect, it, vi } from 'vitest';

const axiosState = vi.hoisted(() => ({
    responseErrorHandler: null,
    post: vi.fn(),
}));

vi.mock('axios', () => {
    const client = vi.fn();
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
});
