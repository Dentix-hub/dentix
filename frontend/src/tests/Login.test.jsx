/**
 * Login Component Tests
 * Verifies form rendering, user interaction, and error handling.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Login from '@/pages/Login';

const loginMock = vi.fn();
const verify2FAMock = vi.fn();

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar', changeLanguage: vi.fn() },
    }),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        login: loginMock,
        verify2FA: verify2FAMock,
    }),
}));

const renderLogin = (props = {}) => render(
    <MemoryRouter>
        <Login isDarkMode={false} toggleDarkMode={vi.fn()} {...props} />
    </MemoryRouter>
);

const renderLoginAt = (path) => render(
    <MemoryRouter initialEntries={[path]}>
        <Login isDarkMode={false} toggleDarkMode={vi.fn()} />
    </MemoryRouter>
);

describe('Login Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        loginMock.mockResolvedValue({ role: 'admin' });
    });

    it('renders the login form with username and password fields', () => {
        renderLogin();
        expect(screen.getByPlaceholderText('auth.login.username')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('auth.login.password')).toBeInTheDocument();
    });

    it('renders submit, register and forgot-password controls', () => {
        renderLogin();
        expect(screen.getByText('auth.login.submit')).toBeInTheDocument();
        expect(screen.getByText('auth.login.register_new')).toBeInTheDocument();
        expect(screen.getByText('auth.login.forgot_password')).toBeInTheDocument();
    });

    it('renders the DENTIX logo', () => {
        renderLogin();
        expect(screen.getByAltText('DENTIX Logo')).toBeInTheDocument();
    });

    it('allows typing username and password', () => {
        renderLogin();
        const usernameInput = screen.getByPlaceholderText('auth.login.username');
        const passwordInput = screen.getByPlaceholderText('auth.login.password');
        fireEvent.change(usernameInput, { target: { value: 'testuser' } });
        fireEvent.change(passwordInput, { target: { value: 'testpass123' } });
        expect(usernameInput.value).toBe('testuser');
        expect(passwordInput.value).toBe('testpass123');
    });

    it('submits credentials through the auth hook', async () => {
        renderLogin();
        fireEvent.change(screen.getByPlaceholderText('auth.login.username'), { target: { value: ' admin ' } });
        fireEvent.change(screen.getByPlaceholderText('auth.login.password'), { target: { value: 'pass123' } });
        fireEvent.click(screen.getByText('auth.login.submit'));
        await waitFor(() => expect(loginMock).toHaveBeenCalledWith('admin', 'pass123'));
    });

    it('shows error message when login fails', async () => {
        loginMock.mockRejectedValueOnce({ response: { data: { detail: 'Invalid credentials' } } });
        renderLogin();
        fireEvent.change(screen.getByPlaceholderText('auth.login.username'), { target: { value: 'wronguser' } });
        fireEvent.change(screen.getByPlaceholderText('auth.login.password'), { target: { value: 'wrongpass' } });
        fireEvent.click(screen.getByText('auth.login.submit'));
        await waitFor(() => expect(screen.getByText('Invalid credentials')).toBeInTheDocument());
    });

    it('shows a localized explanation after a session mismatch redirect', () => {
        renderLoginAt('/login?reason=session_mismatch');

        expect(screen.getByText('auth.login.errors.session_mismatch')).toBeInTheDocument();
    });

    it('renders footer terms and privacy links', () => {
        renderLogin();
        expect(screen.getByText('auth.login.terms')).toBeInTheDocument();
        expect(screen.getByText('auth.login.privacy')).toBeInTheDocument();
    });
});
