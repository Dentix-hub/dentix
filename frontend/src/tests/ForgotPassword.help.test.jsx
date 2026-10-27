import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import ForgotPassword from '../pages/ForgotPassword';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key) => key }) }));
vi.mock('../api', () => ({ forgotPassword: vi.fn() }));

it('shows the same guidance without looking up an account', () => {
    render(<MemoryRouter><ForgotPassword /></MemoryRouter>);
    expect(screen.getByText('auth.forgot_password.no_email_help')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('example@email.com')).toHaveAttribute('aria-describedby', 'no-email-help');
});
