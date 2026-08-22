import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AuthProvider from '@/auth/AuthProvider';
import { useAuth } from '@/auth/useAuth';
import { useAuthStore } from '@/store/auth.store';
import { useTenantStore } from '@/store/tenant.store';

const apiLoginMock = vi.hoisted(() => vi.fn());
const hasSessionCookieHintMock = vi.hoisted(() => vi.fn(() => false));

vi.mock('@/api', () => ({
    api: { post: vi.fn() },
    login: apiLoginMock,
    registerClinic: vi.fn(),
    getSessionSilent: vi.fn(),
    hasSessionCookieHint: hasSessionCookieHintMock,
}));

vi.mock('@/utils', () => ({ logout: vi.fn() }));
vi.mock('@/utils/logger', () => ({
    logger: { log: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));

function deferred() {
    let resolve;
    const promise = new Promise((resolvePromise) => {
        resolve = resolvePromise;
    });
    return { promise, resolve };
}

function LoginHarness() {
    const auth = useAuth();
    if (auth.isAuthenticated) return <div>Dashboard ready</div>;
    return (
        <button type="button" onClick={() => void auth.login('admin', 'secret')}>
            Log in
        </button>
    );
}

describe('AuthProvider login lifecycle', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useAuthStore.setState({
            user: null,
            isAuthLoading: true,
            isAuthenticated: false,
            is2faPending: false,
            tempToken: null,
        });
        useTenantStore.getState().clearTenant();
    });

    it('does not mount the authenticated dashboard before tenant hydration finishes', async () => {
        const tenantHydration = deferred();
        const fetchTenant = vi.fn(() => tenantHydration.promise);
        useTenantStore.setState({ fetchTenant });
        apiLoginMock.mockResolvedValue({
            data: {
                role: 'admin',
                user_status: 'active',
                user: { id: 7, name: 'Clinic Admin', role: 'admin', tenant_id: 44 },
            },
        });

        render(
            <AuthProvider>
                <LoginHarness />
            </AuthProvider>
        );

        const loginButton = await screen.findByRole('button', { name: 'Log in' });
        fireEvent.click(loginButton);

        await waitFor(() => expect(fetchTenant).toHaveBeenCalledTimes(1));
        expect(useAuthStore.getState().user).toBeNull();
        expect(screen.queryByText('Dashboard ready')).toBeNull();

        await act(async () => {
            tenantHydration.resolve();
            await tenantHydration.promise;
        });

        expect(await screen.findByText('Dashboard ready')).toBeInTheDocument();
        expect(useAuthStore.getState().user).toMatchObject({ id: 7, tenant_id: 44 });
    });
});
