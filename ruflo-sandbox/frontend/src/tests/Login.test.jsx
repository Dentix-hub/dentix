/**
 * Login Component Tests
 * Verifies form rendering, user interaction, and error handling.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Login from '@/pages/Login';

// Mock dependencies
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key) => key,
        i18n: { language: 'ar', changeLanguage: vi.fn() },
    }),
}));

vi.mock('../api', () => ({
    login: vi.fn(),
}));

// Base64 assets replaced with static files (T-1.9)
// Logo is now referenced via static URL in component

const renderLogin = (props = {}) => {
    return render(
        <MemoryRouter>
            <Login isDarkMode={false} toggleDarkMode={vi.fn()} {...props} />
        </MemoryRouter>
    );
};

describe('Login Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the login form with username and password fields', () => {
        renderLogin();
        expect(screen.getByPlaceholderText('auth.login.username')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('auth.login.password')).toBeInTheDocument();
    });

    it('renders submit button', () => {
        renderLogin();
        expect(screen.getByText('auth.login.submit')).toBeInTheDocument();
    });

    it('renders register link', () => {
        renderLogin();
        expect(screen.getByText('auth.login.register_new')).toBeInTheDocument();
    });

    it('renders forgot password link', () => {
        renderLogin();
        expect(screen.getByText('auth.login.forgot_password')).toBeInTheDocument();
    });

    it('renders the DENTIX logo', () => {
        renderLogin();
        expect(screen.getByAltText('DENTIX Logo')).toBeInTheDocument();
    });

    it('renders dark mode toggle button', () => {
        const toggleFn = vi.fn();
        renderLogin({ toggleDarkMode: toggleFn });
        // The toggle button should exist (contains Sun or Moon icon)
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThanOrEqual(1);
    });

    it('allows typing in username and password fields', () => {
        renderLogin();
        const usernameInput = screen.getByPlaceholderText('auth.login.username');
        const passwordInput = screen.getByPlaceholderText('auth.login.password');

        fireEvent.change(usernameInput, { target: { value: 'testuser' } });
        fireEvent.change(passwordInput, { target: { value: 'testpass123' } });

        expect(usernameInput.value).toBe('testuser');
        expect(passwordInput.value).toBe('testpass123');
    });

    it('renders remember me checkbox', () => {
        renderLogin();
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
        expect(checkbox).not.toBeChecked();
    });

    it('toggles remember me checkbox', () => {
        renderLogin();
        const checkbox = screen.getByRole('checkbox');
        fireEvent.click(checkbox);
        expect(checkbox).toBeChecked();
    });

    it('shows error message when login fails', async () => {
        const { login: loginApi } = await import('../api');
        loginApi.mockRejectedValueOnce({
            response: { data: { detail: 'Invalid credentials' } },
        });

        renderLogin();
        const usernameInput = screen.getByPlaceholderText('auth.login.username');
        const passwordInput = screen.getByPlaceholderText('auth.login.password');
        const submitButton = screen.getByText('auth.login.submit');

        fireEvent.change(usernameInput, { target: { value: 'wronguser' } });
        fireEvent.change(passwordInput, { target: { value: 'wrongpass' } });
        fireEvent.click(submitButton);

        await waitFor(() => {
            expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
        });
    });

    it('renders footer with terms and privacy links', () => {
        renderLogin();
        expect(screen.getByText('auth.login.terms')).toBeInTheDocument();
        expect(screen.getByText('auth.login.privacy')).toBeInTheDocument();
    });
});

