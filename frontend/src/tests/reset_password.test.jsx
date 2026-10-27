import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import ResetPassword from '../pages/ResetPassword';
import { verifyResetToken, resetPassword } from '../api';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({ t: (key) => key }),
}));

vi.mock('../api', () => ({
    verifyResetToken: vi.fn(),
    resetPassword: vi.fn(),
}));

describe('<ResetPassword /> contract', () => {
    beforeEach(() => vi.clearAllMocks());

    it('accepts the StandardResponse envelope and enforces the backend length policy', async () => {
        verifyResetToken.mockResolvedValue({ data: { success: true, data: { valid: true } } });

        const { container } = render(
            <MemoryRouter initialEntries={['/reset-password?token=valid-token']}>
                <ResetPassword />
            </MemoryRouter>
        );

        await waitFor(() => expect(screen.getByText('auth.reset_password.submit')).toBeDefined());
        const passwordInputs = container.querySelectorAll('input[type="password"]');
        expect(passwordInputs[0].getAttribute('minlength')).toBe('8');
        expect(passwordInputs[0].getAttribute('maxlength')).toBe('144');

        fireEvent.click(screen.getByRole('button', { name: 'auth.show_password' }));
        expect(screen.getByRole('button', { name: 'auth.hide_password' })).toHaveAttribute('aria-pressed', 'true');
        expect(passwordInputs[0]).toHaveAttribute('type', 'text');
        expect(resetPassword).not.toHaveBeenCalled();

        fireEvent.change(passwordInputs[0], { target: { value: '1234567' } });
        fireEvent.change(passwordInputs[1], { target: { value: '1234567' } });
        fireEvent.click(screen.getByText('auth.reset_password.submit'));

        expect(await screen.findByText('auth.reset_password.errors.password_min_length')).toBeDefined();
        expect(resetPassword).not.toHaveBeenCalled();

        fireEvent.change(passwordInputs[0], { target: { value: 'abcdefgh' } });
        fireEvent.change(passwordInputs[1], { target: { value: 'abcdefgh' } });
        fireEvent.click(screen.getByText('auth.reset_password.submit'));

        expect(await screen.findByText('auth.reset_password.errors.password_weak')).toBeDefined();
        expect(resetPassword).not.toHaveBeenCalled();

        fireEvent.change(passwordInputs[0], { target: { value: 'a1'.repeat(37) } });
        fireEvent.change(passwordInputs[1], { target: { value: 'a1'.repeat(37) } });
        fireEvent.click(screen.getByText('auth.reset_password.submit'));
        expect(await screen.findByText('auth.reset_password.errors.password_max_length')).toBeDefined();
        expect(resetPassword).not.toHaveBeenCalled();

        fireEvent.change(passwordInputs[0], { target: { value: 'password1' } });
        fireEvent.change(passwordInputs[1], { target: { value: 'password1' } });
        fireEvent.click(screen.getByText('auth.reset_password.submit'));
        expect(await screen.findByText('auth.reset_password.errors.password_common')).toBeDefined();
        expect(resetPassword).not.toHaveBeenCalled();
    });

    it.each(['abc12345', 'كلمة1234', 'ahmed2024'])('submits valid password %s', async (password) => {
        verifyResetToken.mockResolvedValue({ data: { success: true, data: { valid: true } } });
        resetPassword.mockResolvedValue({ data: { success: true } });
        const { container } = render(
            <MemoryRouter initialEntries={['/reset-password?token=valid-token']}>
                <ResetPassword />
            </MemoryRouter>
        );
        await screen.findByText('auth.reset_password.submit');
        const inputs = container.querySelectorAll('input[type="password"]');
        fireEvent.change(inputs[0], { target: { value: password } });
        fireEvent.change(inputs[1], { target: { value: password } });
        fireEvent.click(screen.getByText('auth.reset_password.submit'));
        await waitFor(() => expect(resetPassword).toHaveBeenCalledWith('valid-token', password));
    });
});
