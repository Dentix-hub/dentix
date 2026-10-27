import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import AuthProvider from '@/auth/AuthProvider';
import Login from '@/pages/Login';
import { useAuthStore } from '@/store/auth.store';
import { useTenantStore } from '@/store/tenant.store';

const mocks = vi.hoisted(() => ({ login: vi.fn(), post: vi.fn() }));
vi.mock('@/api', () => ({
    api: { post: mocks.post }, login: mocks.login, registerClinic: vi.fn(),
    getSessionSilent: vi.fn(), hasSessionCookieHint: () => false, clearSessionCookieHint: vi.fn(),
}));
vi.mock('@/utils', () => ({ logout: vi.fn() }));
vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() }, logger: { log: vi.fn(), info: vi.fn(), error: vi.fn() } }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key) => key, i18n: { language: 'ar', changeLanguage: vi.fn() } }) }));

beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ user: null, isAuthenticated: false, isAuthLoading: true });
    useTenantStore.getState().clearTenant();
    useTenantStore.setState({ fetchTenant: vi.fn().mockResolvedValue(undefined) });
});

it('keeps the real login mounted through a delayed challenge and verifies it', async () => {
    let resolveLogin;
    mocks.login.mockReturnValue(new Promise((resolve) => { resolveLogin = resolve; }));
    mocks.post.mockResolvedValue({ data: { user: { id: 1, name: 'Admin', role: 'admin', tenant_id: 1 }, role: 'admin' } });
    render(<MemoryRouter><AuthProvider><Login isDarkMode={false} toggleDarkMode={vi.fn()} /></AuthProvider></MemoryRouter>);
    fireEvent.change(await screen.findByPlaceholderText('auth.login.username'), { target: { value: 'admin' } });
    fireEvent.change(screen.getByPlaceholderText('auth.login.password'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('checkbox', { name: 'auth.login.remember_me' }));
    fireEvent.click(screen.getByText('auth.login.submit'));
    expect(mocks.login).toHaveBeenCalledWith('admin', 'secret', true);
    expect(screen.getByPlaceholderText('auth.login.password')).toBeInTheDocument();
    await act(async () => resolveLogin({ data: { user_status: '2fa_required', access_token: 'pending' } }));
    fireEvent.change(await screen.findByPlaceholderText('000000'), { target: { value: '123456' } });
    fireEvent.click(screen.getByText('تأكيد الرمز'));
    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/api/v1/auth/login/2fa', 'code=123456', expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer pending' }) })));
    await waitFor(() => expect(useAuthStore.getState().user).toMatchObject({ id: 1 }));
});
