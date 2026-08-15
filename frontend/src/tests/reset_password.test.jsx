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
        expect(passwordInputs[0].getAttribute('maxlength')).toBe('72');

        fireEvent.change(passwordInputs[0], { target: { value: '1234567' } });
        fireEvent.change(passwordInputs[1], { target: { value: '1234567' } });
        fireEvent.click(screen.getByText('auth.reset_password.submit'));

        expect(await screen.findByText('auth.reset_password.errors.password_min_length')).toBeDefined();
        expect(resetPassword).not.toHaveBeenCalled();
    });
});
