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
let currentLanguage = 'ar';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: {
            get language() { return currentLanguage; },
            changeLanguage: vi.fn((lang) => { currentLanguage = lang; }),
        },
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
        currentLanguage = 'ar';
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
        await waitFor(() => expect(loginMock).toHaveBeenCalledWith('admin', 'pass123', false));
    });

    it('toggles password visibility without submitting and sends remember-me', async () => {
        renderLogin();
        const password = screen.getByPlaceholderText('auth.login.password');
        const checkbox = screen.getByRole('checkbox', { name: 'auth.login.remember_me' });
        expect(checkbox).not.toBeChecked();
        fireEvent.click(screen.getByRole('button', { name: 'auth.show_password' }));
        expect(password).toHaveAttribute('type', 'text');
        expect(loginMock).not.toHaveBeenCalled();
        fireEvent.click(checkbox);
        fireEvent.change(screen.getByPlaceholderText('auth.login.username'), { target: { value: 'admin' } });
        fireEvent.change(password, { target: { value: 'pass123' } });
        fireEvent.click(screen.getByText('auth.login.submit'));
        await waitFor(() => expect(loginMock).toHaveBeenCalledWith('admin', 'pass123', true));
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

    it('shows a localized explanation after a session expired redirect', () => {
        renderLoginAt('/login?reason=session_expired');

        expect(screen.getByText('auth.login.errors.session_expired')).toBeInTheDocument();
    });

    it('renders footer terms and privacy links', () => {
        renderLogin();
        expect(screen.getByText('auth.login.terms')).toBeInTheDocument();
        expect(screen.getByText('auth.login.privacy')).toBeInTheDocument();
    });

    it('renders native discovery link to Arabic marketing page when language is ar', () => {
        currentLanguage = 'ar';
        renderLogin();
        const aboutLink = screen.getByText('auth.login.about');
        expect(aboutLink).toBeInTheDocument();
        expect(aboutLink.closest('a')).toHaveAttribute('href', '/ar');
    });

    it('renders native discovery link to English marketing page when language is en', () => {
        currentLanguage = 'en';
        renderLogin();
        const aboutLink = screen.getByText('auth.login.about');
        expect(aboutLink).toBeInTheDocument();
        expect(aboutLink.closest('a')).toHaveAttribute('href', '/en');
    });

    it('associates visible localized labels with username and password inputs and preserves autocomplete and tab order', () => {
        const { container } = renderLogin();
        const usernameInput = screen.getByLabelText('auth.login.username');
        const passwordInput = screen.getByLabelText('auth.login.password');
        const usernameLabel = container.querySelector(`label[for="${usernameInput.id}"]`);
        const passwordLabel = container.querySelector(`label[for="${passwordInput.id}"]`);
        const toggleButton = screen.getByRole('button', { name: 'auth.show_password' });
        const rememberCheckbox = screen.getByRole('checkbox', { name: 'auth.login.remember_me' });
        const submitButton = screen.getByRole('button', { name: 'auth.login.submit' });

        expect(usernameInput.id).toBeTruthy();
        expect(passwordInput.id).toBeTruthy();
        expect(usernameLabel).toBeInTheDocument();
        expect(passwordLabel).toBeInTheDocument();
        expect(usernameLabel).not.toHaveClass('sr-only');
        expect(passwordLabel).not.toHaveClass('sr-only');
        expect(usernameInput).toHaveAttribute('autocomplete', 'username');
        expect(passwordInput).toHaveAttribute('autocomplete', 'current-password');
        expect(toggleButton).toHaveAttribute('aria-pressed', 'false');

        const formFocusables = Array.from(
            container.querySelectorAll('form input, form button, form a'),
        );
        expect(formFocusables.indexOf(usernameInput)).toBeLessThan(formFocusables.indexOf(passwordInput));
        expect(formFocusables.indexOf(passwordInput)).toBeLessThan(formFocusables.indexOf(toggleButton));
        expect(formFocusables.indexOf(toggleButton)).toBeLessThan(formFocusables.indexOf(rememberCheckbox));
        expect(formFocusables.indexOf(rememberCheckbox)).toBeLessThan(formFocusables.indexOf(submitButton));
    });

    it('applies high-contrast #0369A1 submit, hover, focus, link, and error styles on the login form', async () => {
        loginMock.mockRejectedValueOnce({ response: { data: { detail: 'Invalid credentials' } } });
        renderLogin();

        const submitButton = screen.getByRole('button', { name: 'auth.login.submit' });
        const forgotLink = screen.getByRole('link', { name: 'auth.login.forgot_password' });
        const registerLink = screen.getByRole('link', { name: 'auth.login.register_new' });

        expect(submitButton).toBeEnabled();
        expect(submitButton).toHaveClass(
            'bg-primary-700',
            'text-white',
            'hover:bg-primary-800',
            'focus-visible:ring-2',
        );
        expect(forgotLink).toHaveClass('text-primary-700', 'dark:text-primary-300', 'focus-visible:ring-2');
        expect(registerLink).toHaveClass('text-primary-700', 'dark:text-primary-300', 'focus-visible:ring-2');

        fireEvent.change(screen.getByLabelText('auth.login.username'), { target: { value: 'user1' } });
        fireEvent.change(screen.getByLabelText('auth.login.password'), { target: { value: 'badpass' } });
        fireEvent.click(submitButton);

        const alert = await screen.findByRole('alert');
        expect(alert).toHaveClass('text-red-700', 'dark:text-red-200');
    });

    it('renders accessible enabled 2FA verify submit contrast and submits verification code', async () => {
        loginMock.mockResolvedValueOnce({ user_status: '2fa_required', access_token: 'temp-2fa-token' });
        verify2FAMock.mockResolvedValueOnce({ role: 'admin' });
        currentLanguage = 'en';
        renderLogin();

        fireEvent.change(screen.getByLabelText('auth.login.username'), { target: { value: 'admin' } });
        fireEvent.change(screen.getByLabelText('auth.login.password'), { target: { value: 'pass123' } });
        fireEvent.click(screen.getByRole('button', { name: 'auth.login.submit' }));

        const codeInput = await screen.findByPlaceholderText('000000');
        const verifyButton = screen.getByRole('button', { name: 'Verify Code' });
        expect(verifyButton).toBeDisabled();

        fireEvent.change(codeInput, { target: { value: '123456' } });
        expect(verifyButton).toBeEnabled();
        expect(verifyButton).toHaveClass(
            'bg-emerald-700',
            'text-white',
            'hover:bg-emerald-800',
            'focus-visible:ring-2',
        );

        fireEvent.click(verifyButton);
        await waitFor(() => expect(verify2FAMock).toHaveBeenCalledWith('123456', 'temp-2fa-token'));
    });
});
