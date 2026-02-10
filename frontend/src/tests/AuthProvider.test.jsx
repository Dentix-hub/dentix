/**
 * AuthProvider Component Tests
 * Verifies authentication state management, login, logout, and context.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import AuthProvider from '@/auth/AuthProvider';
import AuthContext from '@/auth/useAuth';
import { useContext } from 'react';

// Mock dependencies
vi.mock('@/', () => ({
    login: vi.fn(),
    registerClinic: vi.fn(),
    getMe: vi.fn(),
}));

vi.mock('@/utils', () => ({
    getToken: vi.fn(),
    setToken: vi.fn(),
    removeToken: vi.fn(),
    parseJwt: vi.fn(),
}));

vi.mock('@/store/tenant.store', () => ({
    useTenantStore: {
        getState: () => ({ setTenant: vi.fn() }),
    },
}));

// Consumer component that reads auth context
function AuthConsumer() {
    const auth = useContext(AuthContext);
    return (
        <div>
            <span data-testid="loading">{String(auth.loading)}</span>
            <span data-testid="authenticated">{String(auth.isAuthenticated)}</span>
            <span data-testid="username">{auth.user?.username || 'none'}</span>
            <button onClick={() => auth.logout()} data-testid="logout-btn">Logout</button>
        </div>
    );
}

describe('AuthProvider', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Reset window.location
        delete window.location;
        window.location = { href: '' };
    });

    it('renders children when loading completes (no token)', async () => {
        const { getToken } = await import('@/utils');
        getToken.mockReturnValue(null);

        render(
            <AuthProvider>
                <AuthConsumer />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(screen.getByTestId('loading').textContent).toBe('false');
        });
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
        expect(screen.getByTestId('username').textContent).toBe('none');
    });

    it('sets user from token on initialization', async () => {
        const { getToken, parseJwt } = await import('@/utils');
        const { getMe } = await import('@/');

        getToken.mockReturnValue('fake-jwt-token');
        parseJwt.mockReturnValue({
            sub: 'dr_ahmed',
            role: 'admin',
            tenant_id: 1,
        });
        getMe.mockResolvedValue({ data: { username: 'dr_ahmed', role: 'admin' } });

        render(
            <AuthProvider>
                <AuthConsumer />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(screen.getByTestId('username').textContent).toBe('dr_ahmed');
        });
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
    });

    it('removes token and resets user on invalid token', async () => {
        const { getToken, parseJwt, removeToken } = await import('@/utils');

        getToken.mockReturnValue('invalid-token');
        parseJwt.mockImplementation(() => {
            throw new Error('Invalid token');
        });

        render(
            <AuthProvider>
                <AuthConsumer />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(removeToken).toHaveBeenCalled();
        });
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
    });

    it('provides isAuthenticated = false when no user', async () => {
        const { getToken } = await import('@/utils');
        getToken.mockReturnValue(null);

        render(
            <AuthProvider>
                <AuthConsumer />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(screen.getByTestId('authenticated').textContent).toBe('false');
        });
    });

    it('provides logout function that clears user', async () => {
        const { getToken, removeToken } = await import('@/utils');
        getToken.mockReturnValue(null);

        render(
            <AuthProvider>
                <AuthConsumer />
            </AuthProvider>
        );

        await waitFor(() => {
            expect(screen.getByTestId('loading').textContent).toBe('false');
        });

        act(() => {
            screen.getByTestId('logout-btn').click();
        });

        expect(removeToken).toHaveBeenCalled();
    });
});
